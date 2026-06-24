"""Скачивание видео через yt-dlp + воркер обработки pending-job'ов."""
from __future__ import annotations

import glob
import logging
import os
from datetime import datetime, timezone

import yt_dlp
from sqlalchemy import select

from bot.config import get_settings
from bot.db.models import (
    JOB_DOWNLOADING,
    JOB_FAILED,
    JOB_PENDING,
    JOB_SCHEDULED,
    Job,
)
from bot.db.session import get_session

logger = logging.getLogger("postiqbot.downloader")


def _ydl_opts(dest_dir: str) -> dict:
    return {
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(dest_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "noprogress": True,
        "noplaylist": True,
        "retries": 3,
    }


def download(video_url: str, video_id: str) -> str:
    """Скачать видео, вернуть путь к файлу (синхронно)."""
    dest_dir = get_settings().download_dir
    os.makedirs(dest_dir, exist_ok=True)
    with yt_dlp.YoutubeDL(_ydl_opts(dest_dir)) as ydl:
        ydl.download([video_url])
    matches = glob.glob(os.path.join(dest_dir, f"{video_id}.*"))
    if not matches:
        raise FileNotFoundError(f"Файл для {video_id} не найден после скачивания")
    matches.sort(key=lambda p: (not p.endswith(".mp4"), -os.path.getsize(p)))
    return matches[0]


async def _claim_pending(limit: int) -> list[tuple[int, str, str]]:
    """Захватить pending-job'ы (перевести в downloading). Вернуть (id, url, video_id)."""
    claimed: list[tuple[int, str, str]] = []
    async with get_session() as session:
        jobs = list(
            await session.scalars(
                select(Job)
                .where(Job.status == JOB_PENDING)
                .order_by(Job.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        for job in jobs:
            job.status = JOB_DOWNLOADING
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


async def process_pending(limit: int = 3) -> int:
    """Скачать до `limit` ожидающих видео. Возвращает число успешно скачанных."""
    import asyncio

    ok = 0
    for job_id, url, video_id in await _claim_pending(limit):
        try:
            path = await asyncio.to_thread(download, url, video_id)
            await _finish(job_id, local_path=path, error=None)
            ok += 1
            logger.info("Скачано job=%d → %s", job_id, path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка скачивания job=%d", job_id)
            await _finish(job_id, local_path=None, error=str(exc))
    return ok
