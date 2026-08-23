"""Скачивание видео через yt-dlp + воркер обработки pending-job'ов."""
from __future__ import annotations

import glob
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import yt_dlp
from aiogram import Bot
from sqlalchemy import func, nulls_first, or_, select

from bot.config import get_settings
from bot.db.models import (
    JOB_AWAITING,
    JOB_DOWNLOADING,
    JOB_FAILED,
    JOB_PENDING,
    JOB_PUBLISHING,
    JOB_SCHEDULED,
    Connection,
    Job,
    PublishAccount,
    SourceChannel,
)
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services.tiktok_policy import POST_FIELDS, is_auto_post, needs_confirm_card
from bot.services.ytdlp_cookies import working_copy

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
        "socket_timeout": 30,
        "remote_components": ["ejs:github"],
    }
    cookies = working_copy(get_settings().ytdlp_cookies_file, dest_dir)
    if cookies:
        opts["cookiefile"] = cookies
    return opts


def _is_age_restricted(error: str) -> bool:
    e = error.lower()
    return "confirm your age" in e or "inappropriate for some users" in e


_TRANSIENT_ERRORS = (
    "unexpected response from webpage request",
    "unable to extract universal data",
    "unable to extract challenge data",
    "unable to solve js challenge",
    "unable to extract aweme detail",
)

_RETRY_DELAYS = (15, 45)

_REQUEUE_DELAYS_MINUTES = (30, 120, 360, 720, 1440, 1440)


def _is_transient(error: str) -> bool:
    e = error.lower()
    return any(m in e for m in _TRANSIENT_ERRORS)


def _requeue_delay(attempts: int) -> timedelta | None:
    """Пауза до следующей попытки скачивания. None — попытки кончились."""
    if attempts >= len(_REQUEUE_DELAYS_MINUTES):
        return None
    return timedelta(minutes=_REQUEUE_DELAYS_MINUTES[attempts])


def download(video_url: str, video_id: str, job_id: int, attempt: int = 0) -> str:
    """Скачать видео, вернуть путь к файлу (синхронно)."""
    dest_dir = get_settings().download_dir
    os.makedirs(dest_dir, exist_ok=True)
    stem = f"{video_id}_{job_id}_a{attempt}"
    opts = _ydl_opts(dest_dir)
    opts["outtmpl"] = os.path.join(dest_dir, f"{stem}.%(ext)s")
    attempts = len(_RETRY_DELAYS) + 1
    for attempt in range(attempts):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([video_url])
            break
        except Exception as exc:  # noqa: BLE001
            if attempt == attempts - 1 or not _is_transient(str(exc)):
                raise
            delay = _RETRY_DELAYS[attempt]
            logger.warning(
                "job=%d: плавающая ошибка скачивания (%s) — повтор через %d с",
                job_id,
                str(exc).splitlines()[0][:150],
                delay,
            )
            time.sleep(delay)
    matches = glob.glob(os.path.join(dest_dir, f"{stem}.*"))
    if not matches:
        raise FileNotFoundError(f"downloaded file for {stem} not found")
    matches.sort(key=lambda p: (not p.endswith(".mp4"), -os.path.getsize(p)))
    return matches[0]


_INFLIGHT_CAP = 4


