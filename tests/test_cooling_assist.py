"""Unit tests for Cooling Assist functionality in Panasonic Japan integration."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.panasonic_japan.cooling_assist import (
    clamp_cooling_assist_values,
    get_cooling_assist_bounds,
    get_default_cooling_assist_time,
)
from custom_components.panasonic_japan.coordinator import PanasonicDataUpdateCoordinator
from custom_components.panasonic_japan.button import CoolingAssistButton
from custom_components.panasonic_japan.select import (
    PanasonicSelect,
    PanasonicSelectDescription,
)
from custom_components.panasonic_japan.number import (
    PanasonicNumber,
    PanasonicNumberDescription,
)
from custom_components.panasonic_japan.climate import PanasonicClimate


def test_cooling_assist_bounds_and_defaults():
    """Test bounds and default times for each cooling assist mode."""
    # Quench
    q_bounds = get_cooling_assist_bounds("quench")
    assert q_bounds["min_time"] == 0
    assert q_bounds["max_time"] == 10
    assert q_bounds["min_sec"] == 0
    assert q_bounds["max_sec"] == 50
    assert q_bounds["step_sec"] == 10
    assert get_default_cooling_assist_time("quench") == (5, 0)

    # Cold
    c_bounds = get_cooling_assist_bounds("cold")
    assert c_bounds["min_time"] == 10
    assert c_bounds["max_time"] == 30
    assert c_bounds["max_sec"] == 0
    assert get_default_cooling_assist_time("cold") == (15, 0)

    # Frozen
    f_bounds = get_cooling_assist_bounds("frozen")
    assert f_bounds["min_time"] == 30
    assert f_bounds["max_time"] == 60
    assert f_bounds["max_sec"] == 0
    assert get_default_cooling_assist_time("frozen") == (45, 0)

    # Off
    o_bounds = get_cooling_assist_bounds("off")
    assert o_bounds["min_time"] == 0
    assert o_bounds["max_time"] == 0
    assert o_bounds["max_sec"] == 0
    assert get_default_cooling_assist_time("off") == (0, 0)


def test_clamp_cooling_assist_values():
    """Test clamping and snapping for different modes and edge values."""
    # Quench within range
    assert clamp_cooling_assist_values("quench", 5, 30) == (5, 30)
    # Quench second snapping to 10s
    assert clamp_cooling_assist_values("quench", 3, 27) == (3, 20)
    # Quench out of bounds
    assert clamp_cooling_assist_values("quench", 15, 80) == (10, 50)
    assert clamp_cooling_assist_values("quench", -5, -10) == (0, 0)

    # Cold clamps min=10, max=30, seconds=0
    assert clamp_cooling_assist_values("cold", 5, 20) == (10, 0)
    assert clamp_cooling_assist_values("cold", 20, 20) == (20, 0)
    assert clamp_cooling_assist_values("cold", 40, 0) == (30, 0)

    # Frozen clamps min=30, max=60, seconds=0
    assert clamp_cooling_assist_values("frozen", 10, 0) == (30, 0)
    assert clamp_cooling_assist_values("frozen", 45, 10) == (45, 0)
    assert clamp_cooling_assist_values("frozen", 90, 0) == (60, 0)

    # Off returns 0, 0
    assert clamp_cooling_assist_values("off", 10, 20) == (0, 0)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with basic attributes."""
    hass = MagicMock(spec=HomeAssistant)
    config_entry = MagicMock()
    config_entry.data = {}
    config_entry.entry_id = "test_entry"
    api = MagicMock()
    api.control_device = AsyncMock()

    appliance_info = {
        "appliance_id": "test_fridge_01",
        "product_code": "NR-F607HPX",
        "eoj": "0x0287",
    }

    with patch(
        "custom_components.panasonic_japan.coordinator.APIHandlerFactory.create"
    ):
        coordinator = PanasonicDataUpdateCoordinator(
            hass, config_entry, appliance_info, api
        )
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def test_coordinator_cooling_assist_state_and_listeners(mock_coordinator):
    """Test coordinator state changes, defaults, and observer callbacks."""
    listener_called = []

    def listener():
        listener_called.append(True)

    unsub = mock_coordinator.register_cooling_assist_listener(listener)

    # Initial state
    assert mock_coordinator.cooling_assist_mode == "off"
    assert mock_coordinator.cooling_assist_time == 0
    assert mock_coordinator.cooling_assist_second == 0

    # Setting mode to quench resets to default (5 min, 0 sec) and notifies
    mock_coordinator.set_cooling_assist_mode("quench")
    assert mock_coordinator.cooling_assist_mode == "quench"
    assert mock_coordinator.cooling_assist_time == 5
    assert mock_coordinator.cooling_assist_second == 0
    assert len(listener_called) == 1

    # Setting time within bounds
    mock_coordinator.set_cooling_assist_time(8)
    assert mock_coordinator.cooling_assist_time == 8
    assert len(listener_called) == 2

    # Setting time out of bounds for quench (max 10)
    mock_coordinator.set_cooling_assist_time(15)
    assert mock_coordinator.cooling_assist_time == 10
    assert len(listener_called) == 3

    # Setting seconds (snaps to 10s)
    mock_coordinator.set_cooling_assist_second(36)
    assert mock_coordinator.cooling_assist_second == 40
    assert len(listener_called) == 4

    # Setting mode to cold
    mock_coordinator.set_cooling_assist_mode("cold")
    assert mock_coordinator.cooling_assist_mode == "cold"
    assert mock_coordinator.cooling_assist_time == 15
    assert mock_coordinator.cooling_assist_second == 0
    assert len(listener_called) == 5

    # Unsubscribe listener
    unsub()
    mock_coordinator.set_cooling_assist_mode("off")
    assert len(listener_called) == 5


