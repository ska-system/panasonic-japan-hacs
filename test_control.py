#!/usr/bin/env python3
"""
Test script for Panasonic fridge control API.

Usage:
    python test_control.py --token YOUR_ACCESS_TOKEN

Fetches current device status then shows an interactive menu to test each control.
"""
import argparse
import json
import sys
from datetime import datetime
from urllib.parse import quote

import requests

REIZO_API_BASE_URL = "https://app.ref.apws.panasonic.com/reizo/v3"
KAPF_API_BASE_URL  = "https://api.kitchen-appliances-pf.com/api/kapf/v1"
API_KEY            = "x6pdB3r5z2eqDCgwf0gF1Ffre7Au7Km3YoFY0fDh"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _reizo_date() -> str:
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Tokyo")
    except ImportError:
        import pytz
        tz = pytz.timezone("Asia/Tokyo")
    return datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S")


def _headers(token: str) -> dict:
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Reizo-Date": _reizo_date(),
    }


def _encode(appliance_id: str) -> str:
    """Convert appliance_id to base64url path segment (matches Android z() method)."""
    return appliance_id.replace("+", "-").replace("/", "_")


# ── API calls ──────────────────────────────────────────────────────────────────

def get_appliance_id(token: str) -> tuple[str, str]:
    """Return (appliance_id, product_code) for the first fridge found."""
    resp = requests.get(
        f"{KAPF_API_BASE_URL}/user/info",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "X-API-Key": API_KEY,
            "User-Agent": "KitchenPocketA/5.4.1",
        },
        timeout=30,
    )
    resp.raise_for_status()
    for a in resp.json().get("myAppliances", []):
        print(f"  Found appliance: eoj={a.get('eoj')}  model={a['info'].get('productCode')}")
        if a.get("eoj") == "03B7":
            return a["info"]["applianceId"], a["info"].get("productCode", "")
    # fallback to first
    appliances = resp.json().get("myAppliances", [])
    if appliances:
        a = appliances[0]
        return a["info"]["applianceId"], a["info"].get("productCode", "")
    raise RuntimeError("No appliance found")


