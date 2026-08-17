"""Data update coordinator for Panasonic Japan."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    PanasonicAPI,
    PanasonicAuthError,
    PanasonicConnectionError,
    PanasonicAPIError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .handlers import APIHandlerFactory

_LOGGER = logging.getLogger(__name__)


class PanasonicDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Panasonic API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        appliance_info: dict,
        api: PanasonicAPI,
    ) -> None:
        """Initialize."""
        self.api = api
        self.appliance_id = appliance_info["appliance_id"]
        self.product_code = appliance_info.get("product_code", "Unknown")
        self.eoj = appliance_info.get("eoj")
        self.config_entry = config_entry
        self.hass = hass

        self.handler = APIHandlerFactory.create(self.eoj, self.api)

        self.pending_cooloven_mode = "quench"
        self.pending_cooloven_time = 0
        self.pending_cooloven_second = 0

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.appliance_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_persist_tokens(self) -> bool:
        """Persist refreshed tokens from the shared API client to the config entry."""
        if not self.api.access_token:
            _LOGGER.error("Token refresh returned empty response")
            return False

        new_data = dict(self.config_entry.data)
        new_data["access_token"] = self.api.access_token
        if self.api.refresh_token:
            new_data["refresh_token"] = self.api.refresh_token
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        _LOGGER.info("Access token refreshed and persisted successfully")
        return True

    async def _async_refresh_and_persist(self) -> bool:
        """Refresh tokens via the API client and persist them."""
        if not self.api.refresh_token:
            _LOGGER.error("No refresh token available — re-authentication required")
            return False

        _LOGGER.info("Refreshing Panasonic access token")
        try:
            await self.hass.async_add_executor_job(self.api.refresh_access_token)
        except PanasonicAuthError as err:
            _LOGGER.error("Token refresh failed: %s — re-authentication required", err)
            return False
        except PanasonicAPIError as err:
            _LOGGER.error("Unexpected API error refreshing token: %s", err)
            return False

        return await self._async_persist_tokens()

    async def _fetch_all(self) -> dict:
        """Fetch all device data from the API via handler."""
        push_term_id = self.config_entry.data.get("push_term_id", "")
        data = await self.handler.fetch_all_data(self.appliance_id, push_term_id)
        data.update({
            "appliance_id": self.appliance_id,
            "product_code": self.product_code,
            "eoj": self.eoj,
        })
        return data

    async def _async_update_data(self) -> dict:
        """Fetch data from Panasonic API."""
        await self.hass.async_add_executor_job(self.api.prepare_request_cycle)

        try:
            await self.hass.async_add_executor_job(self.api.ensure_token_valid)
        except PanasonicAuthError:
            if not await self._async_refresh_and_persist():
                raise UpdateFailed(
                    "Access token expired and refresh failed — please re-authenticate"
                )

        try:
            return await self._fetch_all()

        except PanasonicAuthError as err:
            _LOGGER.warning("Auth error during fetch — attempting token refresh: %s", err)
            if await self._async_refresh_and_persist():
                try:
                    return await self._fetch_all()
                except Exception as retry_err:
                    raise UpdateFailed(
                        f"API error after token refresh: {retry_err}"
                    ) from retry_err
            raise UpdateFailed(f"Authentication failed: {err}") from err

        except PanasonicConnectionError as err:
            await self.hass.async_add_executor_job(self.api.handle_connection_error)
            raise UpdateFailed(f"Network error (will retry): {err}") from err

        except PanasonicAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
