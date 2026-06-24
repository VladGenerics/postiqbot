"""Резолв исходного YouTube-канала из ссылки/@handle/ID в (channel_id, title)."""
from __future__ import annotations

import asyncio
import re

import yt_dlp

from bot.services.rss import fetch_feed

_TAB_SUFFIX_RE = re.compile(
    r"/(shorts|videos|streams|featured|community|playlists|about|podcasts|releases)/?$",
    re.IGNORECASE,
)


def _normalize_to_url(query: str) -> str | None:
    """Привести пользовательский ввод к URL страницы YouTube."""
    q = query.strip()
    if not q:
        return None
    q = _TAB_SUFFIX_RE.sub("", q)
    if re.fullmatch(r"UC[\w-]{22}", q):
        return f"https://www.youtube.com/channel/{q}"
    if q.startswith("@"):
        return f"https://www.youtube.com/{q}"
    if q.startswith("http://") or q.startswith("https://"):
        return q
    if "youtube.com" in q or "youtu.be" in q:
        return "https://" + q
    return f"https://www.youtube.com/@{q}"


def _extract_channel_id_sync(url: str) -> str | None:
    """Достать channel_id (UC...) через yt-dlp. Синхронно → звать в to_thread."""
    m = re.search(r"/channel/(UC[\w-]{22})", url)
    if m:
        return m.group(1)
    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "playlist_items": "1",
        "noprogress": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return None
    channel_id = info.get("channel_id")
    if channel_id and channel_id.startswith("UC"):
        return channel_id
    return None


async def resolve_source_channel(query: str) -> tuple[str, str] | None:
    """Вернуть (channel_id, channel_title) или None, если канал не найден."""
    url = _normalize_to_url(query)
    if url is None:
        return None
    channel_id = await asyncio.to_thread(_extract_channel_id_sync, url)
    if channel_id is None:
        return None
    feed = await fetch_feed(channel_id)
    if feed is None:
        return None
    return channel_id, feed.channel_title
