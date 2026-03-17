"""FCM push notification handler for Panasonic Japan."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    EVENT_DOOR,
    EVENT_PUSH,
    FIREBASE_API_KEY,
    FIREBASE_APP_ID,
    FIREBASE_PROJECT_ID,
    FIREBASE_SENDER_ID,
    PUSH_KIND_DOOR,
)

_LOGGER = logging.getLogger(__name__)


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
                "firebase_messaging package not installed; push notifications disabled. "
                "Add 'firebase-messaging' to your requirements."
            )
            return

        entry_data = dict(self.config_entry.data)
        term_id: str = entry_data.get("push_term_id") or str(uuid.uuid4())
        stored_credentials = entry_data.get("fcm_credentials")

        config = FcmRegisterConfig(
            sender_id=FIREBASE_SENDER_ID,
            app_id=FIREBASE_APP_ID,
            api_key=FIREBASE_API_KEY,
            project_id=FIREBASE_PROJECT_ID,
        )

        self._client = FcmPushClient(
            credentials=stored_credentials,
            config=config,
            callback=self._on_message,
        )

        new_credentials = await self._client.checkin_or_register()

        # Re-register with Panasonic whenever our FCM credentials change
        if new_credentials != stored_credentials:
            fcm_token: str = new_credentials.get("token", "")
            firebase_install_id: str = new_credentials.get(
                "firebase_installation_id", str(uuid.uuid4())
            )

            _LOGGER.debug(
                "New FCM token acquired, registering push term with Panasonic"
            )
            term_data = await self.hass.async_add_executor_job(
                self.api.register_push_term,
                term_id,
                fcm_token,
                firebase_install_id,
            )
            if term_data:
                term_id = term_data.get("termId", term_id)

            entry_data["fcm_credentials"] = new_credentials
            entry_data["push_term_id"] = term_id
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=entry_data
            )
            _LOGGER.debug("Push term registered: %s", term_id)

        await self._client.start()
        _LOGGER.info("Panasonic push notification listener started (term_id=%s)", term_id)

    async def async_stop(self) -> None:
        """Stop the push notification listener."""
        if self._client:
            await self._client.stop()
            self._client = None
            _LOGGER.debug("Push notification listener stopped")

    def _on_message(self, sender_id: str, data: dict[str, Any]) -> None:
        """Handle an incoming FCM push message from Panasonic."""
        kind: str = data.get("kind", "")
        appliance_id: str = data.get("appliance_id", "")

        _LOGGER.debug("Push received: kind=%s appliance_id=%s", kind, appliance_id)

        event_data = {
            "kind": kind,
            "appliance_id": appliance_id,
            "title": data.get("title", ""),
            "body": data.get("body", ""),
        }

        if kind == PUSH_KIND_DOOR:
            self.hass.bus.fire(EVENT_DOOR, event_data)
            _LOGGER.info(
                "Door event fired for appliance %s: %s",
                appliance_id,
                data.get("body", ""),
            )
        else:
            # Fire a generic event for other notification types (errors, firmware, etc.)
            self.hass.bus.fire(EVENT_PUSH, event_data)
