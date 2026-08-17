"""Typed wrapper for hass.data storage."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

from homeassistant.core import HomeAssistant

from .const import DOMAIN, _PUSH_KEY
from .utils import is_fridge_eoj

if TYPE_CHECKING:
    from .coordinator import PanasonicDataUpdateCoordinator
    from .push import PanasonicPushHandler


@dataclass
class EntryCustomData:
    """Per-config-entry custom entity state shared across platforms."""

    cooling_assist_mode: str = "off"
    number_entities: dict = field(default_factory=dict)


@dataclass
class PanasonicDataStore:
    """Root data container stored in hass.data[DOMAIN]."""

    entries: dict[str, dict[str, PanasonicDataUpdateCoordinator]] = field(
        default_factory=dict
    )
    custom: dict[str, EntryCustomData] = field(default_factory=dict)

    @classmethod
    def get(cls, hass: HomeAssistant) -> PanasonicDataStore:
        """Return the typed data store, creating it if necessary."""
        store = hass.data.get(DOMAIN)
        if not isinstance(store, PanasonicDataStore):
            store = PanasonicDataStore()
            hass.data[DOMAIN] = store
        return store

    def get_coordinators(
        self, entry_id: str
    ) -> dict[str, PanasonicDataUpdateCoordinator]:
        """Return coordinators for a config entry."""
        return self.entries.get(entry_id, {})

    def set_coordinator(
        self,
        entry_id: str,
        appliance_id: str,
        coordinator: PanasonicDataUpdateCoordinator,
    ) -> None:
        """Register a coordinator for an appliance."""
        self.entries.setdefault(entry_id, {})[appliance_id] = coordinator

    def init_entry(self, entry_id: str) -> None:
        """Initialize storage for a new config entry."""
        self.entries[entry_id] = {}

    def remove_entry(self, entry_id: str) -> None:
        """Remove all data associated with a config entry."""
        self.entries.pop(entry_id, None)
        self.custom.pop(entry_id, None)

    def has_entries(self) -> bool:
        """Return True if any config entries remain."""
        return bool(self.entries)

    def get_custom(self, entry_id: str) -> EntryCustomData:
        """Return (and create if needed) custom data for a config entry."""
        if entry_id not in self.custom:
            self.custom[entry_id] = EntryCustomData()
        return self.custom[entry_id]

    def iter_fridge_coordinators(
        self, appliance_id: str | None = None
    ) -> Iterator[PanasonicDataUpdateCoordinator]:
        """Yield refrigerator coordinators, optionally filtered by appliance_id."""
        for entry_coords in self.entries.values():
            for coord in entry_coords.values():
                if is_fridge_eoj(coord.eoj):
                    if not appliance_id or coord.appliance_id == appliance_id:
                        yield coord


@dataclass
class PanasonicPushStore:
    """Typed wrapper for hass.data[_PUSH_KEY]."""

    handlers: dict[str, PanasonicPushHandler] = field(default_factory=dict)

    @classmethod
    def get(cls, hass: HomeAssistant) -> PanasonicPushStore:
        """Return the push handler store, creating it if necessary."""
        store = hass.data.get(_PUSH_KEY)
        if not isinstance(store, PanasonicPushStore):
            store = PanasonicPushStore()
            hass.data[_PUSH_KEY] = store
        return store

    def set_handler(self, entry_id: str, handler: PanasonicPushHandler) -> None:
        """Register a push handler for a config entry."""
        self.handlers[entry_id] = handler

    def remove_handler(self, entry_id: str) -> PanasonicPushHandler | None:
        """Remove and return the push handler for a config entry."""
        return self.handlers.pop(entry_id, None)

    def has_handlers(self) -> bool:
        """Return True if any push handlers remain."""
        return bool(self.handlers)
