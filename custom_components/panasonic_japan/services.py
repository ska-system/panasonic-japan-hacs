"""Service registration for Panasonic Japan."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .data import PanasonicDataStore
from .utils import is_fridge_eoj

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_COOLOVEN = "set_cooloven"


async def handle_set_cooloven(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle cooloven service call dynamically for target devices."""
    mode = call.data.get("mode")
    time_min = call.data.get("time", 0)
    time_sec = call.data.get("second", 0)
    target_appliance_id = call.data.get("appliance_id")

    payload = {"cooloven_mode": mode}
    if mode != "off":
        payload["cooloven_time"] = int(time_min or 0)
        payload["cooloven_second"] = int(time_sec or 0)

    store = PanasonicDataStore.get(hass)
    for coordinator in store.iter_fridge_coordinators(target_appliance_id):
        await hass.async_add_executor_job(
            coordinator.api.control_device,
            coordinator.appliance_id,
            payload,
        )
        await coordinator.async_request_refresh()


def async_register_services(hass: HomeAssistant, coordinators: dict) -> None:
    """Register integration-level services when supported devices are present."""
    if not any(is_fridge_eoj(c.eoj) for c in coordinators.values()):
        return

    if hass.services.has_service(DOMAIN, SERVICE_SET_COOLOVEN):
        return

    async def _handle_set_cooloven(call: ServiceCall) -> None:
        await handle_set_cooloven(hass, call)

    hass.services.async_register(DOMAIN, SERVICE_SET_COOLOVEN, _handle_set_cooloven)


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove integration-level services when no config entries remain."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_COOLOVEN):
        hass.services.async_remove(DOMAIN, SERVICE_SET_COOLOVEN)
