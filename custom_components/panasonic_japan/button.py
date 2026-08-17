"""Button platform for the cooling assist integration."""
from __future__ import annotations

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator
from .data import PanasonicDataStore
from .utils import is_fridge_eoj

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinators = PanasonicDataStore.get(hass).get_coordinators(entry.entry_id)

    entities = []
    for coordinator in coordinators.values():
        if is_fridge_eoj(coordinator.eoj):
            entities.append(CoolingAssistButton(coordinator))

    async_add_entities(entities)


class CoolingAssistButton(CoordinatorEntity[PanasonicDataUpdateCoordinator], ButtonEntity):
    """Representation of the Cooling Assist trigger button."""

    _attr_has_entity_name = True
    _attr_translation_key = "cooling_assist"

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_cooling_assist"
        self._attr_icon = "mdi:snowflake"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    async def async_press(self) -> None:
        """Handle the button press action with validation and clamping."""
        registry = er.async_get(self.hass)

        mode_entity_id = registry.async_get_entity_id(
            "select", DOMAIN, f"{self.coordinator.appliance_id}_cooling_assist_mode"
        )
        time_entity_id = registry.async_get_entity_id(
            "number", DOMAIN, f"{self.coordinator.appliance_id}_cooling_assist_time"
        )
        sec_entity_id = registry.async_get_entity_id(
            "number", DOMAIN, f"{self.coordinator.appliance_id}_cooling_assist_second"
        )

        mode = "off"
        if mode_entity_id:
            if state := self.hass.states.get(mode_entity_id):
                mode = state.state

        time_val = 0.0
        if time_entity_id:
            if state := self.hass.states.get(time_entity_id):
                try:
                    time_val = float(state.state)
                except (TypeError, ValueError):
                    pass

        sec_val = 0.0
        if sec_entity_id:
            if state := self.hass.states.get(sec_entity_id):
                try:
                    sec_val = float(state.state)
                except (TypeError, ValueError):
                    pass

        time_int = int(time_val)
        sec_int = int(sec_val)

        min_time, max_time = 0, 60
        max_sec = 50

        if mode == "quench":
            min_time, max_time = 0, 10
            max_sec = 50
            sec_int = (sec_int // 10) * 10
            if sec_int < 0:
                sec_int = 0
            if sec_int > max_sec:
                sec_int = max_sec
        elif mode == "cold":
            min_time, max_time = 10, 30
            sec_int = 0
        elif mode in ("freeze", "frozen"):
            min_time, max_time = 30, 60
            sec_int = 0
        elif mode == "off":
            time_int = 0
            sec_int = 0

        if time_int < min_time:
            time_int = min_time
        if time_int > max_time:
            time_int = max_time

        if mode == "quench" and time_int == 0 and sec_int == 0:
            raise HomeAssistantError("Time and seconds cannot both be 0 in quench mode.")

        service_data = {
            "mode": mode,
            "appliance_id": self.coordinator.appliance_id,
        }
        if mode != "off":
            service_data["time"] = time_int
            service_data["second"] = sec_int

        await self.hass.services.async_call(
            DOMAIN,
            "set_cooloven",
            service_data,
            blocking=True,
        )