"""Скачивание видео через yt-dlp + воркер обработки pending-job'ов."""
from __future__ import annotations

import glob
import logging
import os
from datetime import datetime, timezone

import yt_dlp
from aiogram import Bot
from sqlalchemy import func, or_, select

from bot.config import get_settings
from bot.db.models import (
    JOB_DOWNLOADING,
    JOB_FAILED,
    JOB_PENDING,
    JOB_SCHEDULED,
    Connection,
    Job,
)
from bot.db.session import get_session
from bot.i18n import t, user_lang

logger = logging.getLogger("postiqbot.downloader")


_FORMAT = (
    "bv*[vcodec^=avc1][height<=1920][width<=1920]+ba[acodec^=mp4a]/"
    "bv*[ext=mp4][height<=1920][width<=1920]+ba[ext=m4a]/"
    "b[ext=mp4][height<=1920][width<=1920]/"
    "b[height<=1920][width<=1920]/b"
)


def _ydl_opts(dest_dir: str) -> dict:
    opts = {
        "format": _FORMAT,
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(dest_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "noprogress": True,
        "noplaylist": True,
        "retries": 3,
    }
    cookies = get_settings().ytdlp_cookies_file
    if cookies and os.path.exists(cookies):
        opts["cookiefile"] = cookies
    return opts


def _is_age_restricted(error: str) -> bool:
    e = error.lower()
    return "confirm your age" in e or "inappropriate for some users" in e


def download(video_url: str, video_id: str, job_id: int) -> str:
    """Скачать видео, вернуть путь к файлу (синхронно)."""
    dest_dir = get_settings().download_dir
    os.makedirs(dest_dir, exist_ok=True)
    stem = f"{video_id}_{job_id}"
    opts = _ydl_opts(dest_dir)
    opts["outtmpl"] = os.path.join(dest_dir, f"{stem}.%(ext)s")
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([video_url])
    matches = glob.glob(os.path.join(dest_dir, f"{stem}.*"))
    if not matches:
        raise FileNotFoundError(f"Файл для {stem} не найден после скачивания")
    matches.sort(key=lambda p: (not p.endswith(".mp4"), -os.path.getsize(p)))
    return matches[0]


_INFLIGHT_CAP = 4


async def _claim_pending(limit: int) -> list[tuple[int, str, str]]:
    """Захватить pending-job'ы (→ downloading)."""
    now = datetime.now(timezone.utc)
    claimed: list[tuple[int, str, str]] = []
    async with get_session() as session:
        inflight: dict[int, int] = dict(
            (
                await session.execute(
                    select(Job.connection_id, func.count(Job.id))
                    .where(Job.status == JOB_SCHEDULED, Job.local_path.isnot(None))
                    .group_by(Job.connection_id)
                )
            ).all()
        )
        jobs = list(
            await session.scalars(
                select(Job)
                .where(
                    Job.status == JOB_PENDING,
                    or_(Job.scheduled_at.is_(None), Job.scheduled_at <= now),
                )
                .order_by(Job.scheduled_at, Job.created_at)
                .limit(limit * 4)
                .with_for_update(skip_locked=True)
            )
        )
        for job in jobs:
            if len(claimed) >= limit:
                break
            if inflight.get(job.connection_id, 0) >= _INFLIGHT_CAP:
                continue
            job.status = JOB_DOWNLOADING
            inflight[job.connection_id] = inflight.get(job.connection_id, 0) + 1
            claimed.append((job.id, job.video_url, job.source_video_id))
    return claimed


async def _finish(job_id: int, *, local_path: str | None, error: str | None) -> None:
    async with get_session() as session:
        job = await session.get(Job, job_id)
        if not job:
            return
        if error:
            job.status = JOB_FAILED
            job.error = error[:2000]
        else:
            job.status = JOB_SCHEDULED
            job.local_path = local_path
            if job.scheduled_at is None:
                job.scheduled_at = datetime.now(timezone.utc)


async def _notify_fail(bot: Bot, job_id: int, error: str) -> None:
    """Сообщить пользователю, почему видео не скачалось (иначе — тишина)."""
    async with get_session() as session:
        row = (
            await session.execute(
                select(Job.title, Connection.user_id)
                .join(Connection, Connection.id == Job.connection_id)
                .where(Job.id == job_id)
            )
        ).first()
    if not row:
        return
    title, user_id = row
    title = title or "video"
    lang = await user_lang(user_id)
    if _is_age_restricted(error):
        text = t("download_failed_age", lang, title=title)
    else:
        reason = error.strip().splitlines()[0][:200] if error else ""
        text = t("download_failed", lang, title=title, reason=reason)
    try:
        await bot.send_message(user_id, text)
    except Exception:  # noqa: BLE001
        logger.warning("Не смог уведомить пользователя %s об ошибке скачивания", user_id)


async def process_pending(bot: Bot | None = None, limit: int = 3) -> int:
    """Скачать до `limit` ожидающих видео. Возвращает число успешно скачанных."""
    import asyncio

    ok = 0
    for job_id, url, video_id in await _claim_pending(limit):
        try:
            path = await asyncio.to_thread(download, url, video_id, job_id)
            await _finish(job_id, local_path=path, error=None)
            ok += 1
            logger.info("Скачано job=%d → %s", job_id, path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка скачивания job=%d", job_id)
            await _finish(job_id, local_path=None, error=str(exc))
            if bot is not None:
                await _notify_fail(bot, job_id, str(exc))
    return ok
