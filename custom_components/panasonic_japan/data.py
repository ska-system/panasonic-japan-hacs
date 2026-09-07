"""Runtime data models for the Panasonic Japan integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .api import PanasonicAPI
    from .coordinator import PanasonicDataUpdateCoordinator
    from .push import PanasonicPushHandler


@dataclass
class EntryCustomData:
    """Per-config-entry custom entity state shared across platforms."""

    cooling_assist_mode: str = "off"
    number_entities: dict = field(default_factory=dict)


@dataclass
class PanasonicData:
    """Runtime data stored in config_entry.runtime_data."""

    api: PanasonicAPI
    coordinators: dict[str, PanasonicDataUpdateCoordinator] = field(default_factory=dict)
    push_handler: PanasonicPushHandler | None = None
    custom: EntryCustomData = field(default_factory=EntryCustomData)


type PanasonicConfigEntry = ConfigEntry[PanasonicData]
