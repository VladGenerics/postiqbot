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


def _archive_urls(channel_id: str) -> list[str]:
    """URL'ы для перебора."""
    urls: list[str] = []
    if channel_id.startswith("UC"):
        urls.append(f"https://www.youtube.com/playlist?list=UU{channel_id[2:]}")
    urls += [
        f"https://www.youtube.com/channel/{channel_id}/videos",
        f"https://www.youtube.com/channel/{channel_id}/shorts",
    ]
    return urls


def _entries_from(info: dict | None) -> list[FeedEntry]:
    items: list[FeedEntry] = []
    for e in (info or {}).get("entries") or []:
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
    return items


def fetch_channel_archive(channel_id: str, limit: int) -> list[FeedEntry]:
    """Все ролики YouTube-канала (включая Shorts) в порядке СТАРЫЕ → НОВЫЕ, не более `limit`."""
    for url in _archive_urls(channel_id):
        try:
            with yt_dlp.YoutubeDL(_flat_opts()) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("archive: %s — %s", url, exc)
            continue
        items = _entries_from(info)
        if items:
            items.reverse()
            logger.info("archive: %d роликов из %s", len(items), url)
            return items[:limit]
    return []
