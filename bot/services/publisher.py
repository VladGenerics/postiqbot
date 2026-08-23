"""Публикация скачанных видео: YouTube (Data API, с квотой проекта) и TikTok (Content Posting API, черновик)."""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from cryptography.fernet import InvalidToken
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from bot.db.models import (
    JOB_AWAITING,
    JOB_DOWNLOADING,
    JOB_FAILED,
    JOB_PENDING,
    JOB_PUBLISHED,
    JOB_PUBLISHING,
    JOB_SCHEDULED,
    Connection,
    Job,
    PublishAccount,
    User,
)
from bot.config import UNLIMITED, get_settings
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services.crypto import decrypt
from bot.services import tiktok_api, tiktok_tokens
from bot.services.overlay import apply_overlay, video_duration
from bot.services.subscription import inc_videos_used
from bot.services.tiktok_policy import POST_FIELDS, effective_toggles, is_direct_post
from bot.services.youtube_api import (
    UploadSessionExpired,
    create_upload_session,
    resume_upload,
)
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
    description: str = ""
    client_id: str = ""
    client_secret: str = ""
    overlay_file_id: str | None = None
    overlay_position: str | None = None
    overlay_scale: int = 30
    account_id: int = 0
    connection_id: int = 0
    source_platform: str = ""
    tt_privacy: str | None = None
    tt_disable_comment: bool = True
    tt_disable_duet: bool = True
    tt_disable_stitch: bool = True
    tt_brand_organic: bool = False
    tt_brand_content: bool = False
    publish_attempts: int = 0
    fell_back_to_draft: bool = False
    tt_publish_id: str | None = None
    yt_resumable_uri: str | None = None

    @property
    def tt_direct(self) -> bool:
        """Публиковать напрямую (а не в черновики). См. tiktok_policy."""
        return is_direct_post(self.platform, self.source_platform)


