"""Обёртки над YouTube Data API v3 (синхронный клиент → вызывать через to_thread)."""
from __future__ import annotations

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def get_my_channel(creds: Credentials) -> tuple[str, str]:
    """Вернуть (channel_id, channel_title) аккаунта, выдавшего токен."""
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    resp = youtube.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        raise ValueError("У аккаунта нет YouTube-канала")
    channel = items[0]
    return channel["id"], channel["snippet"]["title"]


def upload_video(
    creds: Credentials,
    file_path: str,
    title: str,
    description: str = "",
    privacy_status: str = "private",
) -> str:
    """Загрузить видео (resumable upload). Вернуть youtube video_id."""
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": (title or "video")[:100],
            "description": description or "",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/*")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    return response["id"]
