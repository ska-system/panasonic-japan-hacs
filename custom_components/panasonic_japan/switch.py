"""Switch platform for Panasonic Japan."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PanasonicSwitchDescription(SwitchEntityDescription):
    """Describe a Panasonic fridge switch."""
    status_key: str = ""
    data_source: str = "device_status"


SWITCHES: tuple[PanasonicSwitchDescription, ...] = (
    PanasonicSwitchDescription(
        key="fast_ice",
        translation_key = "fast_ice_status",
        icon="mdi:snowflake-variant",
        status_key="fast_ice_status",
    ),
    PanasonicSwitchDescription(
        key="stop_ice",
        translation_key = "stop_ice_status",
        icon="mdi:snowflake-off",
        status_key="stop_ice_status",
    ),
    PanasonicSwitchDescription(
        key="fresh_frozen",
        translation_key = "fresh_frozen_status",
        icon="mdi:fridge-industrial",
        status_key="fresh_frozen_status",
    ),
    PanasonicSwitchDescription(
        key="econavi_lamp",
        translation_key = "econavi_lamp_status",
        icon="mdi:lightbulb",
        status_key="econavi_lamp_status",
    ),
    PanasonicSwitchDescription(
        key="notify_water_shortage",
        translation_key="notify_water_shortage",
        icon="mdi:water-alert",
        status_key="waterShortage",
        entity_category=EntityCategory.CONFIG,
        data_source="notification_settings",
    ),
    PanasonicSwitchDescription(
        key="notify_cool_oven",
        translation_key="notify_cool_oven",
        icon="mdi:snowflake-alert",
        status_key="coolOven",
        entity_category=EntityCategory.CONFIG,
        data_source="notification_settings",
    ),
    PanasonicSwitchDescription(
        key="notify_ice_completed",
        translation_key="notify_ice_completed",
        icon="mdi:fridge-alert",
        status_key="iceCompleted",
        entity_category=EntityCategory.CONFIG,
        data_source="notification_settings",
    ),
    PanasonicSwitchDescription(
        key="notify_error_occurred",
        translation_key="notify_error_occurred",
        icon="mdi:alert-circle",
        status_key="errorOccured",
        entity_category=EntityCategory.CONFIG,
        data_source="notification_settings",
    ),
    PanasonicSwitchDescription(
        key="notify_door_open",
        translation_key="notify_door_open",
        icon="mdi:door-open",
        status_key="doorOpenInfo",
        entity_category=EntityCategory.CONFIG,
        data_source="notification_settings",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan switches from a config entry."""
    coordinator: PanasonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Only add switches whose status key is present in coordinator data
    device_status = coordinator.data.get("device_status", {})
    notification_settings = coordinator.data.get("notification_settings", {})

    entities = []
    for description in SWITCHES:
        source_data = (
            notification_settings
            if description.data_source == "notification_settings"
            else device_status
        )
        if description.status_key in source_data:
            entities.append(PanasonicSwitch(coordinator, description))

    async_add_entities(entities)

class PanasonicSwitch(CoordinatorEntity[PanasonicDataUpdateCoordinator], SwitchEntity):
    """A controllable boolean switch on the Panasonic fridge."""

    entity_description: PanasonicSwitchDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PanasonicDataUpdateCoordinator,
        description: PanasonicSwitchDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.appliance_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    @property
    def is_on(self) -> bool | None:
        """Return current state."""
        source = self.entity_description.data_source
        return self.coordinator.data.get(source, {}).get(
            self.entity_description.status_key
        )
    @property
    def is_on(self) -> bool | None:
        """Return current state."""
        if self.entity_description.data_source == "notification_settings":
            param_list = self.coordinator.data.get("notification_settings", {}).get("param_list", [])
            for item in param_list:
                if item.get("param_name") == self.entity_description.status_key:
                    return item.get("param_value")
            return False # 見つからない場合

        # 通常のデバイスステータスの場合
        return self.coordinator.data.get("device_status", {}).get(self.entity_description.status_key)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self._control({self.entity_description.status_key: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self._control({self.entity_description.status_key: False})

    async def _control(self, payload: dict[str, Any]) -> None:
        if self.entity_description.data_source == "notification_settings":
            # 1. 現在の全通知設定を取得 (取得済みのJSON構造)
            current_settings = dict(self.coordinator.data.get("notification_settings", {}))
            
            # 2. payload から今回の変更値を取得 (例: {"waterShortage": True} -> True)
            target_key = self.entity_description.status_key
            target_value = payload.get(target_key)

            # 3. param_list 内の値を更新
            if "param_list" in current_settings:
                for item in current_settings["param_list"]:
                    if item.get("param_name") == target_key:
                        item["param_value"] = target_value
                        break
            # 4. APIへ送信
            await self.hass.async_add_executor_job(
                self.coordinator.api.update_notification_settings,
                self.coordinator.appliance_id,
                current_settings,
            )
        else:
            await self.hass.async_add_executor_job(
                self.coordinator.api.control_device,
                self.coordinator.appliance_id,
                payload,
            )
        await self.coordinator.async_request_refresh()