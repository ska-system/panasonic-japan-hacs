"""Number platform for Panasonic Japan."""
from __future__ import annotations

import logging
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan numbers from a config entry."""
    coordinator: PanasonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PanasonicCoolovenTimeMinuteNumber(coordinator),
        PanasonicCoolovenTimeSecondNumber(coordinator),
    ]
    async_add_entities(entities)


class PanasonicCoolovenTimeMinuteNumber(CoordinatorEntity[PanasonicDataUpdateCoordinator], NumberEntity):
    """Number entity for pending cooloven time (minutes)."""

    _attr_has_entity_name = True
    _attr_name = "Cooling Assist Minutes"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 0
    _attr_native_max_value = 60
    _attr_native_step = 1

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_pending_cooloven_time"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    @property
    def native_value(self) -> float:
        """Return the current value from coordinator cache."""
        return float(self.coordinator.pending_cooloven_time)

    async def async_set_native_value(self, value: float) -> None:
        """Update the cached minutes value."""
        self.coordinator.pending_cooloven_time = int(value)
        self.async_write_ha_state()


class PanasonicCoolovenTimeSecondNumber(CoordinatorEntity[PanasonicDataUpdateCoordinator], NumberEntity):
    """Number entity for pending cooloven time (seconds)."""

    _attr_has_entity_name = True
    _attr_name = "Cooling Assist Seconds"
    _attr_icon = "mdi:timer-sand"
    _attr_native_min_value = 0
    _attr_native_max_value = 50
    _attr_native_step = 10

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_pending_cooloven_second"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    @property
    def native_value(self) -> float:
        """Return the current value from coordinator cache."""
        return float(self.coordinator.pending_cooloven_second)

    async def async_set_native_value(self, value: float) -> None:
        """Update the cached seconds value."""
        self.coordinator.pending_cooloven_second = int(value)
        self.async_write_ha_state()