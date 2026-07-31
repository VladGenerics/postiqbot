"""TikTok Login Kit v2: OAuth-флоу и обновление access-токена."""
from __future__ import annotations

from urllib.parse import urlencode

import httpx

from bot.config import get_settings

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USERINFO_URL = "https://open.tiktokapis.com/v2/user/info/"

SCOPES = "user.info.basic,video.upload"


def build_auth_url(state: str) -> str:
    s = get_settings()
    params = {
        "client_key": s.tiktok_client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": s.tiktok_redirect_uri,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """code → токены. Возвращает dict с access_token, refresh_token, open_id, ..."""
    s = get_settings()
    data = {
        "client_key": s.tiktok_client_key,
        "client_secret": s.tiktok_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": s.tiktok_redirect_uri,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    payload = resp.json()
    if "access_token" not in payload:
        raise ValueError(f"TikTok token error: {payload}")
    return payload


async def refresh_access_token(refresh_token: str) -> dict:
    """refresh_token → свежий access_token (нужно перед каждой публикацией)."""
    s = get_settings()
    data = {
        "client_key": s.tiktok_client_key,
        "client_secret": s.tiktok_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    payload = resp.json()
    if "access_token" not in payload:
        raise ValueError(f"TikTok refresh error: {payload}")
    return payload


async def get_user_info(access_token: str) -> tuple[str, str]:
    """Вернуть (open_id, display_name) авторизовавшегося пользователя."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            USERINFO_URL,
            params={"fields": "open_id,display_name"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    data = resp.json().get("data", {}).get("user", {})
    open_id = data.get("open_id")
    if not open_id:
        raise ValueError(f"TikTok user info error: {resp.text}")
    name = data.get("display_name") or "TikTok"
    return open_id, name