def _start_of_day(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _tt_settings(job: Job, conn: Connection) -> dict:
    """Настройки TikTok-поста для этого джоба."""
    source = job if job.tt_privacy else conn
    return {f: getattr(source, f) for f in POST_FIELDS}


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

        conn_used_rows = await session.execute(
            select(Job.connection_id, func.count(Job.id))
            .where(
                Job.status == JOB_PUBLISHED,
                Job.updated_at >= _start_of_day(now),
            )
            .group_by(Job.connection_id)
        )
        conn_used: dict[int, int] = dict(conn_used_rows.all())

        last_pub_rows = await session.execute(
            select(Job.connection_id, func.max(Job.updated_at))
            .where(Job.status == JOB_PUBLISHED)
            .group_by(Job.connection_id)
        )
        last_pub: dict[int, datetime] = dict(last_pub_rows.all())

        candidates = list(
            await session.scalars(
                select(Job)
                .where(Job.status == JOB_SCHEDULED, Job.scheduled_at <= now)
                .order_by(Job.scheduled_at)
                .options(
                    joinedload(Job.connection)
                    .joinedload(Connection.publish_account)
                    .joinedload(PublishAccount.project),
                    joinedload(Job.connection).joinedload(Connection.source_channel),
                )
                .limit(limit * 8)
                .with_for_update(skip_locked=True, of=Job)
            )
        )

        user_ids = [j.connection.user_id for j in candidates]
        admins = get_settings().admin_id_set
        users = {
            u.telegram_id: u
            for u in await session.scalars(
                select(User).where(User.telegram_id.in_(user_ids))
            )
        }
        conn_limit = {
            j.connection.id: (
                UNLIMITED if j.connection.user_id in admins
                else (users[j.connection.user_id].tier_videos
                      if j.connection.user_id in users else get_settings().trial_videos)
            )
            for j in candidates
        }
        prio = {
            j.connection.user_id: (
                99 if j.connection.user_id in admins
                else (users[j.connection.user_id].tier_priority
                      if j.connection.user_id in users else 0)
            )
            for j in candidates
        }
        candidates.sort(key=lambda j: (-prio.get(j.connection.user_id, 0), j.scheduled_at))

        for job in candidates:
            if len(tasks) >= limit:
                break
            conn = job.connection
            uid = conn.user_id
            acc = conn.publish_account
            day_limit = conn_limit.get(conn.id, get_settings().trial_videos)
            if conn_used.get(conn.id, 0) >= day_limit:
                continue
            if (
                conn.schedule_mode == "immediate"
                and day_limit < UNLIMITED
                and conn.id in last_pub
            ):
                gap = timedelta(hours=24 / day_limit)
                last = last_pub[conn.id]
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                if now - last < gap:
                    continue
            try:
                refresh_token = decrypt(acc.refresh_token_enc)
            except InvalidToken:
                logger.exception(
                    "Не смог расшифровать refresh_token аккаунта %d (связка %d) "
                    "— пропускаю, джоб помечен ошибкой", acc.id, conn.id,
                )
                job.error = "decrypt failed: refresh_token аккаунта не читается"
                continue
            except Exception:  # noqa: BLE001 — любая другая ошибка тоже не стоп-кран
                logger.exception(
                    "Ошибка расшифровки токена аккаунта %d (связка %d)", acc.id, conn.id,
                )
                job.error = "decrypt failed: неизвестная ошибка расшифровки"
                continue

            common = dict(
                job_id=job.id,
                user_id=conn.user_id,
                title=job.title or "video",
                local_path=job.local_path or "",
                refresh_token=refresh_token,
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
                try:
                    client_secret = decrypt(project.client_secret_enc)
                except InvalidToken:
                    logger.exception(
                        "Не смог расшифровать client_secret проекта %d — "
                        "пропускаю, джоб помечен ошибкой", project.id,
                    )
                    job.error = "decrypt failed: client_secret проекта не читается"
                    continue
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Ошибка расшифровки client_secret проекта %d", project.id,
                    )
                    job.error = "decrypt failed: неизвестная ошибка расшифровки"
                    continue
                used[project.id] = used.get(project.id, 0) + 1
                job.status = JOB_PUBLISHING
                tasks.append(
                    _Task(
                        platform="youtube",
                        privacy=conn.privacy,
                        client_id=project.client_id,
                        client_secret=client_secret,
                        yt_resumable_uri=job.yt_resumable_uri,
                        **common,
                    )
                )
            elif acc.platform == "tiktok":
                job.status = JOB_PUBLISHING
                tasks.append(_Task(
                    platform="tiktok",
                    account_id=acc.id,
                    connection_id=conn.id,
                    source_platform=conn.source_channel.platform,
                    publish_attempts=job.publish_attempts,
                    tt_publish_id=job.tt_publish_id,
                    **_tt_settings(job, conn),
                    **common,
                ))
            else:
                continue
            conn_used[conn.id] = conn_used.get(conn.id, 0) + 1
            last_pub[conn.id] = now
    return tasks


async def _save_tt_publish_id(job_id: int, publish_id: str) -> None:
    """Сохранить publish_id в джоб СРАЗУ после init-запроса, до заливки байтов."""
    async with get_session() as session:
        job = await session.get(Job, job_id)
        if job:
            job.tt_publish_id = publish_id


async def _save_yt_resumable_uri(job_id: int, uri: str) -> None:
    """Сохранить URI resumable-сессии YouTube ДО заливки байтов."""
    async with get_session() as session:
        job = await session.get(Job, job_id)
        if job:
            job.yt_resumable_uri = uri


async def _finalize(
    job_id: int, *, remote_id: str | None, error: str | None, platform: str = ""
) -> None:
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
            if platform == "tiktok":
                job.tt_publish_id = remote_id


async def _requeue(job_id: int) -> None:
    """Вернуть джоб на скачивание (файл пропал — напр."""
    async with get_session() as session:
        job = await session.get(Job, job_id)
        if job:
            job.status = JOB_PENDING
            job.local_path = None


_RATE_LIMITED = (
    "spam_risk_too_many_posts",
    "spam_risk_too_many_pending_share",
    "rate_limit_exceeded",
)

_PUBLISH_RETRY_MINUTES = (60, 180, 360, 720)


def _publish_retry_delay(attempts: int, error: str) -> timedelta | None:
    """Пауза до повторной попытки публикации."""
    if not any(m in error for m in _RATE_LIMITED):
        return None
    if attempts >= len(_PUBLISH_RETRY_MINUTES):
        return None
    return timedelta(minutes=_PUBLISH_RETRY_MINUTES[attempts])


async def _reschedule(job_id: int, delay: timedelta, error: str) -> None:
    """Вернуть джоб в очередь публикации через delay, сохранив скачанный файл."""
    async with get_session() as session:
        job = await session.get(Job, job_id)
        if not job:
            return
        job.status = JOB_SCHEDULED
        job.scheduled_at = datetime.now(timezone.utc) + delay
        job.publish_attempts += 1
        job.error = error[:2000]


def _fail_msg(task: _Task, exc: Exception, lang: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """Текст (и кнопка) для окончательной ошибки публикации."""
    if isinstance(exc, tiktok_api.TikTokScopeError):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t("btn_reconnect_tiktok", lang), callback_data="connect_tiktok"
            )
        ]])
        return t("pub_tt_reconnect", lang, title=task.title), kb
    if isinstance(exc, _VideoTooLong):
        return t("ttc_too_long", lang, title=task.title,
                 duration=exc.duration, limit=exc.limit), None
    if isinstance(exc, _PrivacyUnavailable):
        return t("pub_tt_privacy_gone", lang, title=task.title), None
    if "spam_risk_too_many_pending_share" in str(exc):
        return t("pub_tt_too_many", lang, title=task.title), None
    if "spam_risk_too_many_posts" in str(exc) or "rate_limit_exceeded" in str(exc):
        return t("pub_tt_rate_limit", lang, title=task.title), None
    return t("pub_fail", lang, title=task.title, error=str(exc)), None


