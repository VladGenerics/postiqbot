"""TikTok Content Posting API — публикация видео."""
from __future__ import annotations

import asyncio
import logging
import os
from urllib.parse import quote

import httpx

logger = logging.getLogger("postiqbot.tiktok_api")

INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
DIRECT_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

PRIVACY_LEVELS = (
    "PUBLIC_TO_EVERYONE",
    "FOLLOWER_OF_CREATOR",
    "MUTUAL_FOLLOW_FRIENDS",
    "SELF_ONLY",
)


def profile_url(info: dict) -> str | None:
    """Ссылка на страницу аккаунта-получателя по данным creator_info."""
    username = str(info.get("creator_username") or "").strip().lstrip("@").strip()
    if not username:
        return None
    return f"https://www.tiktok.com/@{quote(username, safe='._-')}"


class TikTokScopeError(RuntimeError):
    """Токен выдан без нужного scope — пользователю надо переподключить аккаунт."""


class TikTokUnauditedError(RuntimeError):
    """Приложение не прошло аудит TikTok: Direct Post разрешён только в приватные аккаунты (фактически SELF_ONLY)."""


def _raise_for_error(payload: dict, ctx: str) -> None:
    """Разобрать поле error ответа TikTok."""
    err = (payload.get("error") or {}) if isinstance(payload, dict) else {}
    code = err.get("code") or ""
    if code and code != "ok":
        msg = f"TikTok {ctx}: {code} {err.get('message', '')}".strip()
        if code == "unaudited_client_can_only_post_to_private_accounts":
            raise TikTokUnauditedError(msg)
        if "scope" in code or "scope" in str(err.get("message", "")).lower():
            raise TikTokScopeError(msg)
        raise ValueError(msg)


async def upload_to_inbox(access_token: str, file_path: str) -> str:
    """Залить файл в черновики TikTok. Вернуть publish_id."""
    size = os.path.getsize(file_path)
    init_body = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": size,
            "total_chunk_count": 1,
        }
    }
    async with httpx.AsyncClient(timeout=180) as client:
        init = await client.post(
            INBOX_INIT_URL,
            json=init_body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        payload = init.json()
        data = payload.get("data") or {}
        publish_id = data.get("publish_id")
        upload_url = data.get("upload_url")
        if not publish_id or not upload_url:
            _raise_for_error(payload, "inbox init")
            raise ValueError(f"TikTok inbox init error: {payload}")

        await _put_file(client, upload_url, file_path, size)

    return publish_id


async def get_creator_info(access_token: str) -> dict:
    """Данные аккаунта для карточки подтверждения."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            CREATOR_INFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
    payload = resp.json()
    data = payload.get("data") or {}
    if not data.get("privacy_level_options"):
        _raise_for_error(payload, "creator_info")
        raise ValueError(f"TikTok creator_info error: {payload}")
    return data


async def direct_post(
    access_token: str,
    file_path: str,
    title: str,
    *,
    privacy: str,
    disable_comment: bool = True,
    disable_duet: bool = True,
    disable_stitch: bool = True,
    brand_content_toggle: bool = False,
    brand_organic_toggle: bool = False,
    creator_info: dict | None = None,
) -> str:
    """Прямая публикация в TikTok (Direct Post, scope video.publish)."""
    if not privacy:
        raise ValueError("privacy_level не выбран пользователем")
    if brand_content_toggle and privacy == "SELF_ONLY":
        raise ValueError("Branded content нельзя публиковать как SELF_ONLY")

    size = os.path.getsize(file_path)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=180) as client:
        options = list((creator_info or {}).get("privacy_level_options") or [])
        if not options:
            ci = await client.post(CREATOR_INFO_URL, headers=headers)
            ci_payload = ci.json()
            options = (ci_payload.get("data") or {}).get("privacy_level_options") or []
            if not options:
                _raise_for_error(ci_payload, "creator_info")
                raise ValueError(f"TikTok creator_info error: {ci_payload}")
        if privacy not in options:
            raise ValueError(
                f"privacy_level_option_mismatch: {privacy} недоступен "
                f"(разрешено: {', '.join(options)})"
            )

        init_body = {
            "post_info": {
                "title": (title or "")[:150],
                "privacy_level": privacy,
                "disable_comment": disable_comment,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
                "brand_content_toggle": brand_content_toggle,
                "brand_organic_toggle": brand_organic_toggle,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            },
        }
        init = await client.post(DIRECT_INIT_URL, json=init_body, headers=headers)
        payload = init.json()
        data = payload.get("data") or {}
        publish_id = data.get("publish_id")
        upload_url = data.get("upload_url")
        if not publish_id or not upload_url:
            _raise_for_error(payload, "direct init")
            raise ValueError(f"TikTok direct init error: {payload}")

        await _put_file(client, upload_url, file_path, size)

    return publish_id


async def _put_file(
    client: httpx.AsyncClient, upload_url: str, file_path: str, size: int
) -> None:
    """Залить байты одним чанком на выданный TikTok upload_url."""
    with open(file_path, "rb") as f:
        content = f.read()
    put = await client.put(
        upload_url,
        content=content,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        },
    )
    if put.status_code not in (200, 201):
        raise ValueError(f"TikTok upload failed: {put.status_code} {put.text}")


async def poll_publish_status(
    access_token: str, publish_id: str, *, attempts: int = 10, delay: float = 6.0
) -> str:
    """Дождаться реального завершения публикации."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    status = "PROCESSING_UPLOAD"
    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(attempts):
            await asyncio.sleep(delay)
            try:
                resp = await client.post(
                    STATUS_URL, json={"publish_id": publish_id}, headers=headers
                )
                payload = resp.json()
            except Exception:  # noqa: BLE001 — сеть моргнула, пробуем ещё
                logger.warning("Опрос статуса %s не удался, повтор", publish_id)
                continue
            data = payload.get("data") or {}
            status = data.get("status") or status
            if status == "PUBLISH_COMPLETE":
                return status
            if status == "FAILED":
                reason = data.get("fail_reason") or payload
                raise ValueError(f"TikTok publish failed: {reason}")
    logger.info("Статус publish_id=%s не финализирован: %s", publish_id, status)
    return status
