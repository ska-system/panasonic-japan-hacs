"""Climate platform for Panasonic Japan."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform, config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator

DEFAULT_TEMPERATURE = 4.0

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan climate from a config entry."""
    coordinators: dict[str, PanasonicDataUpdateCoordinator] = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for coordinator in coordinators.values():
        if (coordinator.eoj or "").upper() == "03B7":
            entities.append(PanasonicClimate(coordinator))

    async_add_entities(entities)

    # エンティティ固有のサービスを登録
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


class PanasonicClimate(CoordinatorEntity[PanasonicDataUpdateCoordinator], ClimateEntity):
    """Representation of a Panasonic fridge as a climate entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:fridge-outline"
    _attr_translation_key = "panasonic_fridge"
    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.AUTO]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_preset_modes = ["off", "quench", "cold", "frozen"]

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

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
        }

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode by calling the set_cooloven service."""
        service_data = {
            "mode": preset_mode,
            "appliance_id": self.coordinator.appliance_id,
        }
        if preset_mode == "quench":
            service_data["time"] = 5
            service_data["second"] = 0
        elif preset_mode == "cold":
            service_data["time"] = 15
        elif preset_mode in ("freeze", "frozen"):
            service_data["time"] = 45

        await self.hass.services.async_call(
            DOMAIN,
            "set_cooloven",
            service_data,
            blocking=True,
        )

    async def async_cooling_assist(self, mode: str, time: int = 0, second: int = 0) -> None:
        """Execute cooling assist by calling the set_cooloven service."""
        service_data = {
            "mode": mode,
            "appliance_id": self.coordinator.appliance_id,
        }
        if mode != "off":
            service_data["time"] = time
        if mode == "quench":
            service_data["second"] = second

        await self.hass.services.async_call(
            DOMAIN,
            "set_cooloven",
            service_data,
            blocking=True,
        )