#!/usr/bin/env python3
"""
Test script for Panasonic push notifications via FCM.

Usage:
    1. First run - no credentials file yet, will register fresh:
       python test_push.py --token YOUR_ACCESS_TOKEN

    2. Subsequent runs - reuses saved credentials (no re-registration):
       python test_push.py --token YOUR_ACCESS_TOKEN

Press Ctrl+C to stop.
"""
import argparse
import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

import requests
from firebase_messaging import FcmPushClient, FcmRegisterConfig

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# Show all firebase_messaging traffic so we can see if any raw message arrives
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("firebase_messaging").setLevel(logging.DEBUG)

log = logging.getLogger("panasonic_push_test")

# ── Panasonic / Firebase constants ────────────────────────────────────────────
FIREBASE_SENDER_ID  = "209752140776"
FIREBASE_APP_ID     = "1:209752140776:android:8d43b943c43bb928"
FIREBASE_API_KEY    = "AIzaSyDARxcioH3WkPV7mLH5esQqMoknjbc1534"
FIREBASE_PROJECT_ID = "kitchen-pocket-mwo"

KAPF_API_BASE_URL = "https://api.kitchen-appliances-pf.com/api/kapf/v1"
REIZO_API_BASE_URL = "https://app.ref.apws.panasonic.com/reizo/v3"
API_KEY           = "x6pdB3r5z2eqDCgwf0gF1Ffre7Au7Km3YoFY0fDh"

CREDENTIALS_FILE = Path("push_credentials.json")

PUSH_KIND_DOOR           = "alert_door_open_info"
PUSH_KIND_WATER_SHORTAGE = "alert_water_shortage"
PUSH_KIND_ICE_COMPLETED  = "alert_ice_completed"
PUSH_KIND_ERROR          = "alert_error_occured"

KIND_LABELS = {
    PUSH_KIND_DOOR:           "🚪  Door left open (5 min)",
    PUSH_KIND_WATER_SHORTAGE: "💧  Water shortage",
    PUSH_KIND_ICE_COMPLETED:  "🧊  Ice making completed",
    PUSH_KIND_ERROR:          "⚠️  Error occurred",
}


# ── Panasonic push-term registration ──────────────────────────────────────────

