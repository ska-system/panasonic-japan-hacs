"""Data update coordinator for Panasonic Japan."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import requests as requests_lib

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PanasonicAPI, PanasonicAPIError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class PanasonicDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Panasonic API."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize."""
        self.api = PanasonicAPI(
            access_token=config_entry.data["access_token"],
            refresh_token=config_entry.data.get("refresh_token"),
        )
        self.appliance_id = config_entry.data["appliance_id"]
        self.product_code = config_entry.data.get("product_code", "Unknown")
        self.config_entry = config_entry
        self.hass = hass

        # クーリングアシストの設定値を一時的に保持するキャッシュ変数
        self.pending_cooloven_mode = "quench"
        self.pending_cooloven_time = 0
        self.pending_cooloven_second = 0

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_refresh_token(self) -> bool:
        """Refresh the access token and persist new tokens to the config entry.

        Returns True on success, False on failure.
        """
        if not self.api.refresh_token:
            _LOGGER.error("No refresh token available — re-authentication required")
            return False

        _LOGGER.info("Refreshing Panasonic access token")
        try:
            token_data = await self.hass.async_add_executor_job(
                self.api.refresh_access_token
            )
        except PanasonicAPIError as err:
            _LOGGER.error("Token refresh failed: %s — re-authentication required", err)
            return False
        except Exception as err:
            _LOGGER.error("Unexpected error refreshing token: %s", err)
            return False

        if not token_data or not self.api.access_token:
            _LOGGER.error("Token refresh returned empty response")
            return False

        new_data = dict(self.config_entry.data)
        new_data["access_token"] = self.api.access_token
        if self.api.refresh_token:
            new_data["refresh_token"] = self.api.refresh_token
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        _LOGGER.info("Access token refreshed and persisted successfully")
        return True

    async def _fetch_all(self) -> dict:
        """Fetch all device data from the API."""
        device_status, device_settings, electricity_data = await asyncio.gather(
            self.hass.async_add_executor_job(
                self.api.get_device_status, self.appliance_id
            ),
            self.hass.async_add_executor_job(
                self.api.get_device_settings, self.appliance_id
            ),
            self.hass.async_add_executor_job(
                self.api.get_electricity_reduction, self.appliance_id
            ),
        )
        device_status.update(device_settings)
        return {
            "device_status": device_status,
            "electricity": electricity_data,
            "appliance_id": self.appliance_id,
            "product_code": self.product_code,
        }

    async def _async_update_data(self) -> dict:
        """Fetch data from Panasonic API."""

        # Fresh connection for every update cycle — prevents stale socket issues
        await self.hass.async_add_executor_job(self.api.reset_session)

        # Proactively refresh the token if it expires within the next 5 minutes
        if self.api.is_token_expiring(margin_seconds=300):
            _LOGGER.debug("Access token is expiring soon — refreshing proactively")
            if not await self._async_refresh_token():
                raise UpdateFailed(
                    "Access token expired and refresh failed — please re-authenticate"
                )

        try:
            return await self._fetch_all()

        except PanasonicAPIError as err:
            _LOGGER.warning("API error (will attempt token refresh): %s", err)

            if "401" in str(err) or "403" in str(err):
                if await self._async_refresh_token():
                    try:
                        return await self._fetch_all()
                    except Exception as retry_err:
                        raise UpdateFailed(
                            f"API error after token refresh: {retry_err}"
                        ) from retry_err

            raise UpdateFailed(f"Error communicating with API: {err}") from err

        except (requests_lib.exceptions.Timeout,
                requests_lib.exceptions.ConnectionError) as err:
            # Reset the session so the next update gets a fresh connection
            _LOGGER.warning("Network error, resetting session: %s", err)
            await self.hass.async_add_executor_job(self.api.reset_session)
            raise UpdateFailed(f"Network error (will retry): {err}") from err

        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
