"""Cooling assist helper functions and validation logic for Panasonic Japan integration."""
from __future__ import annotations

from typing import TypedDict


class CoolingAssistBounds(TypedDict):
    """Bounds and step definition for cooling assist mode."""

    min_time: int
    max_time: int
    step_time: int
    min_sec: int
    max_sec: int
    step_sec: int


COOLING_ASSIST_BOUNDS: dict[str, CoolingAssistBounds] = {
    "quench": {
        "min_time": 0,
        "max_time": 10,
        "step_time": 1,
        "min_sec": 0,
        "max_sec": 50,
        "step_sec": 10,
    },
    "cold": {
        "min_time": 10,
        "max_time": 30,
        "step_time": 1,
        "min_sec": 0,
        "max_sec": 0,
        "step_sec": 10,
    },
    "frozen": {
        "min_time": 30,
        "max_time": 60,
        "step_time": 1,
        "min_sec": 0,
        "max_sec": 0,
        "step_sec": 10,
    },
    "freeze": {
        "min_time": 30,
        "max_time": 60,
        "step_time": 1,
        "min_sec": 0,
        "max_sec": 0,
        "step_sec": 10,
    },
    "off": {
        "min_time": 0,
        "max_time": 0,
        "step_time": 1,
        "min_sec": 0,
        "max_sec": 0,
        "step_sec": 10,
    },
}

DEFAULT_TIMES: dict[str, tuple[int, int]] = {
    "quench": (5, 0),
    "cold": (15, 0),
    "frozen": (45, 0),
    "freeze": (45, 0),
    "off": (0, 0),
}


def get_cooling_assist_bounds(mode: str) -> CoolingAssistBounds:
    """Return bounds and step for given cooling assist mode."""
    return COOLING_ASSIST_BOUNDS.get(
        mode,
        {
            "min_time": 0,
            "max_time": 60,
            "step_time": 1,
            "min_sec": 0,
            "max_sec": 50,
            "step_sec": 10,
        },
    )


def get_default_cooling_assist_time(mode: str) -> tuple[int, int]:
    """Return (default_minutes, default_seconds) for given mode."""
    return DEFAULT_TIMES.get(mode, (0, 0))


def clamp_cooling_assist_values(mode: str, time_min: int | float, time_sec: int | float) -> tuple[int, int]:
    """Clamp time (minutes) and second to the allowed range for given mode."""
    try:
        t_int = int(time_min)
    except (TypeError, ValueError):
        t_int = 0

    try:
        s_int = int(time_sec)
    except (TypeError, ValueError):
        s_int = 0

    bounds = get_cooling_assist_bounds(mode)

    if mode == "quench":
        clamped_time = max(bounds["min_time"], min(bounds["max_time"], t_int))
        # Snap second to multiple of step_sec (10)
        clamped_sec = (max(bounds["min_sec"], min(bounds["max_sec"], s_int)) // 10) * 10
        return clamped_time, clamped_sec

    if mode in ("cold", "frozen", "freeze"):
        clamped_time = max(bounds["min_time"], min(bounds["max_time"], t_int))
        return clamped_time, 0

    return 0, 0
