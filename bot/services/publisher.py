"""Публикация скачанных видео: YouTube (Data API, с квотой проекта) и TikTok (Content Posting API, черновик)."""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from bot.db.models import (
    JOB_FAILED,
    JOB_PUBLISHED,
    JOB_PUBLISHING,
    JOB_SCHEDULED,
    Connection,
    Job,
    PublishAccount,
)
from bot.config import get_settings
from bot.db.session import get_session
from bot.services.crypto import decrypt
from bot.services import tiktok_api, tiktok_oauth
from bot.services.overlay import apply_overlay
from bot.services.subscription import inc_videos_used, video_limited_users
from bot.services.youtube_api import upload_video
from bot.services.youtube_oauth import credentials_from_refresh_token

logger = logging.getLogger("postiqbot.publisher")


@dataclass
class _Task:
    job_id: int
    user_id: int
    title: str
    local_path: str
    platform: str
    refresh_token: str
    privacy: str = "private"
    client_id: str = ""
    client_secret: str = ""
    overlay_file_id: str | None = None
    overlay_position: str | None = None
    overlay_scale: int = 30


def _start_of_day(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def _claim_due(limit: int) -> list[_Task]:
    """Захватить готовые к публикации job'ы."""
    now = datetime.now(timezone.utc)
    tasks: list[_Task] = []

    async with get_session() as session:
        used_rows = await session.execute(
            select(PublishAccount.project_id, func.count(Job.id))
            .join(Connection, Connection.id == Job.connection_id)
            .join(PublishAccount, PublishAccount.id == Connection.publish_account_id)
            .where(
                Job.status == JOB_PUBLISHED,
                Job.updated_at >= _start_of_day(now),
                PublishAccount.project_id.isnot(None),
            )
            .group_by(PublishAccount.project_id)
        )
        used: dict[int, int] = dict(used_rows.all())

        candidates = list(
            await session.scalars(
                select(Job)
                .where(Job.status == JOB_SCHEDULED, Job.scheduled_at <= now)
                .order_by(Job.scheduled_at)
                .options(
                    joinedload(Job.connection)
                    .joinedload(Connection.publish_account)
                    .joinedload(PublishAccount.project)
                )
                .limit(limit * 4)
                .with_for_update(skip_locked=True, of=Job)
            )
        )

        limited = await video_limited_users(
            [j.connection.user_id for j in candidates]
        )

        for job in candidates:
            if len(tasks) >= limit:
                break
            conn = job.connection
            if conn.user_id in limited:
                continue
            acc = conn.publish_account
            common = dict(
                job_id=job.id,
                user_id=conn.user_id,
                title=job.title or "video",
                local_path=job.local_path or "",
                refresh_token=decrypt(acc.refresh_token_enc),
                overlay_file_id=conn.overlay_file_id,
                overlay_position=conn.overlay_position,
                overlay_scale=conn.overlay_scale,
            )

            if acc.platform == "youtube":
                project = acc.project
                if project is None:
                    continue
                if used.get(project.id, 0) >= project.daily_quota:
                    continue
                used[project.id] = used.get(project.id, 0) + 1
                job.status = JOB_PUBLISHING
                tasks.append(
                    _Task(
                        platform="youtube",
                        privacy=conn.privacy,
                        client_id=project.client_id,
                        client_secret=decrypt(project.client_secret_enc),
                        **common,
                    )
                )
            elif acc.platform == "tiktok":
                job.status = JOB_PUBLISHING
                tasks.append(_Task(platform="tiktok", **common))
    return tasks


async def _finalize(job_id: int, *, remote_id: str | None, error: str | None) -> None:
    async with get_session() as session:
        job = await session.get(Job, job_id)
        if not job:
            return
        if error:
            job.status = JOB_FAILED
            job.error = error[:2000]
        else:
            job.status = JOB_PUBLISHED
            job.youtube_video_id = remote_id


def _yt_upload(task: _Task, path: str) -> str:
    creds = credentials_from_refresh_token(
        task.refresh_token, task.client_id, task.client_secret
    )
    return upload_video(
        creds, path, task.title, description="", privacy_status=task.privacy
    )


async def _publish(task: _Task, path: str) -> str:
    if task.platform == "youtube":
        return await asyncio.to_thread(_yt_upload, task, path)
    if task.platform == "tiktok":
        tokens = await tiktok_oauth.refresh_access_token(task.refresh_token)
        return await tiktok_api.upload_to_inbox(tokens["access_token"], path)
    raise ValueError(f"Неизвестная платформа: {task.platform}")


async def _download_overlay(bot: Bot, file_id: str) -> str:
    """Скачать оверлей из Telegram во временный файл (расширение из file_path)."""
    file = await bot.get_file(file_id)
    ext = os.path.splitext(file.file_path or "")[1] or ".bin"
    os.makedirs(get_settings().download_dir, exist_ok=True)
    dest = os.path.join(
        get_settings().download_dir, f"overlay_{file.file_unique_id}{ext}"
    )
    await bot.download_file(file.file_path, dest)
    return dest


async def _prepare_path(bot: Bot, task: _Task) -> tuple[str, list[str]]:
    """Вернуть (путь для публикации, список временных файлов на удаление)."""
    if not (task.overlay_file_id and task.overlay_position):
        return task.local_path, []
    overlay_tmp = await _download_overlay(bot, task.overlay_file_id)
    overlaid = await asyncio.to_thread(
        apply_overlay, task.local_path, overlay_tmp, task.overlay_position, task.overlay_scale
    )
    return overlaid, [overlay_tmp, overlaid]


def _success_msg(task: _Task, remote_id: str) -> str:
    if task.platform == "youtube":
        return (
            f"✅ Видео опубликовано: https://youtu.be/{remote_id}\n"
            f"<i>{task.title}</i> (доступ: {task.privacy})"
        )
    return (
        f"✅ Видео отправлено в черновики TikTok: <i>{task.title}</i>\n"
        "Открой приложение TikTok → Профиль → Черновики → опубликуй."
    )


async def process_scheduled(bot: Bot, limit: int = 3) -> int:
    """Опубликовать до `limit` видео. Возвращает число опубликованных."""
    published = 0
    for task in await _claim_due(limit):
        extra_files: list[str] = []
        try:
            publish_path, extra_files = await _prepare_path(bot, task)
            remote_id = await _publish(task, publish_path)
            await _finalize(task.job_id, remote_id=remote_id, error=None)
            await inc_videos_used(task.user_id)
            published += 1
            logger.info("Опубликовано job=%d (%s) → %s", task.job_id, task.platform, remote_id)
            await _notify(bot, task.user_id, _success_msg(task, remote_id))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка публикации job=%d", task.job_id)
            await _finalize(task.job_id, remote_id=None, error=str(exc))
            await _notify(bot, task.user_id, f"❌ Не удалось опубликовать «{task.title}»: {exc}")
        finally:
            _cleanup(task.local_path)
            for f in extra_files:
                _cleanup(f)
    return published


def _cleanup(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        logger.warning("Не смог удалить файл %s", path)


async def _notify(bot: Bot, user_id: int, text: str) -> None:
    try:
        await bot.send_message(user_id, text)
    except Exception:  # noqa: BLE001
        logger.warning("Не смог уведомить пользователя %s", user_id)
