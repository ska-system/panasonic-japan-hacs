import json
from unittest.mock import AsyncMock, MagicMock
import pytest
import aiohttp
from custom_components.panasonic_japan.api import (
    PanasonicAPI,
    PanasonicAuthError,
    PanasonicConnectionError,
    PanasonicRequestError,
)


class MockClientResponse:
    """aiohttp ClientResponse の非同期コンテキストマネージャモック"""

    def __init__(self, status: int = 200, json_data: dict | None = None, text_data: str = "") -> None:
        self.status = status
        self._json_data = json_data
        self._text_data = text_data if text_data else (json.dumps(json_data) if json_data is not None else "")
        self.ok = status < 400

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def create_mock_session(response: MockClientResponse) -> MagicMock:
    """モックレスポンスを返す aiohttp.ClientSession モックを作成"""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.closed = False
    session.request = MagicMock(return_value=response)
    return session


def test_calculate_electricity_usage():
    """電力使用量の計算ロジックが正常に動作することを検証する。"""
    api = PanasonicAPI()
    # (750 - 440) / 31 = 10.0 (YEN_PER_KWH が 31 と仮定)
    usage = api.calculate_electricity_usage(440)
    assert usage == pytest.approx(10.0)


async def test_get_device_status_success():
    """デバイスステータス取得の正常系テスト。"""
    mock_resp = MockClientResponse(status=200, json_data={"power": "on", "temperature": 20})
    session = create_mock_session(mock_resp)

    api = PanasonicAPI(session=session, access_token="dummy_token")
    result = await api.get_device_status("test_appliance_id")

    assert result == {"power": "on", "temperature": 20}
    session.request.assert_called_once()


async def test_control_device_success():
    """デバイス制御（PUT）の正常系テスト。"""
    mock_resp = MockClientResponse(status=200, json_data={"result": "ok"})
    session = create_mock_session(mock_resp)

    api = PanasonicAPI(session=session, access_token="dummy_token")
    result = await api.control_device("test_appliance_id", {"eco_nav": True})

    assert result == {"result": "ok"}


async def test_make_request_unauthorized():
    """401エラー時に PanasonicAuthError が送出されることを検証する。"""
    mock_resp = MockClientResponse(status=401)
    session = create_mock_session(mock_resp)

    api = PanasonicAPI(session=session, access_token="expired_token")

    with pytest.raises(PanasonicAuthError) as excinfo:
        await api.get_user_info()
    assert "Authentication failed: 401" in str(excinfo.value)


async def test_make_request_server_error():
    """500エラー時に PanasonicRequestError が送出されることを検証する。"""
    mock_resp = MockClientResponse(status=500, text_data="Internal Server Error")
    session = create_mock_session(mock_resp)

    api = PanasonicAPI(session=session, access_token="dummy_token")

    with pytest.raises(PanasonicRequestError) as excinfo:
        await api.get_user_info()
    assert "HTTP 500" in str(excinfo.value)


async def test_make_request_connection_error():
    """ネットワーク切断時に PanasonicConnectionError が送出されることを検証する。"""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.closed = False
    session.request.side_effect = aiohttp.ClientConnectorError(
        connection_key=MagicMock(), os_error=OSError("Connection failed")
    )

    api = PanasonicAPI(session=session, access_token="dummy_token")

    with pytest.raises(PanasonicConnectionError):
        await api.get_device_status("test_appliance_id")


async def test_refresh_access_token_success():
    """リフレッシュトークンによるトークン更新成功を検証する。"""
    mock_resp = MockClientResponse(
        status=200,
        json_data={"access_token": "new_access_token", "refresh_token": "new_refresh_token"},
    )
    session = create_mock_session(mock_resp)

    api = PanasonicAPI(session=session, access_token="old_access", refresh_token="old_refresh")
    token_data = await api.refresh_access_token()

    assert token_data["access_token"] == "new_access_token"
    assert api.access_token == "new_access_token"
    assert api.refresh_token == "new_refresh_token"


async def test_refresh_access_token_no_token():
    """リフレッシュトークンが存在しない場合にエラーを送出することを検証する。"""
    api = PanasonicAPI(access_token="dummy_access", refresh_token=None)

    with pytest.raises(PanasonicAuthError) as excinfo:
        await api.refresh_access_token()
    assert "No refresh token available" in str(excinfo.value)


def test_is_token_expiring_with_invalid_token():
    """不正な形式のアクセストークンが渡された場合に True を返すことを検証する。"""
    api = PanasonicAPI(access_token="invalid_token_format")
    assert api.is_token_expiring() is True