async def test_coordinator_control_and_execute_cooling_assist(mock_coordinator):
    """Test API dispatching for cooling assist commands."""
    # Control device quench
    await mock_coordinator.async_control_cooling_assist("quench", 5, 20)
    mock_coordinator.api.control_device.assert_called_with(
        "test_fridge_01",
        {"cooloven_mode": "quench", "cooloven_time": 5, "cooloven_second": 20},
    )

    # Control device off
    await mock_coordinator.async_control_cooling_assist("off", 5, 20)
    mock_coordinator.api.control_device.assert_called_with(
        "test_fridge_01",
        {"cooloven_mode": "off"},
    )

    # Execute with valid quench state
    mock_coordinator.cooling_assist_mode = "quench"
    mock_coordinator.cooling_assist_time = 3
    mock_coordinator.cooling_assist_second = 30
    await mock_coordinator.async_execute_cooling_assist()
    mock_coordinator.api.control_device.assert_called_with(
        "test_fridge_01",
        {"cooloven_mode": "quench", "cooloven_time": 3, "cooloven_second": 30},
    )

    # Execute with invalid quench state (0 min, 0 sec) raises error
    mock_coordinator.cooling_assist_time = 0
    mock_coordinator.cooling_assist_second = 0
    with pytest.raises(HomeAssistantError, match="Time and seconds cannot both be 0 in quench mode"):
        await mock_coordinator.async_execute_cooling_assist()


async def test_cooling_assist_button(mock_coordinator):
    """Test CoolingAssistButton delegates execution directly to coordinator."""
    button = CoolingAssistButton(mock_coordinator)
    mock_coordinator.async_execute_cooling_assist = AsyncMock()

    await button.async_press()
    mock_coordinator.async_execute_cooling_assist.assert_awaited_once()


async def test_cooling_assist_select_and_number_entities(mock_coordinator):
    """Test PanasonicSelect and PanasonicNumber dynamic reflection and coordination."""
    select_desc = PanasonicSelectDescription(
        key="cooling_assist_mode",
        translation_key="cooling_assist_mode",
        options=["off", "quench", "cold", "frozen"],
        status_key=None,
    )
    select_entity = PanasonicSelect(mock_coordinator, select_desc)
    select_entity.hass = mock_coordinator.hass
    select_entity.async_write_ha_state = MagicMock()

    time_desc = PanasonicNumberDescription(
        key="cooling_assist_time",
        translation_key="cooling_assist_time",
    )
    time_entity = PanasonicNumber(mock_coordinator, time_desc)
    time_entity.hass = mock_coordinator.hass
    time_entity.async_write_ha_state = MagicMock()

    sec_desc = PanasonicNumberDescription(
        key="cooling_assist_second",
        translation_key="cooling_assist_second",
    )
    sec_entity = PanasonicNumber(mock_coordinator, sec_desc)
    sec_entity.hass = mock_coordinator.hass
    sec_entity.async_write_ha_state = MagicMock()

    # Initial state (off)
    assert select_entity.current_option == "off"
    assert time_entity.native_min_value == 0.0
    assert time_entity.native_max_value == 0.0
    assert time_entity.native_value == 0.0
    assert sec_entity.native_min_value == 0.0
    assert sec_entity.native_max_value == 0.0
    assert sec_entity.native_value == 0.0

    # User changes select to 'quench'
    await select_entity.async_select_option("quench")
    assert mock_coordinator.cooling_assist_mode == "quench"
    assert select_entity.current_option == "quench"
    assert time_entity.native_min_value == 0.0
    assert time_entity.native_max_value == 10.0
    assert time_entity.native_value == 5.0
    assert sec_entity.native_min_value == 0.0
    assert sec_entity.native_max_value == 50.0
    assert sec_entity.native_value == 0.0

    # User changes time to 8
    await time_entity.async_set_native_value(8.0)
    assert mock_coordinator.cooling_assist_time == 8
    assert time_entity.native_value == 8.0

    # User changes second to 30
    await sec_entity.async_set_native_value(30.0)
    assert mock_coordinator.cooling_assist_second == 30
    assert sec_entity.native_value == 30.0

    # User changes mode to 'cold'
    await select_entity.async_select_option("cold")
    assert time_entity.native_min_value == 10.0
    assert time_entity.native_max_value == 30.0
    assert time_entity.native_value == 15.0
    assert sec_entity.native_max_value == 0.0
    assert sec_entity.native_value == 0.0


async def test_climate_cooling_assist(mock_coordinator):
    """Test Climate preset mode and cooling assist service calls."""
    climate = PanasonicClimate(mock_coordinator)
    climate.hass = mock_coordinator.hass
    mock_coordinator.async_control_cooling_assist = AsyncMock()

    # Set preset mode to quench
    await climate.async_set_preset_mode("quench")
    mock_coordinator.async_control_cooling_assist.assert_called_with("quench", 5, 0)

    # Set preset mode to cold
    await climate.async_set_preset_mode("cold")
    mock_coordinator.async_control_cooling_assist.assert_called_with("cold", 15, 0)

    # Set preset mode to off
    await climate.async_set_preset_mode("off")
    mock_coordinator.async_control_cooling_assist.assert_called_with("off", 0, 0)

    # Entity service call async_cooling_assist
    await climate.async_cooling_assist("quench", 7, 20)
    mock_coordinator.async_control_cooling_assist.assert_called_with("quench", 7, 20)
