import base64
import hashlib
import json
import os
import secrets
import urllib.parse
import requests

AUTH0_DOMAIN = "auth.digital.panasonic.com"
CLIENT_ID = "w7UI3iLByFFz3GOj6Ef6BCHfPczOcsy8"
AUDIENCE = "https://club.panasonic.jp/w7UI3iLByFFz3GOj6Ef6BCHfPczOcsy8/api/v1/"
REDIRECT_URI = "com.panasonic.jp.kitchenpocket.auth0://auth.digital.panasonic.com/android/com.panasonic.jp.kitchenpocket/callback"
SCOPE = "openid kitchenpocket.service smartrf_prd.control eatpick.service offline_access"

def generate_pkce():
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
    code_challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_bytes).decode("utf-8").rstrip("=")
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    return code_verifier, code_challenge, state, nonce

def generate_login_url(code_challenge, state, nonce):
    auth0_client = {
        "name": "Auth0.Android",
        "env": {"android": "31"},
        "version": "2.5.0",
    }
    auth0_client_json = json.dumps(auth0_client, separators=(",", ":"))
    auth0_client_b64 = base64.b64encode(auth0_client_json.encode("utf-8")).decode("utf-8")
    auth0_client_encoded = urllib.parse.quote(auth0_client_b64)

    params = {
        "scope": urllib.parse.quote(SCOPE),
        "audience": urllib.parse.quote(AUDIENCE),
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "auth0Client": auth0_client_encoded,
        "client_id": CLIENT_ID,
        "redirect_uri": urllib.parse.quote(REDIRECT_URI),
        "state": state,
        "nonce": nonce,
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://{AUTH0_DOMAIN}/authorize?{query_string}"

if __name__ == "__main__":
    code_verifier, code_challenge, state, nonce = generate_pkce()
    url = generate_login_url(code_challenge, state, nonce)
    print("=== code_verifier (あとで使用します) ===")
    print(code_verifier)
    print("=======================================")
    print("\n以下のログインURLをブラウザで開いてください:")
    print(url)