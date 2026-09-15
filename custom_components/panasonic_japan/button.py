"""Button platform for the cooling assist integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PanasonicDataUpdateCoordinator
from .data import PanasonicConfigEntry
from .entity import PanasonicEntity
from .utils import is_fridge_eoj

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PanasonicConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinators = entry.runtime_data.coordinators

    entities = [
        CoolingAssistButton(coordinator)
        for coordinator in coordinators.values()
        if is_fridge_eoj(coordinator.eoj)
    ]
    async_add_entities(entities)


class CoolingAssistButton(PanasonicEntity, ButtonEntity):
    """Representation of the Cooling Assist trigger button."""

    _attr_translation_key = "cooling_assist"

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_cooling_assist"
        self._attr_icon = "mdi:snowflake"

    async def async_press(self) -> None:
        """Handle the button press action."""
        await self.coordinator.async_execute_cooling_assist()