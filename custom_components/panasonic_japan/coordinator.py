"""Data update coordinator for Panasonic Japan."""
from __future__ import annotations

import logging
from datetime import timedelta

from typing import TYPE_CHECKING, Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    PanasonicAPI,
    PanasonicAuthError,
    PanasonicConnectionError,
    PanasonicAPIError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .cooling_assist import (
    clamp_cooling_assist_values,
    get_cooling_assist_bounds,
    get_default_cooling_assist_time,
)
from .handlers import APIHandlerFactory

if TYPE_CHECKING:
    from .data import PanasonicConfigEntry

_LOGGER = logging.getLogger(__name__)


class PanasonicDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Panasonic API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: PanasonicConfigEntry,
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

        # Cooling assist state managed per appliance
        self.cooling_assist_mode: str = "off"
        self.cooling_assist_time: int = 0
        self.cooling_assist_second: int = 0
        self._cooling_assist_listeners: list[Callable[[], None]] = []

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{self.appliance_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    def register_cooling_assist_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a listener for cooling assist state changes."""
        self._cooling_assist_listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._cooling_assist_listeners:
                self._cooling_assist_listeners.remove(listener)

        return unsubscribe

    def _notify_cooling_assist_listeners(self) -> None:
        """Notify registered listeners of cooling assist changes."""
        for listener in list(self._cooling_assist_listeners):
            try:
                listener()
            except Exception as err:
                _LOGGER.warning("Error notifying cooling assist listener: %s", err)

    def set_cooling_assist_mode(self, mode: str) -> None:
        """Update cooling assist mode and set default duration."""
        self.cooling_assist_mode = mode
        def_time, def_sec = get_default_cooling_assist_time(mode)
        self.cooling_assist_time = def_time
        self.cooling_assist_second = def_sec
        self._notify_cooling_assist_listeners()

    def set_cooling_assist_time(self, time_min: int | float) -> None:
        """Update cooling assist minutes with clamping."""
        bounds = get_cooling_assist_bounds(self.cooling_assist_mode)
        self.cooling_assist_time = max(bounds["min_time"], min(bounds["max_time"], int(time_min)))
        self._notify_cooling_assist_listeners()

    def set_cooling_assist_second(self, time_sec: int | float) -> None:
        """Update cooling assist seconds with step snapping and clamping."""
        bounds = get_cooling_assist_bounds(self.cooling_assist_mode)
        if bounds["max_sec"] > 0:
            clamped = (round(int(time_sec) / 10)) * 10
            self.cooling_assist_second = max(bounds["min_sec"], min(bounds["max_sec"], clamped))
        else:
            self.cooling_assist_second = 0
        self._notify_cooling_assist_listeners()

    async def async_control_cooling_assist(
        self, mode: str, time_min: int | float = 0, time_sec: int | float = 0
    ) -> None:
        """Send cooling assist command to the device and refresh status."""
        clamped_time, clamped_sec = clamp_cooling_assist_values(mode, time_min, time_sec)
        payload: dict[str, Any] = {"cooloven_mode": mode}
        if mode != "off":
            payload["cooloven_time"] = clamped_time
            payload["cooloven_second"] = clamped_sec

        await self.api.control_device(self.appliance_id, payload)
        await self.async_request_refresh()

    async def async_execute_cooling_assist(self) -> None:
        """Execute cooling assist using currently configured settings."""
        if (
            self.cooling_assist_mode == "quench"
            and self.cooling_assist_time == 0
            and self.cooling_assist_second == 0
        ):
            raise HomeAssistantError("Time and seconds cannot both be 0 in quench mode.")

        await self.async_control_cooling_assist(
            self.cooling_assist_mode,
            self.cooling_assist_time,
            self.cooling_assist_second,
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
            await self.api.refresh_access_token()
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
        """Fetch data from Panasonic API with safe token validation and retry."""
        try:
            await self.api.ensure_token_valid()
        except PanasonicConnectionError as err:
            self.api.handle_connection_error()
            raise UpdateFailed(f"Network error during token check (will retry): {err}") from err
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
            self.api.handle_connection_error()
            raise UpdateFailed(f"Network error (will retry): {err}") from err

        except PanasonicAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
