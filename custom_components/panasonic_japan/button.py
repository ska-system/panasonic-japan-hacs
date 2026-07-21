"""Button platform for Panasonic Japan."""
from __future__ import annotations

import logging
from homeassistant.components.button import ButtonEntity
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
    """Set up Panasonic Japan buttons from a config entry."""
    coordinator: PanasonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PanasonicCoolovenExecuteButton(coordinator),
    ]
    async_add_entities(entities)


class PanasonicCoolovenExecuteButton(CoordinatorEntity[PanasonicDataUpdateCoordinator], ButtonEntity):
    """Button entity to execute cooloven control with cached values."""

    _attr_has_entity_name = True
    _attr_name = "Start Cooling Assist"
    _attr_icon = "mdi:play"

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_cooloven_execute"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    async def async_press(self) -> None:
        """Send cached cooloven parameters to the API."""
        payload = {
            "cooloven_mode": self.coordinator.pending_cooloven_mode,
            "cooloven_time": int(self.coordinator.pending_cooloven_time),
            "cooloven_second": int(self.coordinator.pending_cooloven_second),
        }
        
        await self.hass.async_add_executor_job(
            self.coordinator.api.control_device,
            self.coordinator.appliance_id,
            payload,
        )
        await self.coordinator.async_request_refresh()