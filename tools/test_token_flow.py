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

def main():
    code_verifier, code_challenge, state, nonce = generate_pkce()
    auth_url = generate_login_url(code_challenge, state, nonce)
    
    print("以下のログインURLをブラウザで開き、ログインを行ってください。")
    print(auth_url)
    print("-" * 50)
    
    callback_url = input("ログイン後のコールバックURL全体を貼り付けてください: ").strip()
    
    parsed = urllib.parse.urlparse(callback_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    if "code" not in query_params:
        print("エラー: コールバックURLから認可コードが見つかりませんでした。")
        return
        
    code = query_params["code"][0]
    
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "KitchenPocketA/5.4.1",
    }
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": REDIRECT_URI,
    }
    
    response = requests.post(token_url, data=data, headers=headers, timeout=30)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {response.text}")

if __name__ == "__main__":
    main()