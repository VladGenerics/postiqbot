"""Мониторинг исходных каналов через RSS → создание job'ов на новые видео."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from bot.db.models import JOB_FAILED, Connection, Job, SourceChannel
from bot.db.session import get_session
from bot.services.rss import Feed, FeedEntry, fetch_feed
from bot.services.scheduling import compute_scheduled_at
from bot.services.subscription import active_user_ids
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


async def _active_connections_for_source(source_id: int) -> list[Connection]:
    async with get_session() as session:
        return list(
            await session.scalars(
                select(Connection).where(
                    Connection.source_channel_id == source_id,
                    Connection.is_active.is_(True),
                )
            )
        )


async def _last_scheduled(connection_id: int) -> datetime | None:
    async with get_session() as session:
        return await session.scalar(
            select(func.max(Job.scheduled_at)).where(
                Job.connection_id == connection_id, Job.status != JOB_FAILED
            )
        )


async def _create_jobs_for_videos(
    connections: list[Connection], videos: list[FeedEntry]
) -> int:
    """Создать job'ы на новые видео для всех связок."""
    now = datetime.now(timezone.utc)
    running: dict[int, datetime | None] = {
        c.id: await _last_scheduled(c.id) for c in connections
    }
    created = 0
    async with get_session() as session:
        for entry in videos:
            for c in connections:
                sched = compute_scheduled_at(
                    mode=c.schedule_mode,
                    interval_minutes=c.interval_minutes,
                    post_times=c.post_times,
                    tz_name=c.tz,
                    last_scheduled=running[c.id],
                    now=now,
                )
                stmt = (
                    insert(Job)
                    .values(
                        connection_id=c.id,
                        source_video_id=entry.video_id,
                        video_url=entry.url,
                        title=entry.title,
                        status="pending",
                        scheduled_at=sched,
                    )
                    .on_conflict_do_nothing(constraint="uq_job_source_video")
                )
                await session.execute(stmt)
                running[c.id] = sched
                created += 1
    return created


async def _update_seen(source_id: int, last_seen: str) -> None:
    async with get_session() as session:
        src = await session.get(SourceChannel, source_id)
        if src:
            src.last_seen_video_id = last_seen
            src.last_checked_at = datetime.now(timezone.utc)


async def _touch_checked(source_id: int) -> None:
    """Отметить время проверки, НЕ трогая last_seen."""
    async with get_session() as session:
        src = await session.get(SourceChannel, source_id)
        if src:
            src.last_checked_at = datetime.now(timezone.utc)


async def poll_sources() -> int:
    """Опросить все активные источники. Возвращает число созданных job'ов."""
    created = 0
    for source in await _active_sources():
        try:
            created += await _poll_one(source)
        except Exception:  # noqa: BLE001
            logger.exception("Опрос источника %s упал", source.channel_title)
    return created


async def _poll_one(source: SourceChannel) -> int:
    """Опросить один источник, создать job'ы на новые видео. Число созданных."""
    feed = await _fetch_for(source)
    if feed is None or not feed.entries:
        await _touch_checked(source.id)
        return 0

    if source.last_seen_video_id is None:
        await _update_seen(source.id, feed.entries[0].video_id)
        logger.info("Источник %s засеян (%s)", source.channel_title, feed.entries[0].video_id)
        return 0

    fresh = _new_entries(feed.entries, source.last_seen_video_id)
    created = 0
    if fresh:
        conns = await _active_connections_for_source(source.id)
        allowed = await active_user_ids([c.user_id for c in conns])
        conns = [c for c in conns if c.user_id in allowed]
        created = await _create_jobs_for_videos(conns, fresh)
        logger.info(
            "Источник %s: %d новых видео × %d связок",
            source.channel_title, len(fresh), len(conns),
        )
    await _update_seen(source.id, feed.entries[0].video_id)
    return created
