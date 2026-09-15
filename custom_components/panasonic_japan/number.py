"""Number platform for Panasonic Japan."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .cooling_assist import get_cooling_assist_bounds
from .coordinator import PanasonicDataUpdateCoordinator
from .data import PanasonicConfigEntry
from .entity import PanasonicEntity
from .utils import is_fridge_eoj

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PanasonicNumberDescription(NumberEntityDescription):
    """Describe a Panasonic fridge number entity."""

    native_min_value: int = 0
    native_max_value: int = 59
    native_step: int = 1
    native_unit_of_measurement: str | None = None
    mode: NumberMode = NumberMode.AUTO
    entity_category: EntityCategory | None = None
    max_value_fn: Any | None = None
    min_value_fn: Any | None = None


NUMBERS: tuple[PanasonicNumberDescription, ...] = (
    PanasonicNumberDescription(
        key="cooling_assist_time",
        translation_key="cooling_assist_time",
        icon="mdi:timer-outline",
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
    ),
    PanasonicNumberDescription(
        key="cooling_assist_second",
        translation_key="cooling_assist_second",
        icon="mdi:timer-sand",
        native_min_value=0,
        native_max_value=59,
        native_step=10,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
    ),
    PanasonicNumberDescription(
        key="notify_door_open_time",
        translation_key="notify_door_open_time",
        icon="mdi:timer-alert",
        native_min_value=0,
        native_max_value=72,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PanasonicConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan number platform."""
    coordinators = entry.runtime_data.coordinators

    entities = []
    for coordinator in coordinators.values():
        if is_fridge_eoj(coordinator.eoj):
            for description in NUMBERS:
                entities.append(PanasonicNumber(coordinator, description))

    async_add_entities(entities)


class PanasonicNumber(PanasonicEntity, NumberEntity):
    """Representation of a Panasonic Number entity."""

    entity_description: PanasonicNumberDescription

    def __init__(
        self,
        coordinator: PanasonicDataUpdateCoordinator,
        description: PanasonicNumberDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.appliance_id}_{description.key}"
        self._attr_native_step = description.native_step
        if description.entity_category:
            self._attr_entity_category = description.entity_category

        self._attr_native_value = 0.0

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        if self.entity_description.key in ("cooling_assist_time", "cooling_assist_second"):
            self.async_on_remove(
                self.coordinator.register_cooling_assist_listener(self.async_write_ha_state)
            )

    @property
    def native_min_value(self) -> float:
        """Return dynamic minimum value based on mode."""
        if self.entity_description.key == "notify_door_open_time":
            return 0.0
        bounds = get_cooling_assist_bounds(self.coordinator.cooling_assist_mode)
        if self.entity_description.key == "cooling_assist_time":
            return float(bounds["min_time"])
        if self.entity_description.key == "cooling_assist_second":
            return float(bounds["min_sec"])
        return 0.0

    @property
    def native_max_value(self) -> float:
        """Return dynamic maximum value based on mode."""
        if self.entity_description.key == "notify_door_open_time":
            return 72.0
        bounds = get_cooling_assist_bounds(self.coordinator.cooling_assist_mode)
        if self.entity_description.key == "cooling_assist_time":
            return float(bounds["max_time"])
        if self.entity_description.key == "cooling_assist_second":
            return float(bounds["max_sec"])
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
        if self.entity_description.key == "notify_door_open_time":
            if not self.coordinator.data:
                return 0.0
            param_list = self.coordinator.data.get("notification_settings", {}).get("param_list", [])
            for item in param_list:
                if item.get("param_name") == "doorOpenInfo":
                    if "param_time" in item:
                        return float(item.get("param_time", 1))
                    return 0.0
            return 0.0
        if self.entity_description.key == "cooling_assist_time":
            return float(self.coordinator.cooling_assist_time)
        if self.entity_description.key == "cooling_assist_second":
            return float(self.coordinator.cooling_assist_second)
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self.entity_description.key == "notify_door_open_time":
            if not self.coordinator.data:
                return
            current_settings = dict(self.coordinator.data.get("notification_settings", {}))
            if "param_list" in current_settings:
                for item in current_settings["param_list"]:
                    if item.get("param_name") == "doorOpenInfo":
                        if int(value) == 0:
                            item["param_value"] = False
                            if "param_time" in item:
                                del item["param_time"]
                        else:
                            item["param_value"] = True
                            item["param_time"] = int(value)
                        break

            await self.coordinator.api.update_notification_settings(
                self.coordinator.appliance_id,
                current_settings,
            )
            await self.coordinator.async_request_refresh()
            return

        if self.entity_description.key == "cooling_assist_time":
            self.coordinator.set_cooling_assist_time(int(value))
        elif self.entity_description.key == "cooling_assist_second":
            self.coordinator.set_cooling_assist_second(int(value))