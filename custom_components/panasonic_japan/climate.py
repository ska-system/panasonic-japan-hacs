"""Climate platform for Panasonic Japan."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator

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


class PanasonicClimate(CoordinatorEntity[PanasonicDataUpdateCoordinator], ClimateEntity):
    """Representation of a Panasonic fridge as a climate entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.COOL, HVACMode.OFF]

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
        # 実際の実装では device_status から状態を判定してください
        return HVACMode.COOL

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        # 冷蔵庫の温度センサーキーを指定
        return self.coordinator.data.get("device_status", {}).get("current_temp")

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return self.coordinator.data.get("device_status", {}).get("target_temp")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        # モード切替のAPI呼び出しを記述
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temp = kwargs.get("temperature")
        await self.hass.async_add_executor_job(
            self.coordinator.api.control_device,
            self.coordinator.appliance_id,
            {"temperature": temp},
        )
        await self.coordinator.async_request_refresh()