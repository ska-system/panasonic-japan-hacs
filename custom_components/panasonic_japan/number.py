"""Number platform for Panasonic Japan."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

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
    native_min_value: int = 0
    native_max_value: int = 59
    native_step: int = 1
    native_unit_of_measurement: str | None = None
    mode: NumberMode = NumberMode.AUTO
    entity_category: EntityCategory | None = None


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
        native_min_value=1,
        native_max_value=72,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
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
        self._attr_native_value = 0

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        custom_data = self.hass.data.setdefault(DOMAIN, {}).setdefault(f"{self._entry_id}_custom", {})
        if "number_entities" not in custom_data:
            custom_data["number_entities"] = {}
        custom_data["number_entities"][self.entity_description.key] = self

    def _get_current_mode(self) -> str:
        """Get current cooling assist mode."""
        custom_data = self.hass.data.get(DOMAIN, {}).get(f"{self._entry_id}_custom", {})
        return custom_data.get("cooling_assist_mode", "off")

    @property
    def native_min_value(self) -> float:
        """Return dynamic minimum value based on mode."""
        if self.entity_description.key == "notify_door_open_time":
            return 1
        mode = self._get_current_mode()
        if self.entity_description.key == "cooling_assist_time":
            if mode == "off":
                return 0
            elif mode == "quench":
                return 0
            elif mode == "cold":
                return 10
            elif mode in ("frozen", "freeze"):
                return 30
        elif self.entity_description.key == "cooling_assist_second":
            return 0
        return 0

    @property
    def native_max_value(self) -> float:
        """Return dynamic maximum value based on mode."""
        if self.entity_description.key == "notify_door_open_time":
            return 72
        mode = self._get_current_mode()
        if self.entity_description.key == "cooling_assist_time":
            if mode == "off":
                return 0
            elif mode == "quench":
                return 10
            elif mode == "cold":
                return 30
            elif mode in ("frozen", "freeze"):
                return 60
        elif self.entity_description.key == "cooling_assist_second":
            if mode in ("cold", "frozen", "freeze", "off"):
                return 0
            elif mode == "quench":
                return 50
        return 0

    @property
    def native_step(self) -> float:
        """Return step value."""
        if self.entity_description.key == "cooling_assist_second":
            return 10
        return 1

    @property
    def native_value(self) -> float | None:
        """Return current value."""
        if self.entity_description.key == "notify_door_open_time":
            param_list = self.coordinator.data.get("notification_settings", {}).get("param_list", [])
            for item in param_list:
                if item.get("param_name") == "doorOpenInfo":
                    return item.get("param_time", 1)
            return 1
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value locally."""
        min_v = self.native_min_value
        max_v = self.native_max_value
        
        # 値のクランプ処理
        value = max(min_v, min(int(value), max_v))
        
        if self.entity_description.key == "cooling_assist_second":
            value = (round(value / 10)) * 10

        # ドアモニター設定時間の場合は、スイッチの状態を確認してAPIへ反映
        if self.entity_description.key == "door_open_time":
            current_settings = dict(self.coordinator.data.get("notification_settings", {}))
            if "param_list" in current_settings:
                for item in current_settings["param_list"]:
                    if item.get("param_name") == "doorOpenInfo":
                        # 現在のスイッチ状態を取得
                        is_on = item.get("param_value", False)
                        
                        # ONの時のみ param_time を設定し、OFFの時は設定しない
                        if is_on:
                            item["param_time"] = int(value)
                        else:
                            # OFFの場合は param_time を削除する（キー自体を除外）
                            if "param_time" in item:
                                del item["param_time"]
                        break
            
            await self.hass.async_add_executor_job(
                self.coordinator.api.update_notification_settings,
                self.coordinator.appliance_id,
                current_settings,
            )
            await self.coordinator.async_request_refresh()
            return

        self._attr_native_value = value
        self.async_write_ha_state()