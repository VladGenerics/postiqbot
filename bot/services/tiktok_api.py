"""TikTok Content Posting API — загрузка видео в «инбокс» (черновики)."""
from __future__ import annotations

import os

import httpx

INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
DIRECT_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"


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
            raise ValueError(f"TikTok inbox init error: {payload}")

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

    return publish_id


async def direct_post(access_token: str, file_path: str, title: str) -> str:
    """Прямая публикация в TikTok (Direct Post, scope video.publish)."""
    size = os.path.getsize(file_path)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=180) as client:
        ci = await client.post(CREATOR_INFO_URL, headers=headers)
        options = (ci.json().get("data") or {}).get("privacy_level_options") or []
        privacy = (
            "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in options
            else (options[0] if options else "SELF_ONLY")
        )
        init_body = {
            "post_info": {
                "title": (title or "")[:150],
                "privacy_level": privacy,
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            },
        }
        init = await client.post(DIRECT_INIT_URL, json=init_body, headers=headers)
        data = init.json().get("data") or {}
        publish_id = data.get("publish_id")
        upload_url = data.get("upload_url")
        if not publish_id or not upload_url:
            raise ValueError(f"TikTok direct init error: {init.json()}")
        with open(file_path, "rb") as f:
            content = f.read()
        put = await client.put(
            upload_url,
            content=content,
            headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size - 1}/{size}"},
        )
        if put.status_code not in (200, 201):
            raise ValueError(f"TikTok direct upload failed: {put.status_code} {put.text}")
    return publish_id
