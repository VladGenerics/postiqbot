"""Обёртки над YouTube Data API v3 (синхронный клиент → вызывать через to_thread)."""
from __future__ import annotations

import json
import logging
import os
import time

import httplib2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger("postiqbot.youtube_api")

_CHUNK_SIZE = 8 * 1024 * 1024
_UPLOAD_RETRIES = 6

_INIT_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable&part=snippet,status"
)


class UploadSessionExpired(RuntimeError):
    """Resumable-сессия больше не жива: URI протух (~неделя) или сброшен сервером."""


def get_my_channel(creds: Credentials) -> tuple[str, str]:
    """Вернуть (channel_id, channel_title) аккаунта, выдавшего токен."""
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    resp = youtube.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        raise ValueError("this Google account has no YouTube channel")
    channel = items[0]
    return channel["id"], channel["snippet"]["title"]


def _upload_body(
    title: str, description: str, privacy_status: str
) -> dict:
    return {
        "snippet": {
            "title": (title or "video")[:100],
            "description": description or "",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }


def _authorized_http(creds: Credentials) -> httplib2.Http:
    """http с автоматическим обновлением access-токена по refresh."""
    return creds.authorize(httplib2.Http(timeout=120))


def _request_with_retries(http, uri: str, *, method: str, body: bytes, headers: dict):
    """Запрос к upload-эндпоинту с ретраями: сеть моргает, 5xx — дело частое."""
    last_exc: Exception | None = None
    for attempt in range(_UPLOAD_RETRIES + 1):
        try:
            resp, content = http.request(uri, method=method, body=body, headers=headers)
            if resp.status < 500:
                return resp, content
            last_exc = RuntimeError(f"YouTube upload: HTTP {resp.status} on {method}")
        except Exception as exc:  # noqa: BLE001 — httplib2 бросает разное
            last_exc = exc
        if attempt < _UPLOAD_RETRIES:
            pause = min(60, 2 ** attempt)
            logger.warning(
                "YouTube upload %s не удался (%s) — повтор через %d с",
                method, str(last_exc)[:150], pause,
            )
            time.sleep(pause)
    assert last_exc is not None
    raise last_exc


def create_upload_session(
    creds: Credentials,
    file_path: str,
    title: str,
    description: str = "",
    privacy_status: str = "private",
) -> str:
    """Инициировать resumable-сессию загрузки."""
    size = os.path.getsize(file_path)
    http = _authorized_http(creds)
    resp, content = _request_with_retries(
        http,
        _INIT_URL,
        method="POST",
        body=json.dumps(_upload_body(title, description, privacy_status)).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "video/*",
            "X-Upload-Content-Length": str(size),
        },
    )
    uri = resp.get("location")
    if resp.status != 200 or not uri:
        detail = content.decode(errors="replace")[:300] if content else ""
        raise RuntimeError(f"YouTube resumable init failed: {resp.status} {detail}")
    return uri


def _parse_range_end(range_header: str | None) -> int:
    """Из 'bytes=0-(N-1)' достать СЛЕДУЮЩИЙ байт для отправки (N)."""
    if not range_header or "=" not in range_header:
        return 0
    rng = range_header.split("=", 1)[1]
    if "-" not in rng:
        return 0
    end = rng.rsplit("-", 1)[1].strip()
    try:
        return int(end) + 1
    except ValueError:
        return 0


def resume_upload(creds: Credentials, resumable_uri: str, file_path: str) -> str:
    """Дозалить байты в resumable-сессию (с последнего полученного байта)."""
    size = os.path.getsize(file_path)
    http = _authorized_http(creds)

    resp, content = _request_with_retries(
        http,
        resumable_uri,
        method="PUT",
        body=b"",
        headers={"Content-Range": f"bytes */{size}", "Content-Length": "0"},
    )
    if resp.status in (200, 201):
        return json.loads(content.decode())["id"]
    if resp.status >= 400:
        raise UploadSessionExpired(
            f"YouTube resumable session dead: HTTP {resp.status}"
        )
    sent = _parse_range_end(resp.get("range"))

    logger.info("YouTube resumable: продолжаю с байта %d из %d", sent, size)
    with open(file_path, "rb") as f:
        f.seek(sent)
        while sent < size:
            chunk = f.read(_CHUNK_SIZE)
            start, end = sent, sent + len(chunk) - 1
            resp, content = _request_with_retries(
                http,
                resumable_uri,
                method="PUT",
                body=chunk,
                headers={
                    "Content-Type": "video/*",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{size}",
                },
            )
            if resp.status in (200, 201):
                return json.loads(content.decode())["id"]
            if resp.status == 308:
                sent = max(_parse_range_end(resp.get("range")), end + 1)
                f.seek(sent)
                continue
            if resp.status >= 400:
                raise UploadSessionExpired(
                    f"YouTube resumable session rejected chunk: HTTP {resp.status}"
                )
            raise RuntimeError(f"YouTube upload failed: HTTP {resp.status}")
    raise RuntimeError("YouTube upload ended without a final response")


def upload_video(
    creds: Credentials,
    file_path: str,
    title: str,
    description: str = "",
    privacy_status: str = "private",
) -> str:
    """Загрузить видео одним вызовом: создать сессию и сразу залить байты."""
    uri = create_upload_session(creds, file_path, title, description, privacy_status)
    return resume_upload(creds, uri, file_path)
