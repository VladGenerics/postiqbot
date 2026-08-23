"""Резолв исходного YouTube-канала из ссылки/@handle/ID в (channel_id, title)."""
from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlparse

import yt_dlp

from bot.services.rss import fetch_feed

logger = logging.getLogger("postiqbot.source_resolver")

_YT_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
_TT_HOSTS = {
    "tiktok.com",
    "www.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
}

_TAB_SUFFIX_RE = re.compile(
    r"/(shorts|videos|streams|featured|community|playlists|about|podcasts|releases)/?$",
    re.IGNORECASE,
)


def _url_host(query: str) -> str | None:
    """Hostname строки, ЕСЛИ это ссылка; None — если на ссылку не похоже."""
    q = query.strip()
    if not q or " " in q:
        return None
    has_scheme = q.lower().startswith(("http://", "https://"))
    if not has_scheme and "/" not in q:
        return None
    if not has_scheme:
        q = "https://" + q
    return (urlparse(q).hostname or "").lower() or None


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
    if _url_host(q) is None:
        return f"https://www.youtube.com/@{q}"
    host = _url_host(q)
    if host not in _YT_HOSTS:
        logger.warning("SSRF-allowlist: hostname %r запрещён для YouTube", host)
        return None
    return q if q.lower().startswith(("http://", "https://")) else "https://" + q


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


def detect_platform(query: str) -> str:
    """Определить платформу источника по hostname ссылки. Без ссылки — youtube."""
    host = _url_host(query)
    if host is not None and host in _TT_HOSTS:
        return "tiktok"
    return "youtube"


async def resolve_source_channel(query: str) -> tuple[str, str, str] | None:
    """Вернуть (platform, channel_id, channel_title) или None, если не найдено."""
    platform = detect_platform(query)
    if platform == "tiktok":
        host = _url_host(query)
        if host is not None and host not in _TT_HOSTS:
            logger.warning("SSRF-allowlist: hostname %r запрещён для TikTok", host)
            return None
        from bot.services.tiktok_source import resolve_tiktok

        return await resolve_tiktok(query)

    url = _normalize_to_url(query)
    if url is None:
        return None
    channel_id = await asyncio.to_thread(_extract_channel_id_sync, url)
    if channel_id is None:
        return None
    feed = await fetch_feed(channel_id)
    if feed is None:
        return None
    return ("youtube", channel_id, feed.channel_title)
