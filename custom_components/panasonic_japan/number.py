"""Number platform for Panasonic Japan."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PanasonicNumberDescription(NumberEntityDescription):
    """Describe a Panasonic fridge number entity."""
    native_min_value: float = 0.0
    native_max_value: float = 59.0
    native_step: float = 1.0
    native_unit_of_measurement: str | None = None
    mode: NumberMode = NumberMode.AUTO
    entity_category: EntityCategory | None = None


NUMBERS: tuple[PanasonicNumberDescription, ...] = (
    PanasonicNumberDescription(
        key="cooling_assist_time",
        translation_key="cooling_assist_time",
        icon="mdi:timer-outline",
        native_min_value=0.0,
        native_max_value=60.0,
        native_step=1.0,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_category=EntityCategory.CONFIG,
    ),
    PanasonicNumberDescription(
        key="cooling_assist_second",
        translation_key="cooling_assist_second",
        icon="mdi:timer-sand",
        native_min_value=0.0,
        native_max_value=59.0,
        native_step=10.0,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan numbers from a config entry."""
    coordinator: PanasonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PanasonicNumber(coordinator, description, entry.entry_id)
        for description in NUMBERS
    ]

    async_add_entities(entities)


class PanasonicNumber(CoordinatorEntity[PanasonicDataUpdateCoordinator], NumberEntity):
    """A number setting for the Panasonic fridge."""

    entity_description: PanasonicNumberDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PanasonicDataUpdateCoordinator,
        description: PanasonicNumberDescription,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry_id = entry_id
        self._attr_unique_id = f"{coordinator.appliance_id}_{description.key}"
        self._attr_native_step = description.native_step
        if description.entity_category:
            self._attr_entity_category = description.entity_category

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )
        self._attr_native_value = 0.0

        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}
        if self._entry_id not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][self._entry_id] = {}
        
        if "number_entities" not in self.hass.data[DOMAIN][self._entry_id]:
            self.hass.data[DOMAIN][self._entry_id]["number_entities"] = {}
        self.hass.data[DOMAIN][self._entry_id]["number_entities"][description.key] = self

    def _get_current_mode(self) -> str:
        """Get current cooling assist mode."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        return entry_data.get("cooling_assist_mode", "off")

    @property
    def native_min_value(self) -> float:
        """Return dynamic minimum value based on mode."""
        mode = self._get_current_mode()
        if self.entity_description.key == "cooling_assist_time":
            if mode == "off":
                return 0.0
            elif mode == "quench":
                return 0.0
            elif mode == "cold":
                return 10.0
            elif mode in ("frozen", "freeze"):
                return 30.0
        elif self.entity_description.key == "cooling_assist_second":
            return 0.0
        return 0.0

    @property
    def native_max_value(self) -> float:
        """Return dynamic maximum value based on mode."""
        mode = self._get_current_mode()
        if self.entity_description.key == "cooling_assist_time":
            if mode == "off":
                return 0.0
            elif mode == "quench":
                return 10.0
            elif mode == "cold":
                return 30.0
            elif mode in ("frozen", "freeze"):
                return 60.0
        elif self.entity_description.key == "cooling_assist_second":
            if mode in ("cold", "frozen", "freeze", "off"):
                return 0.0
            elif mode == "quench":
                return 50.0
        return 0.0

    @property
    def native_step(self) -> float:
        """Return step value."""
        if self.entity_description.key == "cooling_assist_second":
            return 10.0
        return 1.0

    @property
    def native_value(self) -> float | None:
        """Return current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value locally with clamping/step adjustment."""
        min_v = self.native_min_value
        max_v = self.native_max_value
        if value < min_v:
            value = min_v
        if value > max_v:
            value = max_v
        
        if self.entity_description.key == "cooling_assist_second":
            value = (round(value / 10.0)) * 10.0

        self._attr_native_value = value
        self.async_write_ha_state()