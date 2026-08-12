"""The Panasonic Japan Kitchen Appliances integration."""
from __future__ import annotations

import logging

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import PanasonicDataUpdateCoordinator
from .push import PanasonicPushHandler

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR, 
    Platform.SWITCH, 
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]

_PUSH_KEY = f"{DOMAIN}_push"

# EOJごとの種別名称マッピング
EOJ_NAME_MAP = {
    "03B7": "Fridge",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic Japan from a config entry."""
    coordinator = PanasonicDataUpdateCoordinator(hass, entry)

    # Start push notification listener (non-blocking; failure is logged, not fatal)
    push_handler = PanasonicPushHandler(hass, coordinator.api, entry)
    hass.data.setdefault(_PUSH_KEY, {})[entry.entry_id] = push_handler
    await push_handler.async_start()

    # term_id が確保された状態でコーディネータの初回リフレッシュを実行する
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # デバイスレジストリへデバイスとして登録する
    device_registry = dr.async_get(hass)
    if coordinator.appliance_id:
        eoj_upper = (coordinator.eoj or "").upper()
        device_type_name = EOJ_NAME_MAP.get(eoj_upper, "Appliance")
        device_name = f"Panasonic {device_type_name} ({coordinator.product_code})"

        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, coordinator.appliance_id)},
            manufacturer="Panasonic",
            name=device_name,
            model=coordinator.product_code,
        )

    # 冷蔵庫（EOJ: 03B7）固有のサービス登録
    if (coordinator.eoj or "").upper() == "03B7":
        async def handle_set_cooloven(call: ServiceCall):
            mode = call.data.get("mode")
            time_min = call.data.get("time", 0)
            time_sec = call.data.get("second", 0)

            payload = {
                "cooloven_mode": mode,
            }
            if mode != "off":
                payload["cooloven_time"] = int(time_min)
                payload["cooloven_second"] = int(time_sec)

            await hass.async_add_executor_job(
                coordinator.api.control_device, 
                coordinator.appliance_id, 
                payload
            )
            await coordinator.async_request_refresh()

        hass.services.async_register(DOMAIN, "set_cooloven", handle_set_cooloven)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await hass.http.async_register_static_paths([
        StaticPathConfig(
            "/panasonic_japan_assets/panasonic-cooloven-card.js",
            hass.config.path("custom_components/panasonic_japan/frontend/panasonic-cooloven-card.js"),
            cache_headers=False,
        ),
        StaticPathConfig(
            "/panasonic_japan_assets/translations",
            hass.config.path("custom_components/panasonic_japan/translations"),
            cache_headers=False,
        ),
    ])

    await _async_register_lovelace_resource(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        push_handler: PanasonicPushHandler = hass.data.get(_PUSH_KEY, {}).pop(
            entry.entry_id, None
        )
        if push_handler:
            await push_handler.async_stop()

    return unload_ok


async def _async_register_lovelace_resource(hass):
    url = "/panasonic_japan_assets/panasonic-cooloven-card.js"
    if "lovelace" in hass.data:
        resources = hass.data["lovelace"].resources
        if not resources.loaded:
            await resources.async_load()
        exists = any(item.get("url") == url for item in resources.async_items())
        if not exists:
            await resources.async_create_item({"res_type": "module", "url": url})