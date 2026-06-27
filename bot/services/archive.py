"""Полный архив канала-источника через yt-dlp (flat-листинг)."""
from __future__ import annotations

import logging

import yt_dlp

from bot.services.rss import FeedEntry

logger = logging.getLogger("postiqbot.archive")


def _flat_opts() -> dict:
    return {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }


def fetch_channel_archive(channel_id: str, limit: int) -> list[FeedEntry]:
    """Все видео YouTube-канала в порядке СТАРЫЕ → НОВЫЕ, не более `limit`."""
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    with yt_dlp.YoutubeDL(_flat_opts()) as ydl:
        info = ydl.extract_info(url, download=False)

    raw = (info or {}).get("entries") or []
    items: list[FeedEntry] = []
    for e in raw:
        if not e:
            continue
        vid = e.get("id")
        if not vid:
            continue
        items.append(
            FeedEntry(
                video_id=vid,
                title=e.get("title") or "video",
                url=e.get("url") or f"https://youtu.be/{vid}",
            )
        )

    items.reverse()
    return items[:limit]
