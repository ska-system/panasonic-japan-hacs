"""Base entity for Panasonic Japan integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EOJ_NAME_MAP
from .coordinator import PanasonicDataUpdateCoordinator
from .utils import normalize_eoj


class PanasonicEntity(CoordinatorEntity[PanasonicDataUpdateCoordinator]):
    """Base class for all Panasonic Japan entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        eoj_upper = normalize_eoj(coordinator.eoj)
        device_type_name = EOJ_NAME_MAP.get(eoj_upper, "Appliance")
        device_name = f"Panasonic {device_type_name} ({coordinator.product_code})"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=device_name,
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    @property
    def appliance_id(self) -> str:
        """Return the appliance ID."""
        return self.coordinator.appliance_id
