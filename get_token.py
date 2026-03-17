#!/usr/bin/env python3
"""
Standalone login helper — runs the same PKCE OAuth2 flow as the HA config flow
and prints the access token so you can use it with test_push.py.

Usage:
    python get_token.py
"""
import base64
import hashlib
import json
import secrets
from urllib.parse import parse_qs, quote, urlparse

import requests

AUTH0_DOMAIN    = "auth.digital.panasonic.com"
AUTH0_CLIENT_ID = "w7UI3iLByFFz3GOj6Ef6BCHfPczOcsy8"
REDIRECT_URI    = (
    "com.panasonic.jp.kitchenpocket.auth0://"
    "auth.digital.panasonic.com/android/"
    "com.panasonic.jp.kitchenpocket/callback"
)
SCOPE = (
    "openid kitchenpocket.service smartrf_prd.control "
    "eatpick.service offline_access"
)


def _pkce():
    verifier  = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    return verifier, challenge, state, nonce


def _login_url(challenge, state, nonce):
    auth0_client = base64.b64encode(
        json.dumps(
            {"name": "Auth0.Android", "env": {"android": "31"}, "version": "2.5.0"},
            separators=(",", ":"),
        ).encode()
    ).decode()

    params = "&".join([
        f"scope={quote(SCOPE)}",
        f"audience={quote('https://club.panasonic.jp/' + AUTH0_CLIENT_ID + '/api/v1/')}",
        "response_type=code",
        f"code_challenge={challenge}",
        "code_challenge_method=S256",
        f"auth0Client={quote(auth0_client)}",
        f"client_id={AUTH0_CLIENT_ID}",
        f"redirect_uri={quote(REDIRECT_URI)}",
        f"state={state}",
        f"nonce={nonce}",
    ])
    return f"https://{AUTH0_DOMAIN}/authorize?{params}"


def main():
    verifier, challenge, state, nonce = _pkce()
    url = _login_url(challenge, state, nonce)

    print("\n" + "═" * 70)
    print("STEP 1 — Open this URL in your browser and log in:")
    print("═" * 70)
    print(url)
    print("═" * 70)
    print(
        "\nSTEP 2 — After login you'll be redirected to a URL starting with:\n"
        "  com.panasonic.jp.kitchenpocket.auth0://...\n"
        "Copy the ENTIRE URL and paste it below.\n"
    )

    callback = input("Callback URL: ").strip()

    parsed = urlparse(callback)
    code   = parse_qs(parsed.query).get("code", [None])[0]
    if not code:
        print("ERROR: could not find 'code' in the callback URL.")
        return

    print("\nExchanging code for tokens …")
    resp = requests.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",
        data={
            "grant_type":    "authorization_code",
            "client_id":     AUTH0_CLIENT_ID,
            "code":          code,
            "redirect_uri":  REDIRECT_URI,
            "code_verifier": verifier,
        },
        timeout=30,
    )
    resp.raise_for_status()
    tokens = resp.json()

    access_token  = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")

    print("\n" + "═" * 70)
    print("ACCESS TOKEN (use with test_push.py --token):")
    print(access_token)
    if refresh_token:
        print("\nREFRESH TOKEN (optional, save for later):")
        print(refresh_token)
    print("═" * 70 + "\n")


if __name__ == "__main__":
    main()
