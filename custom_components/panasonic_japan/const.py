"""Constants for the Panasonic Japan integration."""
from __future__ import annotations

DOMAIN = "panasonic_japan"

# API Configuration
API_BASE_URL = "https://app.ref.apws.panasonic.com/reizo/v3"
KAPF_API_BASE_URL = "https://api.kitchen-appliances-pf.com/api/kapf/v1"
AUTH0_DOMAIN = "auth.digital.panasonic.com"
AUTH0_CLIENT_ID = "w7UI3iLByFFz3GOj6Ef6BCHfPczOcsy8"
AUTH0_AUDIENCE = "https://club.panasonic.jp/w7UI3iLByFFz3GOj6Ef6BCHfPczOcsy8/api/v1/"
AUTH0_TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
API_KEY = "x6pdB3r5z2eqDCgwf0gF1Ffre7Au7Km3YoFY0fDh"

# Status usages values (eUsagesItem enum from Android app)
USAGES_TOP_SCREEN     = 1   # returns: operation_mode, cooloven_in_seconds, house_sitting, etc.
USAGES_SETTING_SCREEN = 2   # returns: all control fields (ice, lights, modes)

# Default values
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
BASELINE_COST = 750  # yen/month
YEN_PER_KWH = 31  # yen/kWh

# Attributes
ATTR_APPLIANCE_ID = "appliance_id"
ATTR_PRODUCT_CODE = "product_code"
ATTR_OPERATION_MODE = "operation_mode"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_COST_REDUCTION = "cost_reduction"
ATTR_ELECTRICITY_USAGE = "electricity_usage"

# Device types
DEVICE_TYPE_FRIDGE = "fridge"

# Firebase / FCM configuration (from Panasonic Kitchen Pocket app)
FIREBASE_SENDER_ID = "209752140776"
FIREBASE_APP_ID = "1:209752140776:android:8d43b943c43bb928"
FIREBASE_API_KEY = "AIzaSyDARxcioH3WkPV7mLH5esQqMoknjbc1534"
FIREBASE_PROJECT_ID = "kitchen-pocket-mwo"

# Push notification types
PUSH_TYPE = "1"  # FCM push type used by Panasonic app

# Push notification kinds (kind field in FCM payload)
PUSH_KIND_DOOR           = "alert_door_open_info"    # Door left open for 5 minutes
PUSH_KIND_WATER_SHORTAGE = "alert_water_shortage"
PUSH_KIND_ICE_COMPLETED  = "alert_ice_completed"
PUSH_KIND_ERROR          = "alert_error_occured"     # Note: Panasonic typo
PUSH_KIND_COOLOVEN_COMPLETED = "alert_cooloven_completed"
PUSH_KIND_COOLOVEN_CANCELED  = "alert_cooloven_canceled"
PUSH_KIND_COOLOVEN_CHANGED   = "alert_cooloven_changed"

# HA event names
EVENT_DOOR           = f"{DOMAIN}_door_event"
EVENT_WATER_SHORTAGE = f"{DOMAIN}_water_shortage_event"
EVENT_ICE_COMPLETED  = f"{DOMAIN}_ice_completed_event"
EVENT_ERROR          = f"{DOMAIN}_error_event"
EVENT_COOLOVEN_COMPLETED = f"{DOMAIN}_cooloven_completed_event"
EVENT_COOLOVEN_CANCELED  = f"{DOMAIN}_cooloven_canceled_event"
EVENT_COOLOVEN_CHANGED   = f"{DOMAIN}_cooloven_changed_event"
EVENT_PUSH           = f"{DOMAIN}_push_event"