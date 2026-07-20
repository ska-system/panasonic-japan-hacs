"""Select platform for Panasonic Japan."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PanasonicSelectDescription(SelectEntityDescription):
    """Describe a Panasonic fridge select entity."""
    status_key: str = ""
    options: list[str] = field(default_factory=list)


SELECTS: tuple[PanasonicSelectDescription, ...] = (
    PanasonicSelectDescription(
        key="partial_mode",
        translation_key="partial_mode",
        icon="mdi:fridge-bottom",
        status_key="partial_mode",
        options=["chilled", "weak", "medium", "strong"],
    ),
    PanasonicSelectDescription(
        key="cold_room_mode",
        translation_key="cold_room_mode",
        icon="mdi:thermometer",
        status_key="cold_room_mode",
        options=["weak", "medium", "strong"],
    ),
    PanasonicSelectDescription(
        key="freezing_room_mode",
        translation_key="freezing_room_mode",
        # name="Freezer Temperature",
        icon="mdi:thermometer-minus",
        status_key="freezing_room_mode",
        options=["weak", "medium", "strong"],
    ),
    PanasonicSelectDescription(
        key="coldroom_light_mode",
        translation_key="coldroom_light_mode",
        # name="Cold Room Light",
        icon="mdi:lightbulb",
        status_key="coldroom_light_mode",
        options=["off", "dark", "bright"],
    ),
    PanasonicSelectDescription(
        key="pcroom_light_mode",
        translation_key="pcroom_light_mode",
        # name="PC Room Light",
        icon="mdi:lightbulb-outline",
        status_key="pcroom_light_mode",
        options=["off", "dark", "bright"],
    ),
    PanasonicSelectDescription(
        key="door_alarms_mode",
        translation_key="door_alarms_mode",
        # name="Door Alarm",
        icon="mdi:alarm-light",
        status_key="door_alarms_mode",
        options=["off", "weak", "medium", "strong"],
    ),
    PanasonicSelectDescription(
        key="cooloven_lamp_mode",
        translation_key="cooloven_lamp_mode",
        # name="Cooling Assist Lamp",
        icon="mdi:lightbulb",
        status_key="cooloven_lamp_mode",
        options=["off", "dark", "bright"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan selects from a config entry."""
    coordinator: PanasonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    device_status = coordinator.data.get("device_status", {})
    entities = [
        PanasonicSelect(coordinator, description)
        for description in SELECTS
        if description.status_key in device_status
    ]
    async_add_entities(entities)


class PanasonicSelect(CoordinatorEntity[PanasonicDataUpdateCoordinator], SelectEntity):
    """A mode selector for the Panasonic fridge."""

    entity_description: PanasonicSelectDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PanasonicDataUpdateCoordinator,
        description: PanasonicSelectDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.appliance_id}_{description.key}"
        self._attr_options = description.options
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        return self.coordinator.data.get("device_status", {}).get(
            self.entity_description.status_key
        )

    async def async_select_option(self, option: str) -> None:
        """Send selected option to the fridge."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.control_device,
            self.coordinator.appliance_id,
            {self.entity_description.status_key: option},
        )
        await self.coordinator.async_request_refresh()
