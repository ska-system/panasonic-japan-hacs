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
PUSH_KIND_DOOR = "alert_door_open_info"

# HA event names
EVENT_DOOR = f"{DOMAIN}_door_event"
EVENT_PUSH = f"{DOMAIN}_push_event"
