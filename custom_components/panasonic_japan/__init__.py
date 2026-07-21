"""The Panasonic Japan Kitchen Appliances integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator
from .push import PanasonicPushHandler

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR, 
    Platform.SWITCH, 
    Platform.SELECT, 
    Platform.NUMBER, 
    Platform.BUTTON
]

_PUSH_KEY = f"{DOMAIN}_push"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic Japan from a config entry."""
    coordinator = PanasonicDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start push notification listener (non-blocking; failure is logged, not fatal)
    push_handler = PanasonicPushHandler(hass, coordinator.api, entry)
    hass.data.setdefault(_PUSH_KEY, {})[entry.entry_id] = push_handler
    hass.async_create_task(push_handler.async_start())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        push_handler: PanasonicPushHandler = hass.data.get(_PUSH_KEY, {}).pop(
            entry.entry_id, None
        )
        if push_handler:
            await push_handler.async_stop()

    return unload_ok
