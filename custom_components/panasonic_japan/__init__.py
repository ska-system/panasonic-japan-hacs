"""Panasonic Japan integration setup."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PLATFORMS, _PUSH_KEY, EOJ_NAME_MAP
from .coordinator import PanasonicDataUpdateCoordinator
from .api import PanasonicAPI
from .push import PanasonicPushHandler

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic Japan from a config entry."""
    appliances = entry.data.get("appliances", [])
    _LOGGER.info("[DEBUG_LOG] appliances in entry.data: %s", appliances)    

    # 家電がなくてもセットアップを継続する
    if not appliances:
        _LOGGER.warning("No appliances found in config entry, but continuing setup.")

    # 単一の API インスタンスを生成して全体で共有（トークン不整合の防止）
    api = PanasonicAPI(
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get("refresh_token"),
    )
    
    # 修正ポイント: 家電がある場合のみ PushHandler を初期化・起動する
    if appliances:
        push_handler = PanasonicPushHandler(hass, api, entry)
        hass.data.setdefault(_PUSH_KEY, {})[entry.entry_id] = push_handler
        await push_handler.async_start()

    coordinators: dict[str, PanasonicDataUpdateCoordinator] = {}
    device_reg = dr.async_get(hass)

    # アカウント（entry_id）ごとの辞書領域を確実に初期化
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    for appliance_info in appliances:
        # info ディクショナリから必要な値を抽出・補完する
        info_dict = appliance_info.get("info", {})
        appliance_id = info_dict.get("applianceId") or appliance_info.get("appliance_id")
        product_code = info_dict.get("productCode") or appliance_info.get("product_code")

        # コーディネーターが参照しやすいようトップレベルにもキーをセット
        if appliance_id:
            appliance_info["appliance_id"] = appliance_id
        if product_code:
            appliance_info["product_code"] = product_code
            
        _LOGGER.info("[DEBUG_LOG] Processing appliance_id: %s, info: %s", appliance_id, appliance_info)

        if not appliance_id:
            _LOGGER.warning("[DEBUG_LOG] appliance_id is empty, skipping.")
            continue

        coordinator = PanasonicDataUpdateCoordinator(hass, entry, appliance_info, api)
        await coordinator.async_config_entry_first_refresh()
        
        # ループ内で各デバイスを entry_id 配下の辞書に直接登録
        hass.data[DOMAIN][entry.entry_id][appliance_id] = coordinator
        coordinators[appliance_id] = coordinator

        eoj_upper = (coordinator.eoj or appliance_info.get("eoj", "")).upper()
        device_type_name = EOJ_NAME_MAP.get(eoj_upper, "Appliance")
        resolved_product_code = coordinator.product_code or product_code
        device_name = f"Panasonic {device_type_name} ({resolved_product_code})"

        _LOGGER.info("[DEBUG_LOG] Creating device in DeviceRegistry: %s (id: %s)", device_name, appliance_id)
        device_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, appliance_id)},
            manufacturer="Panasonic",
            name=device_name,
            model=resolved_product_code,
        )

    async def handle_set_cooloven(call: ServiceCall):
        """Handle cooloven service call dynamically for target devices."""
        mode = call.data.get("mode")
        time_min = call.data.get("time", 0)
        time_sec = call.data.get("second", 0)

        payload = {"cooloven_mode": mode}
        if mode != "off":
            payload["cooloven_time"] = int(time_min or 0)
            payload["cooloven_second"] = int(time_sec or 0)

        # 全 ConfigEntry の中身と型を詳細に出力して確認
        all_entries = hass.data.get(DOMAIN, {})
        _LOGGER.error("[DEBUG_LOG] all_entries: %s", all_entries)
        for entry_id, entry_coords in all_entries.items():
            _LOGGER.error("[DEBUG_LOG] entry_id=%s, type=%s, value=%s", entry_id, type(entry_coords), entry_coords)
            if isinstance(entry_coords, dict):
                for sub_k, sub_v in entry_coords.items():
                    _LOGGER.error("[DEBUG_LOG]   -> key=%s, type=%s, value=%s", sub_k, type(sub_v), sub_v)

        target_coordinators = [
            coord
            for entry_coords in all_entries.values()
            for coord in entry_coords.values()
            if hasattr(coord, "eoj") and (coord.eoj or "").upper() == "03B7"
        ]

        for target_coord in target_coordinators:
            await hass.async_add_executor_job(
                target_coord.api.control_device,
                target_coord.appliance_id,
                payload,
            )
            await target_coord.async_request_refresh()

    if any((c.eoj or "").upper() == "03B7" for c in coordinators.values()):
        # サービスの二重登録を防ぐガードを追加
        if not hass.services.has_service(DOMAIN, "set_cooloven"):
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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # 該当エントリのデータ削除と、全アカウント削除時のサービス解除処理
        if DOMAIN in hass.data:
            hass.data[DOMAIN].pop(entry.entry_id, None)
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN, None)
                if hass.services.has_service(DOMAIN, "set_cooloven"):
                    hass.services.async_remove(DOMAIN, "set_cooloven")
        
        # PushHandler の停止と削除の整理
        if _PUSH_KEY in hass.data:
            push_handler: PanasonicPushHandler | None = hass.data[_PUSH_KEY].pop(entry.entry_id, None)
            if push_handler:
                await push_handler.async_stop()
            if not hass.data[_PUSH_KEY]:
                hass.data.pop(_PUSH_KEY, None)

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