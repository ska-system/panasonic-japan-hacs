"""Button platform for the cooling assist integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up the button platform."""
    coordinator: PanasonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CoolingAssistButton(coordinator)])

class CoolingAssistButton(CoordinatorEntity[PanasonicDataUpdateCoordinator], ButtonEntity):
    """Representation of the Cooling Assist trigger button."""

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_name = "Cooling Assist"
        self._attr_unique_id = f"{coordinator.appliance_id}_cooling_assist"
        self._attr_icon = "mdi:snowflake"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    async def async_press(self) -> None:
        """Handle the button press action."""
        pass