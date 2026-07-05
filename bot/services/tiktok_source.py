"""TikTok как ИСТОЧНИК: резолв профиля и список последних видео через yt-dlp."""
from __future__ import annotations

import asyncio
import re

import yt_dlp

from bot.config import get_settings
from bot.services.rss import Feed, FeedEntry


def _ydl_opts() -> dict:
    opts: dict = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "noprogress": True,
        "playlist_items": "1:15",
    }
    cookies = get_settings().tiktok_cookies_file
    if cookies:
        opts["cookiefile"] = cookies
    return opts


def _norm_username(query: str) -> str:
    q = query.strip()
    m = re.search(r"tiktok\.com/@([\w.\-]+)", q, re.IGNORECASE)
    if m:
        return m.group(1)
    if q.startswith("@"):
        return q[1:]
    return q


def _profile_url(username: str) -> str:
    return f"https://www.tiktok.com/@{username}"


def _extract_sync(username: str) -> Feed:
    with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
        info = ydl.extract_info(_profile_url(username), download=False)
    title = info.get("uploader") or info.get("channel") or username
    entries: list[FeedEntry] = []
    for e in info.get("entries") or []:
        vid = e.get("id")
        if not vid:
            continue
        url = e.get("url") or f"{_profile_url(username)}/video/{vid}"
        text = e.get("title") or e.get("description") or ""
        entries.append(FeedEntry(video_id=str(vid), title=text[:200], url=url))
    return Feed(channel_title=title, entries=entries)


def _resolve_username_sync(query: str) -> str | None:
    """Достать @username из любой TikTok-ссылки: прямой профиль, @handle."""
    q = query.strip()
    m = re.search(r"tiktok\.com/@([\w.\-]+)", q, re.IGNORECASE)
    if m:
        return m.group(1)
    if q.startswith("@"):
        return q[1:]
    if "tiktok.com" not in q.lower():
        return q or None
    opts = {"quiet": True, "skip_download": True, "noprogress": True, "playlist_items": "1"}
    cookies = get_settings().tiktok_cookies_file
    if cookies:
        opts["cookiefile"] = cookies
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(q, download=False)
    if info.get("_type") == "playlist" and info.get("entries"):
        info = info["entries"][0] or info
    url = info.get("uploader_url") or info.get("channel_url") or ""
    m = re.search(r"@([\w.\-]+)", url)
    return m.group(1) if m else (info.get("uploader") or None)


async def resolve_tiktok(query: str) -> tuple[str, str, str] | None:
    """Вернуть (platform, channel_id=username, title) или None."""
    try:
        username = await asyncio.to_thread(_resolve_username_sync, query)
    except Exception:
        return None
    if not username:
        return None
    try:
        feed = await asyncio.to_thread(_extract_sync, username)
    except Exception:
        return None
    return ("tiktok", username, feed.channel_title)


async def fetch_recent_tiktok(username: str) -> Feed | None:
    """Последние видео TikTok-профиля (новые → старые), как у YouTube RSS."""
    try:
        return await asyncio.to_thread(_extract_sync, username)
    except Exception:
        return None


def _archive_sync(username: str, limit: int) -> list[FeedEntry]:
    opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "noprogress": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "playlist_items": f"1:{limit}",
    }
    cookies = get_settings().tiktok_cookies_file
    if cookies:
        opts["cookiefile"] = cookies
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(_profile_url(username), download=False)
    entries: list[FeedEntry] = []
    for e in (info or {}).get("entries") or []:
        if not e:
            continue
        vid = e.get("id")
        if not vid:
            continue
        url = e.get("url") or f"{_profile_url(username)}/video/{vid}"
        text = e.get("title") or e.get("description") or "video"
        entries.append(FeedEntry(video_id=str(vid), title=text[:200], url=url))
    entries.reverse()
    return entries[:limit]


async def fetch_tiktok_archive(username: str, limit: int) -> list[FeedEntry]:
    """Архив TikTok-профиля в порядке СТАРЫЕ → НОВЫЕ, не более `limit`."""
    try:
        return await asyncio.to_thread(_archive_sync, username, limit)
    except Exception:
        return []
