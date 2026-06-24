"""Резолв исходного YouTube-канала из ссылки/@handle/ID в (channel_id, title)."""
from __future__ import annotations

import re

import httpx

from bot.services.rss import fetch_feed

_CHANNEL_ID_RE = re.compile(r"(UC[\w-]{22})")
_CANONICAL_RE = re.compile(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"')
_META_CHANNEL_RE = re.compile(r'"(?:externalId|channelId)":"(UC[\w-]{22})"')

_UA = {"User-Agent": "Mozilla/5.0 (compatible; PostiqBot/1.0)"}


def _normalize_to_url(query: str) -> str | None:
    """Привести пользовательский ввод к URL страницы YouTube."""
    q = query.strip()
    if not q:
        return None
    if re.fullmatch(r"UC[\w-]{22}", q):
        return f"https://www.youtube.com/channel/{q}"
    if q.startswith("@"):
        return f"https://www.youtube.com/{q}"
    if q.startswith("http://") or q.startswith("https://"):
        return q
    if "youtube.com" in q or "youtu.be" in q:
        return "https://" + q
    return f"https://www.youtube.com/@{q}"


async def _extract_channel_id(url: str) -> str | None:
    m = re.search(r"/channel/(UC[\w-]{22})", url)
    if m:
        return m.group(1)
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=_UA) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        return None
    html = resp.text
    for pattern in (_CANONICAL_RE, _META_CHANNEL_RE, _CHANNEL_ID_RE):
        m = pattern.search(html)
        if m:
            return m.group(1)
    return None


async def resolve_source_channel(query: str) -> tuple[str, str] | None:
    """Вернуть (channel_id, channel_title) или None, если канал не найден."""
    url = _normalize_to_url(query)
    if url is None:
        return None
    channel_id = await _extract_channel_id(url)
    if channel_id is None:
        return None
    feed = await fetch_feed(channel_id)
    if feed is None:
        return None
    return channel_id, feed.channel_title