def _reizo_date() -> str:
    """Current Japan time for X-Reizo-Date header."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Tokyo")
    except ImportError:
        import pytz
        tz = pytz.timezone("Asia/Tokyo")
    return datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S")


def link_push_to_device(access_token: str, appliance_id: str, term_id: str) -> dict:
    """GET devices/{appliance_id}/settings?term_id=... — links the push term to this fridge."""
    from urllib.parse import quote
    encoded_id = quote(appliance_id, safe="")
    url = f"{REIZO_API_BASE_URL}/devices/{encoded_id}/settings"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "X-Reizo-Date": _reizo_date(),
    }
    log.info("Linking push term to device via GET /devices/.../settings ...")
    resp = requests.get(url, params={"term_id": term_id}, headers=headers, timeout=30)
    log.info("  → %s %s", resp.status_code, resp.text[:400])
    resp.raise_for_status()
    return resp.json()


def get_appliance_id(access_token: str) -> str | None:
    """Fetch appliance_id from user info."""
    url = f"{KAPF_API_BASE_URL}/user/info"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "X-API-Key": API_KEY,
        "User-Agent": "KitchenPocketA/5.1.0",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    for appliance in data.get("myAppliances", []):
        log.info("Found appliance: eoj=%s info=%s", appliance.get("eoj"), appliance.get("info", {}).get("productCode"))
        if appliance.get("eoj") == "03B7":
            return appliance["info"]["applianceId"]
    # fallback: return first appliance
    appliances = data.get("myAppliances", [])
    if appliances:
        log.warning("No EOJ 03B7 found, using first appliance")
        return appliances[0]["info"]["applianceId"]
    return None


def register_push_term(access_token: str, term_id: str, fcm_token: str, firebase_install_id: str) -> dict:
    """POST /push/new-term — mirrors what the Android app does."""
    url = f"{KAPF_API_BASE_URL}/push/new-term"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "X-API-Key": API_KEY,
        "User-Agent": "KitchenPocketA/5.1.0",
    }
    payload = {
        "smpLocale": "ja",
        "termId": term_id,
        "token": fcm_token,
        "type": "1",
        "firebaseInstallId": firebase_install_id,
    }
    log.info("Registering push term with Panasonic API …")
    log.debug("  term_id=%s  token=%s…  fid=%s", term_id, fcm_token[:20], firebase_install_id[:8])
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    log.info("  → %s %s", resp.status_code, resp.text[:200])
    resp.raise_for_status()
    return resp.json()


# ── Credential persistence ─────────────────────────────────────────────────────

def load_credentials() -> dict | None:
    if CREDENTIALS_FILE.exists():
        data = json.loads(CREDENTIALS_FILE.read_text())
        log.info("Loaded saved credentials from %s", CREDENTIALS_FILE)
        return data
    return None


def save_credentials(creds: dict) -> None:
    CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2))
    log.info("Credentials saved to %s", CREDENTIALS_FILE)


# ── FCM message callback ───────────────────────────────────────────────────────

def on_message(data: dict, sender_id: str, context=None) -> None:
    kind        = data.get("kind", "")
    appliance   = data.get("appliance_id", "")
    title       = data.get("title", "")
    body        = data.get("body", "")

    print("\n" + "═" * 60)
    print(f"  📨  Push message received!")
    print(f"  kind        : {kind}")
    print(f"  appliance_id: {appliance}")
    print(f"  title       : {title}")
    print(f"  body        : {body}")
    print(f"  sender_id   : {sender_id}")
    print(f"  raw data    : {data}")
    print("═" * 60 + "\n")

    label = KIND_LABELS.get(kind, f"📩  Unknown event ({kind})")
    print(label)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main(access_token: str, appliance_id: str | None = None) -> None:
    saved = load_credentials()
    term_id: str = (saved or {}).get("panasonic_term_id") or str(uuid.uuid4())

    fcm_config = FcmRegisterConfig(
        project_id=FIREBASE_PROJECT_ID,
        app_id=FIREBASE_APP_ID,
        api_key=FIREBASE_API_KEY,
        messaging_sender_id=FIREBASE_SENDER_ID,
        bundle_id="com.panasonic.jp.kitchenpocket",
    )

    # credentials_updated_callback is called whenever FCM rotates the token
    def on_credentials_updated(new_creds: dict) -> None:
        new_creds["panasonic_term_id"] = term_id
        save_credentials(new_creds)

    client = FcmPushClient(
        callback=on_message,
        fcm_config=fcm_config,
        credentials=saved,
        credentials_updated_callback=on_credentials_updated,
    )

    log.info("Checking in / registering with Firebase …")
    fcm_token = await client.checkin_or_register()
    log.info("FCM token: %s…", fcm_token[:30])

    # Only register with Panasonic if we got a fresh token (no saved creds, or creds changed)
    old_token = (saved or {}).get("fcm", {}).get("registration", {}).get("token")
    if fcm_token != old_token:
        # fid lives at credentials["fcm"]["installation"]["fid"]
        firebase_install_id = (
            client.credentials.get("fcm", {}).get("installation", {}).get("fid")
            or str(uuid.uuid4())
        )
        result = register_push_term(access_token, term_id, fcm_token, firebase_install_id)
        returned_term_id = result.get("termId", term_id)

        # Persist credentials + term_id together
        creds_to_save = dict(client.credentials)
        creds_to_save["panasonic_term_id"] = returned_term_id
        save_credentials(creds_to_save)
        log.info("Push term registered. termId=%s", returned_term_id)
    else:
        log.info("Reusing existing FCM token and push term (no re-registration needed)")

    # Step 3: link the push term to the specific fridge device
    if not appliance_id:
        appliance_id = await asyncio.get_event_loop().run_in_executor(
            None, get_appliance_id, access_token
        )
    if appliance_id:
        await asyncio.get_event_loop().run_in_executor(
            None, link_push_to_device, access_token, appliance_id, term_id
        )
    else:
        log.warning("Could not find appliance_id — skipping device link step")

    log.info("Starting FCM listener … (open/close your fridge door, then check here)")
    await client.start()

    # Keep running until Ctrl+C
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        log.info("Stopping …")
        await client.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Panasonic FCM push notifications")
    parser.add_argument(
        "--token",
        required=True,
        help="Panasonic access token (from HA config entry or login flow)",
    )
    parser.add_argument(
        "--appliance-id",
        default=None,
        help="Appliance ID (optional, will be fetched automatically if not provided)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.token, args.appliance_id))
    except KeyboardInterrupt:
        print("\nStopped.")
