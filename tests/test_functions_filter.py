"""Tests for device functions filtering across Home Assistant platforms."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from homeassistant.core import HomeAssistant
from custom_components.panasonic_japan.api import PanasonicAPI
from custom_components.panasonic_japan.coordinator import PanasonicDataUpdateCoordinator
from custom_components.panasonic_japan.switch import async_setup_entry as setup_switches
from custom_components.panasonic_japan.select import async_setup_entry as setup_selects
from custom_components.panasonic_japan.number import async_setup_entry as setup_numbers
from custom_components.panasonic_japan.sensor import async_setup_entry as setup_sensors
from custom_components.panasonic_japan.button import async_setup_entry as setup_buttons
from custom_components.panasonic_japan.climate import async_setup_entry as setup_climates


def create_mock_coordinator(hass, functions_dict=None):
    """Create a mock PanasonicDataUpdateCoordinator with given functions data."""
    api = MagicMock(spec=PanasonicAPI)
    config_entry = MagicMock()
    config_entry.data = {}

    appliance_info = {
        "appliance_id": "test_fridge_001",
        "product_code": "NR-F607HPX-N",
        "eoj": "03B7",
    }

    coord = PanasonicDataUpdateCoordinator(
        hass=hass,
        config_entry=config_entry,
        appliance_info=appliance_info,
        api=api,
    )

    coord.data = {
        "device_status": {
            "fast_ice_status": True,
            "stop_ice_status": False,
            "fresh_frozen_status": False,
            "econavi_lamp_status": True,
            "cold_room_mode": "medium",
            "freezing_room_mode": "medium",
            "coldroom_light_mode": "bright",
            "pcroom_light_mode": "bright",
            "partial_mode": "chilled",
            "door_alarms_mode": "medium",
            "cooloven_lamp_mode": "bright",
            "ice_making_mode": "normal",
            "nanoex": "on",
            "cooloven_mode": "off",
            "operation_mode": "normal",
            "firmware_current_version": "1.0.0",
        },
        "notification_settings": {
            "param_list": [
                {"param_name": "coolOven", "param_value": True},
                {"param_name": "doorOpenInfo", "param_value": True, "param_time": 1},
                {"param_name": "waterShortage", "param_value": False},
                {"param_name": "iceCompleted", "param_value": True},
                {"param_name": "errorOccured", "param_value": True},
            ]
        },
        "electricity": {"current_reduction_amount": 100},
        "door_open_info": {"weekly": {"door_open_list": [], "average_open_count": 0}},
        "functions": functions_dict,
    }
    return coord


def test_coordinator_is_function_supported(hass: HomeAssistant):
    """Coordinator の is_function_supported メソッドの動作検証。"""
    coord = create_mock_coordinator(
        hass,
        functions_dict={
            "coolOven": True,
            "freshFrozen": False,
            "doorOpenInfo": True,
        },
    )

    assert coord.is_function_supported("coolOven") is True
    assert coord.is_function_supported("freshFrozen") is False
    assert coord.is_function_supported("non_existent") is False
    assert coord.is_function_supported(None) is True


def test_coordinator_is_function_supported_none_functions(hass: HomeAssistant):
    """functions が None の場合のフォールバック検証。"""
    coord = create_mock_coordinator(hass, functions_dict=None)
    assert coord.is_function_supported("coolOven", default=True) is True
    assert coord.is_function_supported("coolOven", default=False) is False


async def test_platforms_filtering_with_user_fridge_model(hass: HomeAssistant):
    """NR-F607HPX-N の functions レスポンスに基づき、正しくエンティティがフィルタリングされることを検証。"""
    # ユーザーが提示した NR-F607HPX-N の functions
    functions_dict = {
        "coolOven": True,
        "recipe": True,
        "doorOpenInfo": True,
        "houseSitting": True,
        "initRequired": False,
        "quickButton": False,
        "firmwareUpdate": False,
        "partialFreezingRoom": False,
        "econaviLedOnOff": True,
        "pcroomLightMode": True,
        "freshFrozen": False,
        "fastGood": True,
        "outagePrepare": False,
        "aiCooling": False,
        "partialHalfDefrost": False,
        "scRoomTemperature": False,
        "demandResponse": False,
        "drAlarm": False,
    }

    coord = create_mock_coordinator(hass, functions_dict=functions_dict)
    mock_entry = MagicMock()
    mock_entry.runtime_data.coordinators = {coord.appliance_id: coord}

    # 1. Switch プラットフォーム
    switches = []
    await setup_switches(hass, mock_entry, lambda ents: switches.extend(ents))
    switch_keys = [s.entity_description.key for s in switches]

    # freshFrozen が False なので fresh_frozen は追加されない
    assert "fresh_frozen" not in switch_keys
    # econaviLedOnOff が True なので econavi_lamp は追加される
    assert "econavi_lamp" in switch_keys
    # coolOven が True なので notify_cool_oven は追加される
    assert "notify_cool_oven" in switch_keys
    # doorOpenInfo が True なので notify_door_open は追加される
    assert "notify_door_open" in switch_keys

    # 2. Select プラットフォーム
    selects = []
    await setup_selects(hass, mock_entry, lambda ents: selects.extend(ents))
    select_keys = [s.entity_description.key for s in selects]

    # partialFreezingRoom が False なので partial_mode は追加されない
    assert "partial_mode" not in select_keys
    # pcroomLightMode が True なので pcroom_light_mode は追加される
    assert "pcroom_light_mode" in select_keys
    # coolOven が True なので cooloven_lamp_mode, cooling_assist_mode は追加される
    assert "cooloven_lamp_mode" in select_keys
    assert "cooling_assist_mode" in select_keys

    # 3. Number プラットフォーム
    numbers = []
    await setup_numbers(hass, mock_entry, lambda ents: numbers.extend(ents))
    number_keys = [n.entity_description.key for n in numbers]

    assert "cooling_assist_time" in number_keys
    assert "cooling_assist_second" in number_keys
    assert "notify_door_open_time" in number_keys

    # 4. Button プラットフォーム
    buttons = []
    await setup_buttons(hass, mock_entry, lambda ents: buttons.extend(ents))
    assert len(buttons) == 1

    # 5. Climate プラットフォーム
    climates = []
    await setup_climates(hass, mock_entry, lambda ents: climates.extend(ents))
    assert len(climates) == 1

    # 6. Sensor プラットフォーム
    sensors = []
    await setup_sensors(hass, mock_entry, lambda ents: sensors.extend(ents))
    sensor_types = [type(s).__name__ for s in sensors]

    assert "PanasonicCostReductionSensor" in sensor_types
    assert "PanasonicOperationModeSensor" in sensor_types
    assert "PanasonicCoolovenStateSensor" in sensor_types
    assert "PanasonicDoorOpenSensor" in sensor_types
    # firmwareUpdate が False なので PanasonicFirmwareSensor は追加されない
    assert "PanasonicFirmwareSensor" not in sensor_types


async def test_platforms_filtering_when_cooloven_disabled(hass: HomeAssistant):
    """coolOven が False の機種の場合、クーリングアシスト関連エンティティが一括で除外されることを検証。"""
    functions_dict = {
        "coolOven": False,
        "doorOpenInfo": False,
        "econaviLedOnOff": False,
        "pcroomLightMode": False,
        "freshFrozen": True,
        "partialFreezingRoom": True,
        "firmwareUpdate": True,
    }

    coord = create_mock_coordinator(hass, functions_dict=functions_dict)
    mock_entry = MagicMock()
    mock_entry.runtime_data.coordinators = {coord.appliance_id: coord}

    # Switch
    switches = []
    await setup_switches(hass, mock_entry, lambda ents: switches.extend(ents))
    switch_keys = [s.entity_description.key for s in switches]
    assert "notify_cool_oven" not in switch_keys
    assert "notify_door_open" not in switch_keys
    assert "econavi_lamp" not in switch_keys
    assert "fresh_frozen" in switch_keys

    # Select
    selects = []
    await setup_selects(hass, mock_entry, lambda ents: selects.extend(ents))
    select_keys = [s.entity_description.key for s in selects]
    assert "cooling_assist_mode" not in select_keys
    assert "cooloven_lamp_mode" not in select_keys
    assert "pcroom_light_mode" not in select_keys
    assert "partial_mode" in select_keys

    # Number
    numbers = []
    await setup_numbers(hass, mock_entry, lambda ents: numbers.extend(ents))
    number_keys = [n.entity_description.key for n in numbers]
    assert "cooling_assist_time" not in number_keys
    assert "cooling_assist_second" not in number_keys
    assert "notify_door_open_time" not in number_keys

    # Button
    buttons = []
    await setup_buttons(hass, mock_entry, lambda ents: buttons.extend(ents))
    assert len(buttons) == 0

    # Climate
    climates = []
    await setup_climates(hass, mock_entry, lambda ents: climates.extend(ents))
    assert len(climates) == 0

    # Sensor
    sensors = []
    await setup_sensors(hass, mock_entry, lambda ents: sensors.extend(ents))
    sensor_types = [type(s).__name__ for s in sensors]
    assert "PanasonicCoolovenStateSensor" not in sensor_types
    assert "PanasonicDoorOpenSensor" not in sensor_types
    assert "PanasonicFirmwareSensor" in sensor_types