def get_status(token: str, appliance_id: str) -> dict:
    # usages=2 = VIEWED_SETTING_SCREEN — returns all control fields
    resp = requests.get(
        f"{REIZO_API_BASE_URL}/devices/{_encode(appliance_id)}/status",
        headers=_headers(token),
        params={"usages": 2},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_functions(token: str, appliance_id: str) -> dict:
    resp = requests.get(
        f"{REIZO_API_BASE_URL}/products/{_encode(appliance_id)}/functions",
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def control(token: str, appliance_id: str, payload: dict) -> dict:
    """PUT /devices/{id}/status with control payload."""
    print(f"\n  → Sending: {json.dumps(payload)}")
    resp = requests.put(
        f"{REIZO_API_BASE_URL}/devices/{_encode(appliance_id)}/status",
        headers=_headers(token),
        json=payload,
        timeout=30,
    )
    print(f"  ← {resp.status_code}")
    print(f"  PUT response: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    resp.raise_for_status()
    return resp.json()


def probe_endpoints(token: str, appliance_id: str) -> None:
    """Try all usages values to find which one returns control fields."""
    # usages enum: 1=TOP, 2=SETTING, 3=COOLING_ASSIST, 4=ECO_NAVI, 5=VERSION,
    #              6=PARTIAL_FREEZING, 7=OUTAGE_PREPARE
    print("\n── Probing usages values ──")
    for usages in range(1, 8):
        url = f"{REIZO_API_BASE_URL}/devices/{_encode(appliance_id)}/status"
        try:
            r = requests.get(url, headers=_headers(token), params={"usages": usages}, timeout=15)
            data = r.json() if r.status_code == 200 else {}
            fields = [k for k in data if k not in ("appliance_id", "operation_mode",
                      "device_err_status", "firmware_current_version",
                      "firmware_latest_version", "firmware_update_status")]
            print(f"  usages={usages} → {r.status_code}  extra fields: {fields}")
        except Exception as e:
            print(f"  usages={usages} → ERROR: {e}")


# ── Interactive menu ───────────────────────────────────────────────────────────

def ask(prompt: str, choices: list[str]) -> str:
    while True:
        print(f"\n{prompt}")
        for i, c in enumerate(choices, 1):
            print(f"  {i}. {c}")
        raw = input("Choice (number or value): ").strip()
        if raw in choices:
            return raw
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print("  Invalid, try again.")


def ask_bool(prompt: str, current: bool) -> bool:
    val = ask(f"{prompt} (current: {current})", ["true", "false"])
    return val == "true"


def ask_enum(prompt: str, choices: list[str], current: str) -> str:
    return ask(f"{prompt} (current: {current})", choices)


LAMP_MODES   = ["off", "dark", "bright"]
TEMP_MODES   = ["weak", "medium", "strong"]
PARTIAL_MODES = ["chilled", "weak", "medium", "strong"]
PARTIAL_FREEZE_MODES = ["freezingWeak", "freezingMedium", "freezingStrong",
                        "partialWeak", "partialMedium", "partialStrong"]
COOLOVEN_MODES = ["off", "quench", "cold", "frozen"]
DOOR_ALARM_MODES = ["off", "quiet", "normal", "loud"]


CONTROLS = [
    # (menu label, field, kind, options/None)
    ("Fast ice ON/OFF",         "fast_ice_status",          "bool",  None),
    ("Stop ice ON/OFF",         "stop_ice_status",           "bool",  None),
    ("Fresh frozen ON/OFF",     "fresh_frozen_status",       "bool",  None),
    ("Econavi lamp ON/OFF",     "econavi_lamp_status",       "bool",  None),
    ("Cold room light mode",    "coldroom_light_mode",       "enum",  LAMP_MODES),
    ("PC room light mode",      "pcroom_light_mode",         "enum",  LAMP_MODES),
    ("Cool oven lamp mode",     "cooloven_lamp_mode",        "enum",  LAMP_MODES),
    ("Cool oven mode",          "cooloven_mode",             "enum",  COOLOVEN_MODES),
    ("Cool oven time (min)",    "cooloven_time",             "int",   None),
    ("Cold room temp adjust",   "cold_room_mode",            "enum",  TEMP_MODES),
    ("Freezer temp adjust",     "freezing_room_mode",        "enum",  TEMP_MODES),
    ("Partial compartment mode","partial_mode",              "enum",  PARTIAL_MODES),
    ("Partial freezing mode",   "partial_freezing_room_mode","enum",  PARTIAL_FREEZE_MODES),
    ("Door alarm mode",         "door_alarms_mode",          "enum",  DOOR_ALARM_MODES),
]


def print_status(status: dict) -> None:
    print("\n" + "═" * 60)
    print("  Current device status")
    print("═" * 60)
    interesting = [
        "operation_mode", "fast_ice_status", "stop_ice_status",
        "fresh_frozen_status", "econavi_lamp_status",
        "coldroom_light_mode", "pcroom_light_mode", "cooloven_lamp_mode",
        "cooloven_mode", "cold_room_mode", "freezing_room_mode",
        "partial_mode", "partial_freezing_room_mode", "door_alarms_mode",
        "winter_setting_status", "house_sitting_status",
        "firmware_current_version",
    ]
    for key in interesting:
        if key in status:
            print(f"  {key:<35} {status[key]}")
    print("═" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Panasonic fridge controls")
    parser.add_argument("--token", required=True, help="Panasonic access token")
    parser.add_argument("--appliance-id", default=None)
    args = parser.parse_args()

    token = args.token

    print("\nFetching appliance info …")
    if args.appliance_id:
        appliance_id = args.appliance_id
        product_code = ""
    else:
        appliance_id, product_code = get_appliance_id(token)
    print(f"  Appliance ID : {appliance_id}")
    print(f"  Product code : {product_code}")

    print("\nFetching current status …")
    status = get_status(token, appliance_id)
    print("\n  RAW status response:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    print_status(status)

    print("\nFetching supported functions …")
    try:
        functions = get_functions(token, appliance_id)
        print(f"  Functions: {json.dumps(functions, ensure_ascii=False)[:400]}")
    except Exception as e:
        print(f"  (functions endpoint error: {e})")
        functions = {}

    # Main control loop
    while True:
        print("\n" + "═" * 60)
        print("  SELECT A CONTROL TO TEST  (0 to refresh status, q to quit)")
        print("═" * 60)
        for i, (label, field, _, _) in enumerate(CONTROLS, 1):
            current = status.get(field, "—")
            print(f"  {i:2}. {label:<35} (now: {current})")
        print("   0. Refresh status")
        print("   q. Quit")

        choice = input("\nChoice: ").strip().lower()
        if choice == "q":
            break
        if choice == "0":
            status = get_status(token, appliance_id)
            print_status(status)
            continue

        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(CONTROLS)):
                raise ValueError
        except ValueError:
            print("  Invalid choice.")
            continue

        label, field, kind, options = CONTROLS[idx]
        current = status.get(field)

        try:
            if kind == "bool":
                new_val = ask_bool(label, bool(current))
                result = control(token, appliance_id, {field: new_val})
            elif kind == "enum":
                new_val = ask_enum(label, options, str(current))
                result = control(token, appliance_id, {field: new_val})
            elif kind == "int":
                raw = input(f"  Enter value (current: {current}): ").strip()
                result = control(token, appliance_id, {field: int(raw)})

            # Refresh status after successful control
            status = get_status(token, appliance_id)
            print_status(status)

        except requests.HTTPError as e:
            print(f"\n  ✗ API error: {e}")
        except (ValueError, KeyboardInterrupt):
            print("\n  Cancelled.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
