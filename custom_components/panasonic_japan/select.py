"""Select platform for Panasonic Japan."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    entity_category: EntityCategory | None = None


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
        icon="mdi:thermometer-minus",
        status_key="freezing_room_mode",
        options=["weak", "medium", "strong"],
    ),
    PanasonicSelectDescription(
        key="coldroom_light_mode",
        translation_key="coldroom_light_mode",
        icon="mdi:lightbulb",
        status_key="coldroom_light_mode",
        options=["off", "dark", "bright"],
    ),
    PanasonicSelectDescription(
        key="pcroom_light_mode",
        translation_key="pcroom_light_mode",
        icon="mdi:lightbulb-outline",
        status_key="pcroom_light_mode",
        options=["off", "dark", "bright"],
    ),
    PanasonicSelectDescription(
        key="door_alarms_mode",
        translation_key="door_alarms_mode",
        icon="mdi:alarm-light",
        status_key="door_alarms_mode",
        options=["medium", "big"],
    ),
    PanasonicSelectDescription(
        key="cooloven_lamp_mode",
        translation_key="cooloven_lamp_mode",
        icon="mdi:lightbulb",
        status_key="cooloven_lamp_mode",
        options=["off", "dark", "bright"],
    ),
    PanasonicSelectDescription(
        key="cooling_assist_mode",
        translation_key="cooling_assist_mode",
        icon="mdi:snowflake",
        status_key="",
        options=["off", "quench", "cold", "frozen"],
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan selects from a config entry."""
    coordinators: dict[str, PanasonicDataUpdateCoordinator] = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for coordinator in coordinators.values():
        if (coordinator.eoj or "").upper() == "03B7":
            device_status = (coordinator.data or {}).get("device_status", {})
            for description in SELECTS:
                if description.status_key:
                    if description.status_key in device_status:
                        entities.append(PanasonicSelect(coordinator, description, entry.entry_id))
                else:
                    entities.append(PanasonicSelect(coordinator, description, entry.entry_id))

    async_add_entities(entities)


class PanasonicSelect(CoordinatorEntity[PanasonicDataUpdateCoordinator], SelectEntity):
    """A mode selector for the Panasonic fridge."""

    entity_description: PanasonicSelectDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PanasonicDataUpdateCoordinator,
        description: PanasonicSelectDescription,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry_id = entry_id
        self._attr_unique_id = f"{coordinator.appliance_id}_{description.key}"
        self._attr_options = description.options
        if description.entity_category:
            self._attr_entity_category = description.entity_category
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            via_device=(DOMAIN, coordinator.config_entry.entry_id),
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )
        if not description.status_key and description.options:
            self._attr_current_option = description.options[0]

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        if not self.entity_description.status_key and self.entity_description.key == "cooling_assist_mode":
            custom_data = self.hass.data.setdefault(DOMAIN, {}).setdefault(f"{self._entry_id}_custom", {})
            custom_data["cooling_assist_mode"] = self._attr_current_option

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        if self.entity_description.status_key:
            if not self.coordinator.data:
                return None
            return self.coordinator.data.get("device_status", {}).get(
                self.entity_description.status_key
            )
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Send selected option to the fridge or update local state."""
        if self.entity_description.status_key:
            await self.hass.async_add_executor_job(
                self.coordinator.api.control_device,
                self.coordinator.appliance_id,
                {self.entity_description.status_key: option},
            )
            await self.coordinator.async_request_refresh()
        else:
            self._attr_current_option = option
            
            if self.entity_description.key == "cooling_assist_mode":
                custom_data = self.hass.data.setdefault(DOMAIN, {}).setdefault(f"{self._entry_id}_custom", {})
                custom_data["cooling_assist_mode"] = option

                number_entities = custom_data.get("number_entities", {})
                time_ent = number_entities.get("cooling_assist_time")
                sec_ent = number_entities.get("cooling_assist_second")

                if option == "off":
                    if time_ent:
                        time_ent._attr_native_value = 0.0
                        time_ent.async_write_ha_state()
                    if sec_ent:
                        sec_ent._attr_native_value = 0.0
                        sec_ent.async_write_ha_state()
                elif option == "quench":
                    if time_ent:
                        time_ent._attr_native_value = 5.0
                        time_ent.async_write_ha_state()
                    if sec_ent:
                        sec_ent._attr_native_value = 0.0
                        sec_ent.async_write_ha_state()
                elif option == "cold":
                    if time_ent:
                        time_ent._attr_native_value = 15.0
                        time_ent.async_write_ha_state()
                    if sec_ent:
                        sec_ent._attr_native_value = 0.0
                        sec_ent.async_write_ha_state()
                elif option in ("frozen", "freeze"):
                    if time_ent:
                        time_ent._attr_native_value = 45.0
                        time_ent.async_write_ha_state()
                    if sec_ent:
                        sec_ent._attr_native_value = 0.0
                        sec_ent.async_write_ha_state()

            self.async_write_ha_state()