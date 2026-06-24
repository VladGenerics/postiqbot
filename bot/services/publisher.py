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
from bot.db.session import get_session
from bot.services.crypto import decrypt
from bot.services import tiktok_api, tiktok_oauth
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

        for job in candidates:
            if len(tasks) >= limit:
                break
            conn = job.connection
            acc = conn.publish_account
            common = dict(
                job_id=job.id,
                user_id=conn.user_id,
                title=job.title or "video",
                local_path=job.local_path or "",
                refresh_token=decrypt(acc.refresh_token_enc),
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


def _yt_upload(task: _Task) -> str:
    creds = credentials_from_refresh_token(
        task.refresh_token, task.client_id, task.client_secret
    )
    return upload_video(
        creds, task.local_path, task.title, description="", privacy_status=task.privacy
    )


async def _publish(task: _Task) -> str:
    if task.platform == "youtube":
        return await asyncio.to_thread(_yt_upload, task)
    if task.platform == "tiktok":
        tokens = await tiktok_oauth.refresh_access_token(task.refresh_token)
        return await tiktok_api.upload_to_inbox(tokens["access_token"], task.local_path)
    raise ValueError(f"Неизвестная платформа: {task.platform}")


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
        try:
            remote_id = await _publish(task)
            await _finalize(task.job_id, remote_id=remote_id, error=None)
            published += 1
            logger.info("Опубликовано job=%d (%s) → %s", task.job_id, task.platform, remote_id)
            await _notify(bot, task.user_id, _success_msg(task, remote_id))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка публикации job=%d", task.job_id)
            await _finalize(task.job_id, remote_id=None, error=str(exc))
            await _notify(bot, task.user_id, f"❌ Не удалось опубликовать «{task.title}»: {exc}")
        finally:
            _cleanup(task.local_path)
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
