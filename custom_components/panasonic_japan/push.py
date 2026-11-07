"""FCM push notification handler for Panasonic Japan."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, Callable
import uuid

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    EVENT_COOLOVEN_CANCELED,
    EVENT_COOLOVEN_COMPLETED,
    EVENT_COOLOVEN_CHANGED,
    EVENT_DOOR,
    EVENT_ERROR,
    EVENT_ICE_COMPLETED,
    EVENT_PUSH,
    EVENT_WATER_SHORTAGE,
    FIREBASE_API_KEY,
    FIREBASE_APP_ID,
    FIREBASE_PROJECT_ID,
    FIREBASE_SENDER_ID,
    PUSH_KIND_COOLOVEN_CANCELED,
    PUSH_KIND_COOLOVEN_COMPLETED,
    PUSH_KIND_DOOR,
    PUSH_KIND_ERROR,
    PUSH_KIND_ICE_COMPLETED,
    PUSH_KIND_WATER_SHORTAGE,
    PUSH_KIND_COOLOVEN_CHANGED,
)

_LOGGER = logging.getLogger(__name__)

_KIND_TO_EVENT = {
    PUSH_KIND_DOOR:           EVENT_DOOR,
    PUSH_KIND_WATER_SHORTAGE: EVENT_WATER_SHORTAGE,
    PUSH_KIND_ICE_COMPLETED:  EVENT_ICE_COMPLETED,
    PUSH_KIND_ERROR:          EVENT_ERROR,
    PUSH_KIND_COOLOVEN_COMPLETED: EVENT_COOLOVEN_COMPLETED,
    PUSH_KIND_COOLOVEN_CANCELED:  EVENT_COOLOVEN_CANCELED,
    PUSH_KIND_COOLOVEN_CHANGED:   EVENT_COOLOVEN_CHANGED,
}

_ACTIVE_PUSH_HANDLERS: list[PanasonicPushHandler] = []


def _extract_header_param(header_val: Any, param_name: str) -> str:
    """Extract a specific parameter (e.g. 'dh' or 'salt') from a Web Push header string (RFC 8188 / RFC 8291)."""
    if not isinstance(header_val, str):
        return str(header_val or "")

    parts = [p.strip() for p in header_val.split(";") if p.strip()]
    val = ""
    prefix = f"{param_name.lower()}="

    # 1. Match explicit name=value (case-insensitive)
    for p in parts:
        if "=" in p:
            name, part_val = p.split("=", 1)
            if name.strip().lower() == param_name.lower():
                val = part_val.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                    val = val[1:-1]
                break

    # 2. If fcmpushclient already sliced the prefix (e.g. crypto-key[3:] or encryption[5:]),
    # the first segment without '=' contains the value
    if not val and parts:
        first = parts[0].strip()
        if "=" not in first:
            val = first
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]

    # 3. Ensure valid URL-safe base64 padding
    if val:
        padding = (4 - len(val) % 4) % 4
        if padding:
            val += "=" * padding

    return val


class PanasonicPushHandler:
    """Register with FCM and forward Panasonic push events to HA with self-healing capabilities."""

    def __init__(self, hass: HomeAssistant, api, config_entry) -> None:
        """Initialize."""
        self.hass = hass
        self.api = api
        self.config_entry = config_entry
        self._client = None
        self._decrypt_error_count = 0
        self._recovering = False
        self._lock = asyncio.Lock()
        self._is_stopped = False
        self._unsub_health_check: Callable[[], None] | None = None

    def _record_decrypt_failure(self) -> None:
        """Record a decryption failure and trigger recovery if threshold is reached."""
        self._decrypt_error_count += 1
        _LOGGER.warning(
            "Push decryption error detected (consecutive: %d/3)",
            self._decrypt_error_count,
        )
        if self._decrypt_error_count >= 3:
            _LOGGER.error(
                "Push decryption failed 3 consecutive times; scheduling full push auto-recovery"
            )
            self._decrypt_error_count = 0
            self.hass.async_create_task(self.async_recover(force_reregister=True))

    def _record_decrypt_success(self) -> None:
        """Reset consecutive decryption error count on success."""
        self._decrypt_error_count = 0

    async def async_start(self) -> None:
        """Register with FCM and start listening for push messages."""
        self._is_stopped = False
        if self not in _ACTIVE_PUSH_HANDLERS:
            _ACTIVE_PUSH_HANDLERS.append(self)

        await self._async_start_client()

        # Start periodic health check (every 60 seconds)
        if self._unsub_health_check is None:
            self._unsub_health_check = async_track_time_interval(
                self.hass, self._async_health_check, timedelta(seconds=60)
            )

    async def _async_start_client(self) -> None:
        """Internal helper to initialize FCM client, register push term, and start listening."""
        try:
            import firebase_messaging.fcmpushclient

            # 復号時の引数（Web Push ヘッダー）を正しく抽出・パディング補正するモンキーパッチ
            if not getattr(firebase_messaging.fcmpushclient.FcmPushClient, "_panasonic_patched", False):
                _original_decrypt = firebase_messaging.fcmpushclient.FcmPushClient._decrypt_raw_data

                @staticmethod
                def _patched_decrypt(credentials, crypto_key_str, salt, raw_data):
                    clean_crypto_key = _extract_header_param(crypto_key_str, "dh")
                    clean_salt = _extract_header_param(salt, "salt")
                    _LOGGER.debug(
                        "FCM decrypt debug: raw_key=%s, clean_key=%s, raw_salt=%s, clean_salt=%s, raw_data_len=%s",
                        crypto_key_str,
                        clean_crypto_key,
                        salt,
                        clean_salt,
                        len(raw_data) if raw_data else 0,
                    )
                    try:
                        decrypted = _original_decrypt(credentials, clean_crypto_key, clean_salt, raw_data)
                        for h in list(_ACTIVE_PUSH_HANDLERS):
                            h._record_decrypt_success()
                        return decrypted
                    except Exception as err:
                        _LOGGER.error(
                            "Decryption failed with error: %s (raw_key=%s, clean_key=%s, clean_salt=%s)",
                            err,
                            crypto_key_str,
                            clean_crypto_key,
                            clean_salt,
                            exc_info=True,
                        )
                        for h in list(_ACTIVE_PUSH_HANDLERS):
                            h._record_decrypt_failure()
                        return raw_data

                firebase_messaging.fcmpushclient.FcmPushClient._decrypt_raw_data = _patched_decrypt
                firebase_messaging.fcmpushclient.FcmPushClient._panasonic_patched = True

            from firebase_messaging import FcmPushClient, FcmRegisterConfig
        except ImportError:
            _LOGGER.error(
                "firebase_messaging not installed; push notifications disabled"
            )
            return

        entry_data = dict(self.config_entry.data)
        term_id: str = entry_data.get("push_term_id") or str(uuid.uuid4())
        saved_credentials: dict | None = entry_data.get("fcm_credentials")

        fcm_config = FcmRegisterConfig(
            project_id=FIREBASE_PROJECT_ID,
            app_id=FIREBASE_APP_ID,
            api_key=FIREBASE_API_KEY,
            messaging_sender_id=FIREBASE_SENDER_ID,
            bundle_id="com.panasonic.jp.kitchenpocket",
        )

        def _on_credentials_updated(new_creds: dict) -> None:
            updated = dict(self.config_entry.data)
            updated["fcm_credentials"] = new_creds
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=updated
            )

        self._client = FcmPushClient(
            callback=self._on_message,
            fcm_config=fcm_config,
            credentials=saved_credentials,
            credentials_updated_callback=_on_credentials_updated,
        )

        fcm_token: str = await self._client.checkin_or_register()

        old_token = (saved_credentials or {}).get("fcm", {}).get(
            "registration", {}
        ).get("token")

        if fcm_token != old_token:
            firebase_install_id: str = (
                self._client.credentials.get("fcm", {})
                .get("installation", {})
                .get("fid")
                or str(uuid.uuid4())
            )
            term_data = await self.api.register_push_term(
                term_id,
                fcm_token,
                firebase_install_id,
            )
            if term_data:
                term_id = term_data.get("termId", term_id)

            entry_data["fcm_credentials"] = self._client.credentials
            entry_data["push_term_id"] = term_id
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=entry_data
            )
            _LOGGER.info("Push term registered: %s", term_id)

        # Link the push term to all registered appliances
        appliances: list[dict[str, Any]] = self.config_entry.data.get("appliances", [])
        for appliance in appliances:
            info = appliance.get("info", {})
            appliance_id = info.get("applianceId") or appliance.get("appliance_id")

            if appliance_id:
                try:
                    await self.api.link_push_to_device(appliance_id, term_id)
                    _LOGGER.debug("Push term linked to device %s", appliance_id)
                except Exception as err:
                    _LOGGER.warning("Failed to link push term to device %s: %s", appliance_id, err)

        await self._client.start()
        _LOGGER.info("Push notification listener started (term_id=%s)", term_id)

    async def _async_health_check(self, now: Any = None) -> None:
        """Periodically check the health of the FCM push client and recover if stalled."""
        if self._is_stopped or self._recovering:
            return

        is_healthy = False
        if self._client is not None:
            # Check is_started
            if getattr(self._client, "is_started", None) and self._client.is_started():
                tasks = getattr(self._client, "tasks", [])
                if tasks and all(not t.done() for t in tasks):
                    is_healthy = True

        if not is_healthy:
            _LOGGER.warning(
                "Push client is inactive or disconnected; initiating automatic recovery"
            )
            await self.async_recover(force_reregister=False)

    async def async_recover(self, force_reregister: bool = False) -> None:
        """Auto-recovery mechanism for FCM push client when decryption breaks or connection drops."""
        async with self._lock:
            if self._recovering or self._is_stopped:
                return
            self._recovering = True
            try:
                _LOGGER.warning(
                    "Initiating FCM push notification auto-recovery (force_reregister=%s)...",
                    force_reregister,
                )
                if self._client:
                    try:
                        await self._client.stop()
                    except Exception as err:
                        _LOGGER.debug("Error stopping push client during recovery: %s", err)
                    self._client = None

                if force_reregister:
                    # Clear stored FCM credentials to force new key pair generation and re-registration
                    updated_data = dict(self.config_entry.data)
                    updated_data.pop("fcm_credentials", None)
                    updated_data.pop("push_term_id", None)
                    self.hass.config_entries.async_update_entry(self.config_entry, data=updated_data)

                self._decrypt_error_count = 0
                await self._async_start_client()
                _LOGGER.info("FCM push client auto-recovery completed successfully")
            except Exception as err:
                _LOGGER.error("FCM push auto-recovery failed: %s", err, exc_info=True)
            finally:
                self._recovering = False

    async def async_stop(self) -> None:
        """Stop the push notification listener and health check."""
        self._is_stopped = True
        if self in _ACTIVE_PUSH_HANDLERS:
            _ACTIVE_PUSH_HANDLERS.remove(self)

        if self._unsub_health_check:
            self._unsub_health_check()
            self._unsub_health_check = None

        if self._client:
            await self._client.stop()
            self._client = None

    def _on_message(self, data: dict[str, Any], sender_id: str, context: Any = None) -> None:
        """Handle an incoming FCM push message from Panasonic."""
        if not isinstance(data, dict):
            _LOGGER.warning("Received invalid push message data type: %s", type(data))
            self._record_decrypt_failure()
            return

        # Check if payload failed decryption (e.g. contains raw bytes or lacks structured fields)
        inner_data = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
        kind = data.get("kind", "") or inner_data.get("kind", "") or inner_data.get("service_id", "")
        raw_msg = data.get("message")
        if not kind and isinstance(raw_msg, (bytes, bytearray)):
            _LOGGER.warning("Received push payload containing undecrypted raw data")
            self._record_decrypt_failure()
            return

        # Successfully parsed structured push event
        self._record_decrypt_success()

        appliance_id = data.get("appliance_id", "") or inner_data.get("appliance_id", "")
        title = data.get("title", "") or inner_data.get("title", "")
        body = data.get("body", "") or inner_data.get("message", "") or inner_data.get("body", "")

        _LOGGER.debug("Push received: kind=%s appliance_id=%s", kind, appliance_id)

        event_data = {
            "kind": kind,
            "appliance_id": appliance_id,
            "title": title,
            "body": body,
        }

        event_type = _KIND_TO_EVENT.get(kind, EVENT_PUSH)
        self.hass.bus.fire(event_type, event_data)

        if event_type != EVENT_PUSH:
            _LOGGER.info("Event fired: %s — %s", event_type, data.get("body", ""))
        else:
            _LOGGER.debug("Generic push event fired: kind=%s", kind)