async def _yt_publish(task: _Task, path: str) -> str:
    """Заливка на YouTube с идемпотентностью по resumable-URI."""
    creds = credentials_from_refresh_token(
        task.refresh_token, task.client_id, task.client_secret
    )
    if task.yt_resumable_uri:
        try:
            return await asyncio.to_thread(
                resume_upload, creds, task.yt_resumable_uri, path
            )
        except UploadSessionExpired:
            logger.warning(
                "job=%d: resumable-сессия YouTube протухла — начинаю заливку заново",
                task.job_id,
            )
            task.yt_resumable_uri = None
    uri = await asyncio.to_thread(
        create_upload_session,
        creds, path, task.title, task.description, task.privacy,
    )
    await _save_yt_resumable_uri(task.job_id, uri)
    return await asyncio.to_thread(resume_upload, creds, uri, path)


class _VideoTooLong(RuntimeError):
    """Видео длиннее лимита аккаунта: TikTok отклонит его только ПОСЛЕ заливки байтов."""

    def __init__(self, duration: float, limit: int) -> None:
        super().__init__(f"video too long: {duration:.0f}s > {limit}s")
        self.duration = int(duration)
        self.limit = limit


class _PrivacyUnavailable(RuntimeError):
    """Сохранённая приватность больше не доступна аккаунту (профиль стал приватным."""

    def __init__(self, privacy: str, options: list[str]) -> None:
        super().__init__(
            f"privacy_level_option_mismatch: {privacy or '—'} unavailable "
            f"(allowed: {', '.join(options) or '—'})"
        )
        self.privacy = privacy


async def _tt_direct(task: _Task, path: str, access: str) -> str:
    """Direct Post + проверки, которые в режиме карточки делал пользователь."""
    if task.tt_publish_id:
        logger.info(
            "job=%d: продолжаю публикацию TikTok по сохранённому publish_id",
            task.job_id,
        )
        await tiktok_api.poll_publish_status(access, task.tt_publish_id)
        return task.tt_publish_id

    info = await tiktok_api.get_creator_info(access)
    limit = int(info.get("max_video_post_duration_sec") or 0)
    if limit:
        duration = await asyncio.to_thread(video_duration, path)
        if duration > limit:
            raise _VideoTooLong(duration, limit)
    options = list(info.get("privacy_level_options") or [])
    if not task.tt_privacy or task.tt_privacy not in options:
        raise _PrivacyUnavailable(task.tt_privacy or "", options)
    toggles = effective_toggles(
        info,
        tt_disable_comment=task.tt_disable_comment,
        tt_disable_duet=task.tt_disable_duet,
        tt_disable_stitch=task.tt_disable_stitch,
    )
    publish_id = await tiktok_api.direct_post(
        access,
        path,
        task.title,
        privacy=task.tt_privacy,
        disable_comment=toggles["tt_disable_comment"],
        disable_duet=toggles["tt_disable_duet"],
        disable_stitch=toggles["tt_disable_stitch"],
        brand_content_toggle=task.tt_brand_content,
        brand_organic_toggle=task.tt_brand_organic,
        creator_info=info,
        on_init=lambda pid: _save_tt_publish_id(task.job_id, pid),
    )
    await tiktok_api.poll_publish_status(access, publish_id)
    return publish_id


