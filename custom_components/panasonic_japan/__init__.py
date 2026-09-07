"""Panasonic Japan integration setup."""
from __future__ import annotations

import logging

from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PanasonicAPI
from .const import DOMAIN, EOJ_NAME_MAP, PLATFORMS
from .coordinator import PanasonicDataUpdateCoordinator
from .data import PanasonicConfigEntry, PanasonicData
from .push import PanasonicPushHandler
from .services import async_register_services, async_unregister_services
from .utils import normalize_eoj

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: PanasonicConfigEntry) -> bool:
    """Set up Panasonic Japan from a config entry."""
    appliances = entry.data.get("appliances", [])
    _LOGGER.debug("Appliances in entry data: %s", appliances)

    if not appliances:
        _LOGGER.warning("No appliances found in config entry, but continuing setup.")

    session = async_get_clientsession(hass)
    api = PanasonicAPI(
        session=session,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get("refresh_token"),
    )

    push_handler: PanasonicPushHandler | None = None
    if appliances:
        push_handler = PanasonicPushHandler(hass, api, entry)
        await push_handler.async_start()

    coordinators: dict[str, PanasonicDataUpdateCoordinator] = {}
    device_reg = dr.async_get(hass)

    for appliance_info in appliances:
        info_dict = appliance_info.get("info", {})
        appliance_id = info_dict.get("applianceId") or appliance_info.get("appliance_id")
        product_code = info_dict.get("productCode") or appliance_info.get("product_code")

        if appliance_id:
            appliance_info["appliance_id"] = appliance_id
        if product_code:
            appliance_info["product_code"] = product_code

        _LOGGER.debug("Processing appliance_id: %s, info: %s", appliance_id, appliance_info)

        if not appliance_id:
            _LOGGER.warning("Appliance ID is empty, skipping.")
            continue

        coordinator = PanasonicDataUpdateCoordinator(hass, entry, appliance_info, api)
        await coordinator.async_config_entry_first_refresh()

        coordinators[appliance_id] = coordinator

        eoj_upper = normalize_eoj(coordinator.eoj or appliance_info.get("eoj"))
        device_type_name = EOJ_NAME_MAP.get(eoj_upper, "Appliance")
        resolved_product_code = coordinator.product_code or product_code
        device_name = f"Panasonic {device_type_name} ({resolved_product_code})"

        _LOGGER.debug("Creating device in DeviceRegistry: %s (id: %s)", device_name, appliance_id)
        device_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, appliance_id)},
            manufacturer="Panasonic",
            name=device_name,
            model=resolved_product_code,
        )

    entry.runtime_data = PanasonicData(
        api=api,
        coordinators=coordinators,
        push_handler=push_handler,
    )

    async_register_services(hass)

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


async def async_unload_entry(hass: HomeAssistant, entry: PanasonicConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        if entry.runtime_data.push_handler:
            await entry.runtime_data.push_handler.async_stop()
        if not hass.config_entries.async_loaded_entries(DOMAIN):
            async_unregister_services(hass)

    return unload_ok
