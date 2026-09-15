"""Climate platform for Panasonic Japan."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform, config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .cooling_assist import get_default_cooling_assist_time
from .coordinator import PanasonicDataUpdateCoordinator
from .data import PanasonicConfigEntry
from .entity import PanasonicEntity
from .utils import is_fridge_eoj

DEFAULT_TEMPERATURE = 4.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PanasonicConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan climate from a config entry."""
    coordinators = entry.runtime_data.coordinators

    entities = []
    for coordinator in coordinators.values():
        if is_fridge_eoj(coordinator.eoj):
            entities.append(PanasonicClimate(coordinator))

    async_add_entities(entities)

    # Register entity-level cooling_assist service
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "cooling_assist",
        {
            vol.Required("mode"): cv.string,
            vol.Optional("time", default=0): vol.Coerce(int),
            vol.Optional("second", default=0): vol.Coerce(int),
        },
        "async_cooling_assist",
    )


class PanasonicClimate(PanasonicEntity, ClimateEntity):
    """Representation of a Panasonic fridge as a climate entity."""

    _attr_name = None
    _attr_icon = "mdi:fridge-outline"
    _attr_translation_key = "panasonic_fridge"
    _attr_supported_features = ClimateEntityFeature.PRESET_MODE
    _attr_hvac_modes = [HVACMode.AUTO]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_preset_modes = ["off", "quench", "cold", "frozen"]

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_climate"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current operation mode."""
        return HVACMode.AUTO

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self.coordinator.data.get("device_status", {}).get("cooloven_mode")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "raw_operation_mode": self.coordinator.data.get("device_status", {}).get("operation_mode"),
            "appliance_id": self.coordinator.appliance_id,
        }

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode for cooling assist."""
        if preset_mode == "off":
            await self.coordinator.async_control_cooling_assist("off", 0, 0)
        else:
            time_val, sec_val = get_default_cooling_assist_time(preset_mode)
            await self.coordinator.async_control_cooling_assist(preset_mode, time_val, sec_val)

    async def async_cooling_assist(self, mode: str, time: int = 0, second: int = 0) -> None:
        """Execute cooling assist directly via coordinator."""
        await self.coordinator.async_control_cooling_assist(mode, time, second)