async def _publish(task: _Task, path: str) -> str:
    if task.platform == "youtube":
        return await _yt_publish(task, path)
    if task.platform == "tiktok":
        access = await tiktok_tokens.access_token(task.account_id)
        save_id = lambda pid: _save_tt_publish_id(task.job_id, pid)  # noqa: E731
        if not task.tt_direct:
            if task.tt_publish_id:
                return task.tt_publish_id
            return await tiktok_api.upload_to_inbox(access, path, on_init=save_id)
        try:
            return await _tt_direct(task, path, access)
        except tiktok_api.TikTokUnauditedError as exc:
            logger.warning(
                "job=%d: аудит TikTok не пройден (%s) — заливаю в черновики",
                task.job_id, str(exc)[:150],
            )
            task.fell_back_to_draft = True
            return await tiktok_api.upload_to_inbox(access, path, on_init=save_id)
    raise ValueError(f"unknown platform: {task.platform}")


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
    if task.tt_direct:
        logger.info("job=%d: оверлей пропущен (TikTok Direct Post)", task.job_id)
        return task.local_path, []
    overlay_tmp = await _download_overlay(bot, task.overlay_file_id)
    try:
        overlaid = await asyncio.to_thread(
            apply_overlay, task.local_path, overlay_tmp, task.overlay_position, task.overlay_scale
        )
    except Exception:  # noqa: BLE001 — не оставляем скачанный оверлей на диске
        _cleanup(overlay_tmp)
        raise
    return overlaid, [overlay_tmp, overlaid]


def _success_msg(task: _Task, remote_id: str, lang: str) -> str:
    if task.platform == "youtube":
        return t("pub_yt_ok", lang, id=remote_id, title=task.title, privacy=task.privacy)
    if task.fell_back_to_draft:
        return t("pub_tt_unaudited", lang, title=task.title)
    key = "pub_tt_live" if task.tt_direct else "pub_tt_ok"
    return t(key, lang, title=task.title)


async def process_scheduled(bot: Bot, limit: int = 3) -> int:
    """Опубликовать до `limit` видео. Возвращает число опубликованных."""
    published = 0
    for task in await _claim_due(limit):
        extra_files: list[str] = []
        keep_file = False
        lang = await user_lang(task.user_id)
        if not task.local_path or not os.path.exists(task.local_path):
            logger.warning("Файл job=%d пропал — возвращаю на скачивание", task.job_id)
            await _requeue(task.job_id)
            continue
        if task.platform == "youtube" and task.user_id in get_settings().admin_id_set:
            from bot.services.ai_meta import generate_meta, is_configured
            if is_configured():
                meta = await generate_meta(task.title)
                if meta:
                    task.title, task.description = meta.title, meta.description
                    logger.info("AI title job=%d → %s", task.job_id, meta.title)
        try:
            publish_path, extra_files = await _prepare_path(bot, task)
            remote_id = await _publish(task, publish_path)
            await _finalize(task.job_id, remote_id=remote_id, error=None,
                            platform=task.platform)
            published += 1
            try:
                await inc_videos_used(task.user_id)
            except Exception:  # noqa: BLE001
                logger.exception("Не смог увеличить счётчик видео job=%d", task.job_id)
            logger.info("Опубликовано job=%d (%s) → %s", task.job_id, task.platform, remote_id)
            await _notify(bot, task.user_id, _success_msg(task, remote_id, lang))
        except Exception as exc:  # noqa: BLE001
            delay = _publish_retry_delay(task.publish_attempts, str(exc))
            if delay is not None:
                keep_file = True
                await _reschedule(task.job_id, delay, str(exc))
                hours = max(1, round(delay.total_seconds() / 3600))
                logger.warning(
                    "job=%d: TikTok отклонил по лимиту (%s) — повтор через %d ч",
                    task.job_id, str(exc).splitlines()[0][:150], hours,
                )
                msg, kb = t("pub_tt_retry", lang, title=task.title, hours=hours), None
            else:
                logger.exception("Ошибка публикации job=%d", task.job_id)
                await _finalize(task.job_id, remote_id=None, error=str(exc))
                msg, kb = _fail_msg(task, exc, lang)
            await _notify(bot, task.user_id, msg, reply_markup=kb)
        finally:
            if not keep_file:
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


