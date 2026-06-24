"""Чтение RSS-фида YouTube-канала."""
from __future__ import annotations

from dataclasses import dataclass

import feedparser
import httpx

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


@dataclass
class FeedEntry:
    video_id: str
    title: str
    url: str


@dataclass
class Feed:
    channel_title: str
    entries: list[FeedEntry]


def feed_url(channel_id: str) -> str:
    return RSS_URL.format(channel_id=channel_id)


async def fetch_feed(channel_id: str) -> Feed | None:
    """Скачать и распарсить RSS канала. None — если канал не найден/пустой фид."""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(feed_url(channel_id))
    if resp.status_code != 200:
        return None
    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries and not parsed.feed.get("title"):
        return None
    title = parsed.feed.get("title", channel_id)
    entries = [
        FeedEntry(
            video_id=e.get("yt_videoid", ""),
            title=e.get("title", ""),
            url=e.get("link", ""),
        )
        for e in parsed.entries
        if e.get("yt_videoid")
    ]
    return Feed(channel_title=title, entries=entries)
