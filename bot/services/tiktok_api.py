"""TikTok Content Posting API — загрузка видео в «инбокс» (черновики)."""
from __future__ import annotations

import os

import httpx

INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"


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