async def _notify(bot: Bot, user_id: int, text: str, reply_markup=None) -> None:
    try:
        await bot.send_message(user_id, text, reply_markup=reply_markup)
    except Exception:  # noqa: BLE001
        logger.warning("Не смог уведомить пользователя %s", user_id)


AWAITING_TTL_HOURS = 48
PUBLISHING_STUCK_MINUTES = 60
DOWNLOADING_STUCK_MINUTES = 60
CARD_RESEND_AFTER_MINUTES = 5


async def sweep_awaiting(bot: Bot) -> int:
    """Отменить неподтверждённые джобы, дослать потерянные карточки и разморозить зависшие в publishing."""
    now = datetime.now(timezone.utc)
    expired: list[tuple[int, int, str, str | None]] = []

    async with get_session() as session:
        rows = (
            await session.execute(
                select(Job, Connection.user_id)
                .join(Connection, Connection.id == Job.connection_id)
                .where(
                    Job.status == JOB_AWAITING,
                    Job.awaiting_since < now - timedelta(hours=AWAITING_TTL_HOURS),
                )
                .with_for_update(skip_locked=True, of=Job)
            )
        ).all()
        for job, user_id in rows:
            job.status = JOB_FAILED
            job.error = f"not confirmed within {AWAITING_TTL_HOURS}h"
            expired.append((job.card_message_id, user_id, job.title or "video", job.local_path))

        stuck = list(
            await session.scalars(
                select(Job)
                .where(
                    Job.status == JOB_PUBLISHING,
                    Job.updated_at < now - timedelta(minutes=PUBLISHING_STUCK_MINUTES),
                )
                .with_for_update(skip_locked=True)
            )
        )
        for job in stuck:
            job.status = JOB_SCHEDULED
        if stuck:
            resumed = sum(
                1 for j in stuck if j.tt_publish_id or j.yt_resumable_uri
            )
            logger.warning(
                "Разморожено зависших в publishing: %d (из них с сохранённой "
                "публикацией — %d)", len(stuck), resumed,
            )

        stuck_dl = list(
            await session.scalars(
                select(Job)
                .where(
                    Job.status == JOB_DOWNLOADING,
                    Job.updated_at < now - timedelta(minutes=DOWNLOADING_STUCK_MINUTES),
                )
                .with_for_update(skip_locked=True)
            )
        )
        for job in stuck_dl:
            job.download_attempts += 1
            job.status = JOB_PENDING
        if stuck_dl:
            logger.warning("Возвращено зависших в downloading: %d", len(stuck_dl))

    for card_message_id, user_id, title, path in expired:
        _cleanup(path or "")
        lang = await user_lang(user_id)
        if card_message_id:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=user_id, message_id=card_message_id, reply_markup=None
                )
            except Exception:  # noqa: BLE001
                pass
        await _notify(bot, user_id, t("ttc_expired", lang, title=title,
                                      hours=AWAITING_TTL_HOURS))
    if expired:
        logger.info("Отменено по таймауту подтверждения: %d", len(expired))

    await _resend_lost_cards(bot, now)
    return len(expired)


async def _resend_lost_cards(bot: Bot, now: datetime) -> None:
    """Дослать карточки подтверждения, которые не дошли до пользователя."""
    async with get_session() as session:
        lost = list(
            await session.scalars(
                select(Job.id).where(
                    Job.status == JOB_AWAITING,
                    Job.card_message_id.is_(None),
                    Job.awaiting_since
                    < now - timedelta(minutes=CARD_RESEND_AFTER_MINUTES),
                )
            )
        )
    if not lost:
        return
    from bot.handlers.tiktok_confirm import send_confirm_card

    for job_id in lost:
        try:
            await send_confirm_card(bot, job_id)
        except Exception:  # noqa: BLE001 — одна карточка не должна ронять уборку
            logger.exception("Не смог дослать карточку подтверждения job=%d", job_id)
    logger.info("Дослано карточек подтверждения: %d", len(lost))
