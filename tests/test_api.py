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
    """401エラー（リフレッシュトークンなし）時に PanasonicAuthError が送出されることを検証する。"""
    mock_resp = MockClientResponse(status=401)
    session = create_mock_session(mock_resp)

    api = PanasonicAPI(session=session, access_token="expired_token", refresh_token=None)

    with pytest.raises(PanasonicAuthError) as excinfo:
        await api.get_user_info()
    assert "Authentication failed: 401" in str(excinfo.value)


async def test_make_request_auto_refresh_on_401():
    """401エラー発生時にリフレッシュトークンがあれば自動更新してリトライ成功することを検証する。"""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.closed = False

    # 1回目: 401 Unauthorized
    # 2回目: Auth0 トークン更新 (200)
    # 3回目: 再リクエスト成功 (200)
    resp_401 = MockClientResponse(status=401)
    resp_token = MockClientResponse(
        status=200, json_data={"access_token": "refreshed_token", "refresh_token": "next_refresh"}
    )
    resp_success = MockClientResponse(status=200, json_data={"result": "ok"})

    session.request = MagicMock(side_effect=[resp_401, resp_token, resp_success])

    api = PanasonicAPI(session=session, access_token="old_access", refresh_token="valid_refresh")
    result = await api.get_user_info()

    assert result == {"result": "ok"}
    assert api.access_token == "refreshed_token"
    assert session.request.call_count == 3


async def test_concurrent_requests_token_refresh():
    """複数APIが同時に401になっても、トークン更新は1回のみ実行され全リクエストが成功することを検証する。"""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.closed = False

    # 2つの並列リクエストが走る想定
    # req1: 401
    # req2: 401
    # auth0: 200 (トークン更新)
    # req1 retry: 200
    # req2 retry: 200
    call_count = 0

    def mock_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        if "oauth/token" in url or "token" in url:
            return MockClientResponse(
                status=200,
                json_data={"access_token": "new_token_123", "refresh_token": "new_refresh_123"},
            )
        auth_hdr = kwargs.get("headers", {}).get("Authorization", "")
        if auth_hdr == "Bearer new_token_123":
            return MockClientResponse(status=200, json_data={"status": "success", "call": call_count})
        return MockClientResponse(status=401)

    session.request = MagicMock(side_effect=mock_request)

    api = PanasonicAPI(session=session, access_token="old_token", refresh_token="valid_refresh")

    import asyncio
    results = await asyncio.gather(
        api.get_device_status("appliance_1"),
        api.get_device_settings("appliance_1"),
        api.get_electricity_reduction("appliance_1"),
    )

    for res in results:
        assert res["status"] == "success"
    assert api.access_token == "new_token_123"


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
    token_data = await api.refresh_access_token(force=True)

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