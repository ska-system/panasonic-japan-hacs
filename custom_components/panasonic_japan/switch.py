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

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PanasonicSwitchDescription(SwitchEntityDescription):
    """Describe a Panasonic fridge switch."""
    status_key: str = ""


SWITCHES: tuple[PanasonicSwitchDescription, ...] = (
    PanasonicSwitchDescription(
        key="fast_ice",
        translation_key = "fast_ice",
        # name="Fast Ice",
        icon="mdi:snowflake-variant",
        status_key="fast_ice_status",
    ),
    PanasonicSwitchDescription(
        key="stop_ice",
        translation_key = "stop_ice",
        # name="Stop Ice",
        icon="mdi:snowflake-off",
        status_key="stop_ice_status",
    ),
    PanasonicSwitchDescription(
        key="fresh_frozen",
        translation_key = "fresh_frozen",
        # name="Fresh Frozen",
        icon="mdi:fridge-industrial",
        status_key="fresh_frozen_status",
    ),
    PanasonicSwitchDescription(
        key="econavi_lamp",
        translation_key = "econavi_lamp",
        # name="Econavi Lamp",
        icon="mdi:lightbulb",
        status_key="econavi_lamp_status",
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
    entities = [
        PanasonicSwitch(coordinator, description)
        for description in SWITCHES
        if description.status_key in device_status
    ]
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
        return self.coordinator.data.get("device_status", {}).get(
            self.entity_description.status_key
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self._control({self.entity_description.status_key: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self._control({self.entity_description.status_key: False})

    async def _control(self, payload: dict[str, Any]) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.api.control_device,
            self.coordinator.appliance_id,
            payload,
        )
        await self.coordinator.async_request_refresh()
