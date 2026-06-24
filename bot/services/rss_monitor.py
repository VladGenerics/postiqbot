"""Мониторинг исходных каналов через RSS → создание job'ов на новые видео."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from bot.db.models import Connection, Job, SourceChannel
from bot.db.session import get_session
from bot.services.rss import Feed, FeedEntry, fetch_feed
from bot.services.tiktok_source import fetch_recent_tiktok

logger = logging.getLogger("postiqbot.monitor")


async def _fetch_for(source: SourceChannel) -> Feed | None:
    """Последние видео источника — по платформе (YouTube RSS / TikTok yt-dlp)."""
    if source.platform == "tiktok":
        return await fetch_recent_tiktok(source.channel_id)
    return await fetch_feed(source.channel_id)


def _new_entries(entries: list[FeedEntry], last_seen: str | None) -> list[FeedEntry]:
    """Видео новее last_seen, в хронологическом порядке (старые → новые)."""
    fresh: list[FeedEntry] = []
    for e in entries:
        if e.video_id == last_seen:
            break
        fresh.append(e)
    fresh.reverse()
    return fresh


async def _active_sources() -> list[SourceChannel]:
    async with get_session() as session:
        return list(
            await session.scalars(
                select(SourceChannel)
                .join(Connection, Connection.source_channel_id == SourceChannel.id)
                .where(Connection.is_active.is_(True))
                .distinct()
            )
        )


async def _connections_for_source(source_id: int) -> list[int]:
    async with get_session() as session:
        return list(
            await session.scalars(
                select(Connection.id).where(
                    Connection.source_channel_id == source_id,
                    Connection.is_active.is_(True),
                )
            )
        )


async def _create_jobs(connection_ids: list[int], entry: FeedEntry) -> None:
    now = datetime.now(timezone.utc)
    async with get_session() as session:
        for cid in connection_ids:
            stmt = (
                insert(Job)
                .values(
                    connection_id=cid,
                    source_video_id=entry.video_id,
                    video_url=entry.url,
                    title=entry.title,
                    status="pending",
                    scheduled_at=now,
                )
                .on_conflict_do_nothing(constraint="uq_job_source_video")
            )
            await session.execute(stmt)


async def _update_seen(source_id: int, last_seen: str) -> None:
    async with get_session() as session:
        src = await session.get(SourceChannel, source_id)
        if src:
            src.last_seen_video_id = last_seen
            src.last_checked_at = datetime.now(timezone.utc)


async def poll_sources() -> int:
    """Опросить все активные источники. Возвращает число созданных job'ов."""
    created = 0
    for source in await _active_sources():
        feed = await _fetch_for(source)
        if feed is None or not feed.entries:
            await _update_seen(source.id, source.last_seen_video_id or "")
            continue

        if source.last_seen_video_id is None:
            await _update_seen(source.id, feed.entries[0].video_id)
            logger.info("Источник %s засеян (%s)", source.channel_title, feed.entries[0].video_id)
            continue

        fresh = _new_entries(feed.entries, source.last_seen_video_id)
        if fresh:
            connection_ids = await _connections_for_source(source.id)
            for entry in fresh:
                await _create_jobs(connection_ids, entry)
                created += len(connection_ids)
            logger.info(
                "Источник %s: %d новых видео × %d связок",
                source.channel_title, len(fresh), len(connection_ids),
            )
        await _update_seen(source.id, feed.entries[0].video_id)
    return created
