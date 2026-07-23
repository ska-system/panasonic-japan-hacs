"""FCM push notification handler for Panasonic Japan."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from homeassistant.core import HomeAssistant

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


class PanasonicPushHandler:
    """Register with FCM and forward Panasonic push events to HA."""

    def __init__(self, hass: HomeAssistant, api, config_entry) -> None:
        """Initialize."""
        self.hass = hass
        self.api = api
        self.config_entry = config_entry
        self._client = None

    async def async_start(self) -> None:
        """Register with FCM and start listening for push messages."""
        try:
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
            term_data = await self.hass.async_add_executor_job(
                self.api.register_push_term,
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

        # Link the push term to the specific fridge device
        appliance_id: str = self.config_entry.data.get("appliance_id", "")
        if appliance_id:
            await self.hass.async_add_executor_job(
                self.api.link_push_to_device, appliance_id, term_id
            )
            _LOGGER.debug("Push term linked to device %s", appliance_id)

        await self._client.start()
        _LOGGER.info("Push notification listener started (term_id=%s)", term_id)

    async def async_stop(self) -> None:
        """Stop the push notification listener."""
        if self._client:
            await self._client.stop()
            self._client = None

    def _on_message(self, data: dict[str, Any], sender_id: str, context: Any = None) -> None:
        """Handle an incoming FCM push message from Panasonic."""
        inner_data = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
        
        kind = data.get("kind", "") or inner_data.get("kind", "") or inner_data.get("service_id", "")
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
