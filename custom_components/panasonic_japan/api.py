"""API client for Panasonic Japan Kitchen Appliances."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from datetime import datetime
from typing import Any

import aiohttp

from .const import (
    API_KEY,
    AUTH0_CLIENT_ID,
    USER_AGENT,
    YEN_PER_KWH,
)
from .utils import (
    auth0_token_url,
    auth0_userinfo_url,
    device_url,
    product_url,
    push_new_term_url,
    user_info_url,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TOKEN_MARGIN_SECONDS = 300


class PanasonicAPIError(Exception):
    """Base exception for Panasonic API errors."""


class PanasonicAuthError(PanasonicAPIError):
    """Authentication or authorization failure."""


class PanasonicConnectionError(PanasonicAPIError):
    """Network-level failure (timeout, connection refused, etc.)."""


class PanasonicRequestError(PanasonicAPIError):
    """HTTP request failed with a non-auth error status."""


class PanasonicAPI:
    """API client for Panasonic Japan Kitchen Appliances."""

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._internal_session: aiohttp.ClientSession | None = None
        self._access_token = access_token
        self._refresh_token = refresh_token

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession."""
        if self._session and not self._session.closed:
            return self._session
        if self._internal_session is None or self._internal_session.closed:
            self._internal_session = aiohttp.ClientSession()
        return self._internal_session

    async def close(self) -> None:
        """Close the internal session if created."""
        if self._internal_session and not self._internal_session.closed:
            await self._internal_session.close()

    def reset_session(self) -> None:
        """No-op for aiohttp shared session compatibility."""
        pass

    def prepare_request_cycle(self) -> None:
        """No-op for aiohttp shared session compatibility."""
        pass

    async def ensure_token_valid(self, margin_seconds: int = DEFAULT_TOKEN_MARGIN_SECONDS) -> None:
        """Proactively refresh the access token if it is expiring soon."""
        if self.is_token_expiring(margin_seconds=margin_seconds):
            _LOGGER.debug("Access token is expiring soon — refreshing proactively")
            await self.refresh_access_token()

    async def retry_after_auth_failure(self) -> bool:
        """Attempt token refresh after an auth failure."""
        try:
            await self.refresh_access_token()
            return True
        except PanasonicAuthError as err:
            _LOGGER.error("Token refresh after auth failure failed: %s", err)
            return False

    def handle_connection_error(self) -> None:
        """Log connection error (aiohttp manages reconnection automatically)."""
        _LOGGER.warning("Network error encountered — aiohttp will handle reconnection on next request")

    def _get_reizo_date(self) -> str:
        """Get current date in Japan timezone for X-Reizo-Date header."""
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo("Asia/Tokyo")
        except ImportError:
            import pytz

            tz = pytz.timezone("Asia/Tokyo")

        return datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S")

    def _get_headers(self, include_reizo_date: bool = True) -> dict[str, str]:
        """Get default headers for API requests."""
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json",
            "X-API-Key": API_KEY,
            "User-Agent": USER_AGENT,
        }

        if include_reizo_date:
            headers["X-Reizo-Date"] = self._get_reizo_date()

        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        return headers

    async def _make_request(
        self, method: str, url: str, **kwargs: Any
    ) -> Any:
        """Make an API request with standardized error handling."""
        session = await self._get_session()
        timeout_sec = kwargs.pop("timeout", 30)
        timeout = aiohttp.ClientTimeout(total=timeout_sec)

        try:
            async with session.request(method, url, timeout=timeout, **kwargs) as response:
                if response.status in (401, 403):
                    raise PanasonicAuthError(
                        f"Authentication failed: {response.status}"
                    )

                if response.status >= 400:
                    raise PanasonicRequestError(
                        f"HTTP {response.status} for {method} {url}"
                    )

                if response.status == 204:
                    return None

                text = await response.text()
                if not text:
                    return None

                try:
                    return json.loads(text)
                except Exception:
                    return text

        except (asyncio.TimeoutError, aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError) as err:
            raise PanasonicConnectionError(f"Request timed out / connection error: {err}") from err
        except aiohttp.ClientError as err:
            raise PanasonicConnectionError(f"Network error: {err}") from err

    async def get_auth0_user_info(self) -> dict[str, Any]:
        """Get Auth0 user info including app_metadata and member_user_id."""
        url = auth0_userinfo_url()
        return await self._make_request("GET", url, headers=self._get_headers(), timeout=30)

    async def get_user_info(self) -> dict[str, Any]:
        """Get user information and list of appliances."""
        url = user_info_url()
        headers = self._get_headers(include_reizo_date=False)
        headers["X-API-Key"] = API_KEY
        headers["User-Agent"] = USER_AGENT

        return await self._make_request("GET", url, headers=headers, timeout=30)

    async def get_device_status(self, appliance_id: str) -> dict[str, Any]:
        """Get device status."""
        url = device_url(appliance_id, "status")
        return await self._make_request(
            "GET", url, headers=self._get_headers(), params={"usages": "1"}, timeout=30
        )

    async def get_device_settings(self, appliance_id: str) -> dict[str, Any]:
        """Get device control settings (usages=2 = VIEWED_SETTING_SCREEN)."""
        url = device_url(appliance_id, "status")
        return await self._make_request(
            "GET", url, headers=self._get_headers(), params={"usages": "2"}, timeout=30
        )

    async def control_device(self, appliance_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """PUT /devices/{id}/status — send a control command to the fridge."""
        url = device_url(appliance_id, "status")
        return await self._make_request(
            "PUT", url, headers=self._get_headers(), json=payload, timeout=30
        )

    async def get_electricity_reduction(self, appliance_id: str) -> dict[str, Any]:
        """Get electricity cost reduction data."""
        url = device_url(appliance_id, "reduction")
        return await self._make_request(
            "GET", url, headers=self._get_headers(), timeout=30
        )

    def calculate_electricity_usage(self, cost_reduction: int) -> float:
        """Calculate electricity usage in kWh/month."""
        return (750 - cost_reduction) / YEN_PER_KWH

    async def get_device_functions(self, appliance_id: str) -> dict[str, Any]:
        """Get device functions list."""
        url = product_url(appliance_id, "functions")
        return await self._make_request(
            "GET", url, headers=self._get_headers(), timeout=30
        )

    async def get_door_open_info(self, appliance_id: str) -> dict[str, Any]:
        """Get door open count and monitoring information."""
        url = device_url(appliance_id, "dooropeninfo")
        return await self._make_request(
            "GET", url, headers=self._get_headers(), timeout=30
        )

    async def get_notification_settings(self, appliance_id: str, term_id: str) -> dict[str, Any]:
        """GET /devices/{id}/settings — get current notification settings."""
        if not term_id:
            return {}

        url = device_url(appliance_id, "settings")
        res = await self._make_request(
            "GET", url, headers=self._get_headers(), params={"term_id": term_id}, timeout=30
        )
        return res if isinstance(res, dict) else {}

    async def update_notification_settings(self, appliance_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """PUT /devices/{id}/settings — update notification settings."""
        url = device_url(appliance_id, "settings")
        res = await self._make_request(
            "PUT", url, headers=self._get_headers(), json=payload, timeout=30
        )
        return res if isinstance(res, dict) else None

    async def register_push_term(
        self, term_id: str, fcm_token: str, firebase_install_id: str
    ) -> dict[str, Any] | None:
        """Register FCM push token with Panasonic API."""
        from .const import PUSH_TYPE

        url = push_new_term_url()
        headers = self._get_headers(include_reizo_date=False)
        headers["X-API-Key"] = API_KEY
        headers["User-Agent"] = USER_AGENT

        data = {
            "smpLocale": "ja",
            "termId": term_id,
            "token": fcm_token,
            "type": PUSH_TYPE,
            "firebaseInstallId": firebase_install_id,
        }

        try:
            return await self._make_request(
                "POST", url, json=data, headers=headers, timeout=30
            )
        except PanasonicAPIError as err:
            _LOGGER.exception("Error registering push term: %s", err)
            return None

    async def link_push_to_device(self, appliance_id: str, term_id: str) -> dict[str, Any] | None:
        """GET /devices/{id}/settings?term_id=... — links the push term to the fridge."""
        url = device_url(appliance_id, "settings")
        try:
            return await self._make_request(
                "GET",
                url,
                headers=self._get_headers(),
                params={"term_id": term_id},
                timeout=30,
            )
        except PanasonicAPIError as err:
            _LOGGER.exception("Error linking push term to device: %s", err)
            return None

    async def refresh_access_token(self) -> dict[str, Any]:
        """Refresh the access token using refresh token with robust error handling."""
        if not self._refresh_token:
            raise PanasonicAuthError("No refresh token available")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        }

        data = {
            "grant_type": "refresh_token",
            "client_id": AUTH0_CLIENT_ID,
            "refresh_token": self._refresh_token,
        }

        try:
            token_data = await self._make_request(
                "POST", auth0_token_url(), data=data, headers=headers, timeout=30
            )
        except PanasonicConnectionError as err:
            raise PanasonicConnectionError(f"Network error during token refresh: {err}") from err
        except PanasonicRequestError as err:
            raise PanasonicAuthError(f"Token refresh rejected by Auth0: {err}") from err

        if not isinstance(token_data, dict):
            raise PanasonicAuthError("Token refresh returned invalid response format")

        self._access_token = token_data.get("access_token")
        if "refresh_token" in token_data:
            self._refresh_token = token_data.get("refresh_token")

        if not self._access_token:
            raise PanasonicAuthError("Token refresh returned empty access token")

        return token_data

    def is_token_expiring(self, margin_seconds: int = DEFAULT_TOKEN_MARGIN_SECONDS) -> bool:
        """Return True if the access token expires within margin_seconds."""
        if not self._access_token:
            return True
        try:
            payload_b64 = self._access_token.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            exp = payload.get("exp", 0)
            return time.time() + margin_seconds >= exp
        except Exception:
            return True

    @property
    def access_token(self) -> str | None:
        """Get current access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        """Get current refresh token."""
        return self._refresh_token