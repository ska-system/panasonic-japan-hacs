from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import logging
from typing import Any

from .api import PanasonicAPI
from .const import EOJ_FRIDGE

_LOGGER = logging.getLogger(__name__)


class BaseApplianceHandler(ABC):
    """家電種別ごとの処理を定義する抽象ハンドラークラス"""

    def __init__(self, api_client: PanasonicAPI) -> None:
        self.api = api_client

    @abstractmethod
    async def fetch_all_data(self, appliance_id: str, push_term_id: str = "") -> dict[str, Any]:
        """該当家電に必要な全データを一括取得する抽象メソッド"""
        pass


class RefrigeratorHandler(BaseApplianceHandler):
    """冷蔵庫（EOJ: 03B7）専用のAPIハンドラー"""

    async def fetch_all_data(self, appliance_id: str, push_term_id: str = "") -> dict[str, Any]:
        # 同一の requests.Session に対するスレッド競合を防ぐため順次実行
        device_status = await asyncio.to_thread(self.api.get_device_status, appliance_id)
        device_settings = await asyncio.to_thread(self.api.get_device_settings, appliance_id)
        electricity_data = await asyncio.to_thread(self.api.get_electricity_reduction, appliance_id)
        notification_settings = await asyncio.to_thread(
            self.api.get_notification_settings, appliance_id, push_term_id
        )
        door_open_info = await asyncio.to_thread(self.api.get_door_open_info, appliance_id)

        device_status.update(device_settings)
        return {
            "device_status": device_status,
            "notification_settings": notification_settings,
            "electricity": electricity_data,
            "door_open_info": door_open_info,
        }

class DefaultApplianceHandler(BaseApplianceHandler):
    """未対応の eoj 向けフォールバックハンドラー"""

    async def fetch_all_data(self, appliance_id: str, push_term_id: str = "") -> dict[str, Any]:
        _LOGGER.warning("Unsupported EOJ code: returning empty status")
        return {
            "device_status": {},
            "notification_settings": {},
            "electricity": {},
        }


class APIHandlerFactory:
    """eoj に基づいて適切なハンドラーを生成するファクトリ"""

    _HANDLERS: dict[str, type[BaseApplianceHandler]] = {
        EOJ_FRIDGE: RefrigeratorHandler,
    }

    @classmethod
    def create(cls, eoj: str | None, api_client: PanasonicAPI) -> BaseApplianceHandler:
        """指定された eoj に対応するハンドラーを生成"""
        if not eoj:
            return DefaultApplianceHandler(api_client)

        normalized_eoj = eoj.upper()
        handler_cls = cls._HANDLERS.get(normalized_eoj, DefaultApplianceHandler)
        return handler_cls(api_client)