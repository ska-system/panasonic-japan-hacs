"""Button platform for the cooling assist integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    async_add_entities([CoolingAssistButton()])

class CoolingAssistButton(ButtonEntity):
    """Representation of the Cooling Assist trigger button."""

    _attr_name = "Cooling Assist"
    _attr_unique_id = "cooling_assist_button"
    _attr_icon = "mdi:snowflake"

    async def async_press(self) -> None:
        """Handle the button press action."""
        # 現時点ではダイアログ確認用のため、アクションはプレースホルダーとする
        pass