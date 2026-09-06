#!/usr/bin/env python3
"""
Test script for Panasonic API token refresh.

Usage:
    python test_refresh.py --refresh-token YOUR_REFRESH_TOKEN
"""
import argparse
import json
import requests

# auth0 settings derived from integration constants
AUTH0_TOKEN_URL = "https://pdpauth-a1.panasonic.auth0.com/oauth/token"
AUTH0_CLIENT_ID = "w7UI3iLByFFz3GOj6Ef6BCHfPczOcsy8"

def refresh_access_token(refresh_token: str) -> dict:
    """Execute token refresh request to Auth0."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "KitchenPocketA/5.4.1",
    }
    data = {
        "grant_type": "refresh_token",
        "client_id": AUTH0_CLIENT_ID,
        "refresh_token": refresh_token,
    }

    print(f"\nSending refresh request to {AUTH0_TOKEN_URL} ...")
    response = requests.post(AUTH0_TOKEN_URL, data=data, headers=headers, timeout=30)
    
    print(f"Response status: {response.status_code}")
    return response.json()

def main() -> None:
    parser = argparse.ArgumentParser(description="Test Panasonic token refresh")
    parser.add_argument("--refresh-token", required=True, help="Valid refresh token")
    args = parser.parse_args()

    try:
        result = refresh_access_token(args.refresh_token)
        print("\n--- Token Refresh Result ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("----------------------------")
    except Exception as e:
        print(f"\nError during token refresh: {e}")

if __name__ == "__main__":
    main()