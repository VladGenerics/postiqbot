"""OAuth2-флоу для YouTube: генерация auth URL, обмен code на токены, восстановление Credentials из refresh-токена."""
from __future__ import annotations

import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_config(client_id: str, client_secret: str, redirect_uri: str) -> dict:
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": _AUTH_URI,
            "token_uri": _TOKEN_URI,
            "redirect_uris": [redirect_uri],
        }
    }


def build_auth_url(
    client_id: str, client_secret: str, redirect_uri: str, state: str
) -> str:
    """Сформировать ссылку на экран согласия Google."""
    flow = Flow.from_client_config(
        _client_config(client_id, client_secret, redirect_uri),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return url


def exchange_code(
    client_id: str, client_secret: str, redirect_uri: str, code: str
) -> Credentials:
    """Обменять authorization code на токены (синхронно)."""
    flow = Flow.from_client_config(
        _client_config(client_id, client_secret, redirect_uri),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_from_refresh_token(
    refresh_token: str, client_id: str, client_secret: str
) -> Credentials:
    """Восстановить Credentials из сохранённого refresh-токена (для публикации)."""
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
