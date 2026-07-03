"""Бэкфилл: залить в очередь архив источника (старые → новые) по расписанию связки."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import joinedload

from bot.config import get_settings
from bot.db.models import JOB_FAILED, JOB_PENDING, Connection, Job, User
from bot.db.session import get_session
from bot.services.archive import fetch_channel_archive
from bot.services.scheduling import compute_scheduled_at
from bot.services.tiktok_source import fetch_tiktok_archive

MAX_BACKFILL = 1000


async def backfill_cap(user_id: int | None) -> int:
    """Максимум видео за один бэкфилл."""
    s = get_settings()
    if user_id is None or user_id in s.admin_id_set:
        return MAX_BACKFILL
    async with get_session() as session:
        user = await session.get(User, user_id)
    return user.tier_videos if user and user.tier_videos else s.trial_videos


@dataclass
class BackfillResult:
    ok: bool
    error: str | None = None
    created: int = 0
    title: str = ""
    sched_mode: str = "immediate"
    first_at: datetime | None = None
    last_at: datetime | None = None


async def _last_scheduled(conn_id: int) -> datetime | None:
    async with get_session() as session:
        return await session.scalar(
            select(func.max(Job.scheduled_at)).where(
                Job.connection_id == conn_id, Job.status != JOB_FAILED
            )
        )


async def backfill_connection(conn_id: int, limit: int, user_id: int | None = None) -> BackfillResult:
    """Поставить в очередь до `limit` архивных видео источника связки."""
    limit = max(1, min(limit, await backfill_cap(user_id)))
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection)
            .where(Connection.id == conn_id)
            .options(joinedload(Connection.source_channel))
        )
        if conn is None or (user_id is not None and conn.user_id != user_id):
            return BackfillResult(ok=False, error="not_found")
        source = conn.source_channel
        sched_mode, interval, post_times, tz = (
            conn.schedule_mode, conn.interval_minutes, conn.post_times, conn.tz
        )
    if source is None:
        return BackfillResult(ok=False, error="no_source")

    if source.platform == "youtube":
        entries = await asyncio.to_thread(fetch_channel_archive, source.channel_id, limit)
    elif source.platform == "tiktok":
        entries = await fetch_tiktok_archive(source.channel_id, limit)
    else:
        return BackfillResult(ok=False, error="unsupported", title=source.channel_title)

    if not entries:
        return BackfillResult(ok=False, error="empty", title=source.channel_title)

    now = datetime.now(timezone.utc)
    running = await _last_scheduled(conn_id)
    created = 0
    first_at = last_at = None
    async with get_session() as session:
        for entry in entries:
            sched = compute_scheduled_at(
                mode=sched_mode, interval_minutes=interval,
                post_times=post_times, tz_name=tz, last_scheduled=running, now=now,
            )
            stmt = (
                insert(Job)
                .values(
                    connection_id=conn_id,
                    source_video_id=entry.video_id,
                    video_url=entry.url,
                    title=entry.title,
                    status=JOB_PENDING,
                    scheduled_at=sched,
                )
                .on_conflict_do_nothing(constraint="uq_job_source_video")
            )
            res = await session.execute(stmt)
            if res.rowcount:
                created += 1
                first_at = first_at or sched
                last_at = sched
            running = sched

    return BackfillResult(
        ok=True, created=created, title=source.channel_title,
        sched_mode=sched_mode, first_at=first_at, last_at=last_at,
    )