async def _claim_pending(limit: int) -> list[tuple[int, str, str, int]]:
    """Захватить pending-job'ы (→ downloading)."""
    now = datetime.now(timezone.utc)
    claimed: list[tuple[int, str, str, int]] = []
    async with get_session() as session:
        inflight: dict[int, int] = dict(
            (
                await session.execute(
                    select(Job.connection_id, func.count(Job.id))
                    .where(
                        Job.status.in_((JOB_SCHEDULED, JOB_AWAITING)),
                        Job.local_path.isnot(None),
                    )
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
                .order_by(nulls_first(Job.scheduled_at), Job.created_at)
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
            claimed.append((job.id, job.video_url, job.source_video_id, job.download_attempts))
    return claimed


async def needs_confirmation(session, connection_id: int) -> bool:
    """Нужно ли для этой связки подтверждение пользователя перед публикацией."""
    card, _ = await tiktok_plan(session, connection_id)
    return card


_TT_FIELDS = POST_FIELDS


async def tiktok_plan(session, connection_id: int) -> tuple[bool, dict]:
    """Что делать с видео этой связки после скачивания."""
    if not get_settings().tiktok_direct_post:
        return False, {}
    row = (
        await session.execute(
            select(
                PublishAccount.platform,
                SourceChannel.platform,
                Connection.tt_auto,
                Connection.tt_privacy,
                Connection.tt_consent_at,
                Connection.tt_disable_comment,
                Connection.tt_disable_duet,
                Connection.tt_disable_stitch,
                Connection.tt_brand_organic,
                Connection.tt_brand_content,
            )
            .join(Connection, Connection.publish_account_id == PublishAccount.id)
            .join(SourceChannel, SourceChannel.id == Connection.source_channel_id)
            .where(Connection.id == connection_id)
        )
    ).first()
    if not row:
        return False, {}
    dest, source = row[0], row[1]
    consent = dict(
        tt_auto=row.tt_auto, tt_privacy=row.tt_privacy, tt_consent_at=row.tt_consent_at
    )
    if needs_confirm_card(dest, source, **consent):
        return True, {}
    if not is_auto_post(dest, source, **consent):
        return False, {}
    return False, {f: getattr(row, f) for f in _TT_FIELDS}


def _job_files(video_id: str, job_id: int) -> list[str]:
    """Все файлы на диске, относящиеся к попыткам скачивания этого джоба (итоговые и недокачанные .part."""
    dest_dir = get_settings().download_dir
    pattern = os.path.join(dest_dir, f"{video_id}_{job_id}_a*")
    return glob.glob(pattern + ".*") + glob.glob(pattern + "*.part")


async def _finish(job_id: int, *, local_path: str | None, error: str | None) -> str:
    """Записать результат скачивания."""
    async with get_session() as session:
        job = await session.get(Job, job_id)
        if not job:
            return "failed"
        if error:
            job.error = error[:2000]
            delay = _requeue_delay(job.download_attempts)
            if delay is not None and _is_transient(error):
                job.download_attempts += 1
                job.status = JOB_PENDING
                job.local_path = None
                job.scheduled_at = datetime.now(timezone.utc) + delay
                return "requeued"
            stale = set(_job_files(job.source_video_id, job.id))
            if local_path:
                stale.add(local_path)
            for path in stale:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    logger.warning("Не смог удалить файл %s джоба %d", path, job_id)
            job.local_path = None
            job.status = JOB_FAILED
            return "failed"
        job.local_path = local_path
        if job.scheduled_at is None:
            job.scheduled_at = datetime.now(timezone.utc)
        card, tt_fields = await tiktok_plan(session, job.connection_id)
        if card:
            job.status = JOB_AWAITING
            job.awaiting_since = datetime.now(timezone.utc)
            return "awaiting"
        for field, value in tt_fields.items():
            setattr(job, field, value)
        job.status = JOB_SCHEDULED
        return "scheduled"


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
    for job_id, url, video_id, attempts in await _claim_pending(limit):
        try:
            path = await asyncio.to_thread(download, url, video_id, job_id, attempts)
        except Exception as exc:  # noqa: BLE001
            result = await _finish(job_id, local_path=None, error=str(exc))
            if result == "requeued":
                logger.warning(
                    "job=%d: скачивание не удалось (%s) — вернул в очередь",
                    job_id, str(exc).splitlines()[0][:150],
                )
            else:
                logger.exception("Ошибка скачивания job=%d", job_id)
                if bot is not None:
                    await _notify_fail(bot, job_id, str(exc))
            continue
        result = await _finish(job_id, local_path=path, error=None)
        ok += 1
        logger.info("Скачано job=%d → %s", job_id, path)
        if result == "awaiting" and bot is not None:
            from bot.handlers.tiktok_confirm import send_confirm_card

            try:
                await send_confirm_card(bot, job_id)
            except Exception:  # noqa: BLE001
                logger.exception("Не смог отправить карточку подтверждения job=%d", job_id)
    return ok


_ORPHAN_GRACE_HOURS = 2

_LIVE_STATUSES = (JOB_PENDING, JOB_DOWNLOADING, JOB_AWAITING, JOB_SCHEDULED, JOB_PUBLISHING)


async def cleanup_downloads(max_age_hours: int = 48) -> int:
    """Свип каталога скачиваний."""
    dest_dir = os.path.abspath(get_settings().download_dir)
    if not os.path.isdir(dest_dir):
        return 0
    now = time.time()
    max_age_sec = max(1, max_age_hours) * 3600
    grace_sec = _ORPHAN_GRACE_HOURS * 3600

    live_paths: set[str] = set()
    live_stems: set[str] = set()
    async with get_session() as session:
        rows = await session.scalars(
            select(Job.local_path).where(
                Job.status.in_(_LIVE_STATUSES), Job.local_path.isnot(None)
            )
        )
        for p in rows:
            ap = os.path.abspath(p)
            live_paths.add(ap)
            live_stems.add(os.path.splitext(ap)[0])

    removed = 0
    with os.scandir(dest_dir) as it:
        for entry in it:
            try:
                if not entry.is_file(follow_symlinks=False):
                    continue
                path = os.path.abspath(entry.path)
                age = now - entry.stat().st_mtime
                owned = (
                    path in live_paths or os.path.splitext(path)[0] in live_stems
                )
                if age <= (max_age_sec if owned else grace_sec):
                    continue
                os.remove(path)
                removed += 1
            except OSError as exc:
                logger.warning("cleanup_downloads: пропускаю %s (%s)", entry.path, exc)
    if removed:
        logger.info("cleanup_downloads: удалено файлов %d", removed)
    return removed
