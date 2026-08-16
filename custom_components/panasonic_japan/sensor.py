"""Sensor platform for Panasonic Japan."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTR_APPLIANCE_ID, ATTR_PRODUCT_CODE, DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Japan sensors from a config entry."""
    coordinators: dict[str, PanasonicDataUpdateCoordinator] = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    for coordinator in coordinators.values():
        if (coordinator.eoj or "").upper() == "03B7":
            sensors.extend(
                [
                    PanasonicCostReductionSensor(coordinator),
                    PanasonicOperationModeSensor(coordinator),
                    PanasonicFirmwareSensor(coordinator),
                    PanasonicCoolovenStateSensor(coordinator),
                    PanasonicDoorOpenSensor(coordinator),
                ]
            )

    async_add_entities(sensors)


class PanasonicSensor(CoordinatorEntity[PanasonicDataUpdateCoordinator], SensorEntity):
    """Base class for Panasonic sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.appliance_id)},
            name=f"Panasonic Fridge ({coordinator.product_code})",
            manufacturer="Panasonic",
            model=coordinator.product_code,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        return {
            ATTR_APPLIANCE_ID: data.get("appliance_id", self.coordinator.appliance_id),
            ATTR_PRODUCT_CODE: data.get("product_code", self.coordinator.product_code),
        }


class PanasonicCostReductionSensor(PanasonicSensor):
    """Sensor for electricity cost reduction."""

    _attr_name = "Electricity Cost Reduction"
    _attr_native_unit_of_measurement = "yen"
    _attr_icon = "mdi:currency-jpy"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_cost_reduction"

    @property
    def native_value(self) -> int:
        """Return the cost reduction in yen."""
        data = self.coordinator.data or {}
        electricity_data = data.get("electricity", {})
        return electricity_data.get("current_reduction_amount", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        electricity_data = data.get("electricity", {})
        attrs.update(
            {
                "last_month_reduction": electricity_data.get(
                    "lastmonth_reduction_amount", 0
                ),
                "last_year_reduction": electricity_data.get(
                    "lastyear_reduction_amount", 0
                ),
            }
        )
        return attrs


class PanasonicOperationModeSensor(PanasonicSensor):
    """Sensor for operation mode."""

    _attr_name = "Operation Mode"
    _attr_icon = "mdi:air-conditioner"

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_operation_mode"

    @property
    def native_value(self) -> str:
        """Return the operation mode."""
        data = self.coordinator.data or {}
        device_status = data.get("device_status", {})
        return device_status.get("operation_mode", "unknown")

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        device_status = data.get("device_status", {})
        attrs.update(
            {
                "winter_setting": device_status.get("winter_setting_status", False),
                "house_sitting": device_status.get("house_sitting_status", False),
                "pre_cooling": device_status.get("pre_cooling_status", False),
                "outage_prepare": device_status.get("outage_prepare_status", False),
            }
        )
        return attrs


class PanasonicFirmwareSensor(PanasonicSensor):
    """Sensor for firmware version."""

    _attr_name = "Firmware Version"
    _attr_icon = "mdi:chip"

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_firmware_version"

    @property
    def native_value(self) -> str:
        """Return the firmware version."""
        data = self.coordinator.data or {}
        device_status = data.get("device_status", {})
        return device_status.get("firmware_current_version", "unknown")

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        device_status = data.get("device_status", {})
        attrs.update(
            {
                "latest_version": device_status.get("firmware_latest_version", ""),
                "update_status": device_status.get("firmware_update_status", ""),
            }
        )
        return attrs


class PanasonicCoolovenStateSensor(PanasonicSensor):
    """Representation of a Panasonic Cooloven State Sensor."""

    _attr_name = "Cooloven State"
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_cooloven_state"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        data = self.coordinator.data or {}
        device_status = data.get("device_status", {})
        return device_status.get("cooloven_mode", "off")

class PanasonicDoorOpenSensor(PanasonicSensor):
    """Sensor for door open count."""

    _attr_name = "Door Open Count"
    _attr_icon = "mdi:door-open"
    _attr_translation_key = "door_open_count"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: PanasonicDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_id}_door_open_count"

    @property
    def native_value(self) -> int:
        """Return the open count for the current day."""
        data = self.coordinator.data or {}
        door_data = data.get("door_open_info", {})
        
        # 週間リストから本日の日付に一致するデータを抽出
        weekly_list = door_data.get("weekly", {}).get("door_open_list", [])
        today_str = dt_util.now().strftime('%Y-%m-%d')
        
        entry = next((item for item in weekly_list if item.get("date") == today_str), None)
        return entry.get("open_count", 0) if entry else 0

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes with weekly history and average."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        door_data = data.get("door_open_info", {})
        
        weekly_data = door_data.get("weekly", {})
        attrs.update({
            "weekly_door_open_list": weekly_data.get("door_open_list", []),
            "average_open_count": weekly_data.get("average_open_count", 0),
        })
        return attrs