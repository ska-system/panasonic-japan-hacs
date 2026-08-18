"""Tests for Panasonic Japan appliance handlers."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from custom_components.panasonic_japan.api import PanasonicAPI
from custom_components.panasonic_japan.handlers import (
    APIHandlerFactory,
    DefaultApplianceHandler,
    RefrigeratorHandler,
)


@pytest.fixture
def mock_api():
    """Mock PanasonicAPI instance with async methods."""
    api = MagicMock(spec=PanasonicAPI)
    api.get_device_status = AsyncMock(return_value={"power": "on", "door": "closed"})
    api.get_device_settings = AsyncMock(return_value={"ice_making_mode": "quick", "eco_nav": True})
    api.get_electricity_reduction = AsyncMock(return_value={"cost_reduction": 150})
    api.get_notification_settings = AsyncMock(return_value={"door_alert": True})
    api.get_door_open_info = AsyncMock(return_value={"open_count": 5})
    return api


async def test_refrigerator_handler_fetch_all_data_parallel(mock_api):
    """RefrigeratorHandler が 5 つの API を呼び出しデータを正しくマージすることを検証する。"""
    handler = RefrigeratorHandler(mock_api)
    result = await handler.fetch_all_data("test_appliance_123", push_term_id="term_abc")

    # 全てのAPIが呼び出されたことを検証
    mock_api.get_device_status.assert_awaited_once_with("test_appliance_123")
    mock_api.get_device_settings.assert_awaited_once_with("test_appliance_123")
    mock_api.get_electricity_reduction.assert_awaited_once_with("test_appliance_123")
    mock_api.get_notification_settings.assert_awaited_once_with("test_appliance_123", "term_abc")
    mock_api.get_door_open_info.assert_awaited_once_with("test_appliance_123")

    # device_status と device_settings がマージされていること
    assert result["device_status"] == {
        "power": "on",
        "door": "closed",
        "ice_making_mode": "quick",
        "eco_nav": True,
    }
    assert result["notification_settings"] == {"door_alert": True}
    assert result["electricity"] == {"cost_reduction": 150}
    assert result["door_open_info"] == {"open_count": 5}


async def test_refrigerator_handler_with_empty_responses(mock_api):
    """APIが空の辞書や None を返した場合でも安全にハンドリングできることを検証する。"""
    mock_api.get_device_status = AsyncMock(return_value={})
    mock_api.get_device_settings = AsyncMock(return_value=None)
    mock_api.get_electricity_reduction = AsyncMock(return_value={})
    mock_api.get_notification_settings = AsyncMock(return_value={})
    mock_api.get_door_open_info = AsyncMock(return_value={})

    handler = RefrigeratorHandler(mock_api)
    result = await handler.fetch_all_data("test_appliance_123")

    assert result["device_status"] == {}
    assert result["notification_settings"] == {}
    assert result["electricity"] == {}
    assert result["door_open_info"] == {}


async def test_default_handler(mock_api):
    """DefaultApplianceHandler がフォールバック構造を返すことを検証する。"""
    handler = DefaultApplianceHandler(mock_api)
    result = await handler.fetch_all_data("unknown_appliance")

    assert result == {
        "device_status": {},
        "notification_settings": {},
        "electricity": {},
    }


def test_handler_factory(mock_api):
    """APIHandlerFactory が EOJ コードに応じて適切なハンドラーを生成することを検証する。"""
    fridge_handler = APIHandlerFactory.create("03B7", mock_api)
    assert isinstance(fridge_handler, RefrigeratorHandler)

    lower_fridge_handler = APIHandlerFactory.create("03b7", mock_api)
    assert isinstance(lower_fridge_handler, RefrigeratorHandler)

    unknown_handler = APIHandlerFactory.create("9999", mock_api)
    assert isinstance(unknown_handler, DefaultApplianceHandler)

    none_handler = APIHandlerFactory.create(None, mock_api)
    assert isinstance(none_handler, DefaultApplianceHandler)
