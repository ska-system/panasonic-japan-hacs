"""Service registration for Panasonic Japan."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .data import PanasonicConfigEntry
from .utils import is_fridge_eoj

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_COOLOVEN = "set_cooloven"


async def handle_set_cooloven(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle cooloven service call dynamically for target devices."""
    mode = call.data.get("mode", "off")
    time_min = call.data.get("time", 0)
    time_sec = call.data.get("second", 0)
    target_appliance_id = call.data.get("appliance_id")

    entries: list[PanasonicConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    for entry in entries:
        for coordinator in entry.runtime_data.coordinators.values():
            if is_fridge_eoj(coordinator.eoj):
                if not target_appliance_id or coordinator.appliance_id == target_appliance_id:
                    await coordinator.async_control_cooling_assist(
                        mode, time_min, time_sec
                    )


def async_register_services(hass: HomeAssistant) -> None:
    """Register integration-level services when supported devices are present."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_COOLOVEN):
        return

    async def _handle_set_cooloven(call: ServiceCall) -> None:
        await handle_set_cooloven(hass, call)

    hass.services.async_register(DOMAIN, SERVICE_SET_COOLOVEN, _handle_set_cooloven)


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove integration-level services when no config entries remain."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_COOLOVEN):
        hass.services.async_remove(DOMAIN, SERVICE_SET_COOLOVEN)
