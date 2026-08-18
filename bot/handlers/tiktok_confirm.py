"""Карточка подтверждения публикации в TikTok (Direct Post)."""
from __future__ import annotations

import asyncio
import html
import logging
import os
import subprocess
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from bot.db.models import (
    JOB_AWAITING,
    JOB_FAILED,
    JOB_SCHEDULED,
    Connection,
    Job,
    PublishAccount,
)
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services import tiktok_api, tiktok_tokens
from bot.services.overlay import video_duration
from bot.services.scheduling import compute_scheduled_at

logger = logging.getLogger("postiqbot.tiktok_confirm")

router = Router(name="tiktok_confirm")

_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

_PRIVACY_LABELS = {
    "PUBLIC_TO_EVERYONE": "ttc_prv_public",
    "FOLLOWER_OF_CREATOR": "ttc_prv_followers",
    "MUTUAL_FOLLOW_FRIENDS": "ttc_prv_friends",
    "SELF_ONLY": "ttc_prv_private",
}

_TOGGLES = (
    ("tt_disable_comment", "ttc_tog_comment", "comment_disabled"),
    ("tt_disable_duet", "ttc_tog_duet", "duet_disabled"),
    ("tt_disable_stitch", "ttc_tog_stitch", "stitch_disabled"),
)


class TitleFlow(StatesGroup):
    waiting = State()


_THUMB_TIMEOUT = 60


def _thumbnail(video_path: str) -> str | None:
    """Кадр из видео для превью в карточке (гайдлайны требуют показать контент)."""
    dest = f"{os.path.splitext(video_path)[0]}_thumb.jpg"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "1", "-i", video_path, "-frames:v", "1",
             "-vf", "scale=480:-2", dest],
            capture_output=True, text=True, check=True, timeout=_THUMB_TIMEOUT,
        )
        return dest if os.path.exists(dest) else None
    except Exception:  # noqa: BLE001
        return None


async def _load(job_id: int, user_id: int) -> Job | None:
    """Джоб вместе со связкой."""
    async with get_session() as session:
        job = (
            await session.scalars(
                select(Job)
                .where(Job.id == job_id)
                .options(
                    joinedload(Job.connection).joinedload(Connection.publish_account)
                )
            )
        ).first()
        if job is None or job.connection.user_id != user_id:
            return None
        return job


async def _creator_info(job: Job) -> dict:
    """Свежие настройки аккаунта."""
    acc: PublishAccount = job.connection.publish_account
    return await tiktok_api.get_creator_info(await tiktok_tokens.access_token(acc.id))


def _card_text(job: Job, info: dict, lang: str) -> str:
    nickname = html.escape(info.get("creator_nickname") or "TikTok")
    url = tiktok_api.profile_url(info)
    account = f'<a href="{url}">{nickname}</a>' if url else nickname
    lines = [
        t("ttc_header", lang),
        "",
        f"🎬 <b>{html.escape(job.title or 'video')}</b>",
        t("ttc_account", lang, nickname=account),
    ]
    if job.tt_privacy:
        lines.append(t("ttc_privacy_is", lang, value=t(_PRIVACY_LABELS.get(
            job.tt_privacy, "ttc_prv_private"), lang)))
    else:
        lines.append(t("ttc_privacy_ask", lang))
    lines += ["", t("ttc_music_notice_brand" if job.tt_brand_content
                    else "ttc_music_notice", lang)]
    return "\n".join(lines)


def _card_markup(job: Job, info: dict, lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for level in info.get("privacy_level_options") or []:
        mark = "🔘 " if job.tt_privacy == level else "⚪ "
        rows.append([InlineKeyboardButton(
            text=mark + t(_PRIVACY_LABELS.get(level, "ttc_prv_private"), lang),
            callback_data=f"ttc_prv:{job.id}:{level}",
        )])
    for field, label_key, blocked_key in _TOGGLES:
        blocked = bool(info.get(blocked_key))
        enabled = not getattr(job, field)
        if blocked:
            mark = "🚫"
        else:
            mark = "☑️" if enabled else "⬜️"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {t(label_key, lang)}",
            callback_data=f"ttc_tog:{job.id}:{field}",
        )])
    rows.append([InlineKeyboardButton(
        text=("☑️ " if job.tt_brand_organic else "⬜️ ") + t("ttc_brand_organic", lang),
        callback_data=f"ttc_tog:{job.id}:tt_brand_organic",
    )])
    rows.append([InlineKeyboardButton(
        text=("☑️ " if job.tt_brand_content else "⬜️ ") + t("ttc_brand_content", lang),
        callback_data=f"ttc_tog:{job.id}:tt_brand_content",
    )])
    rows.append([InlineKeyboardButton(
        text=t("ttc_btn_title", lang), callback_data=f"ttc_title:{job.id}"
    )])
    rows.append([
        InlineKeyboardButton(text=t("ttc_btn_go", lang), callback_data=f"ttc_go:{job.id}"),
        InlineKeyboardButton(text=t("ttc_btn_no", lang), callback_data=f"ttc_no:{job.id}"),
    ])
    rows.append([InlineKeyboardButton(
        text=t("ttc_btn_auto", lang), callback_data=f"tts:{job.connection_id}:new"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _fail(job_id: int, reason: str) -> None:
    async with get_session() as session:
        job = await session.get(Job, job_id)
        if job:
            job.status = JOB_FAILED
            job.error = reason[:2000]


def _cleanup(path: str | None) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        logger.warning("Не смог удалить файл %s", path)


async def send_confirm_card(bot: Bot, job_id: int) -> None:
    """Прислать пользователю карточку подтверждения для скачанного видео."""
    async with get_session() as session:
        row = (
            await session.execute(
                select(Job, Connection.user_id)
                .join(Connection, Connection.id == Job.connection_id)
                .where(Job.id == job_id)
            )
        ).first()
    if not row:
        return
    job, user_id = row
    lang = await user_lang(user_id)
    full = await _load(job_id, user_id)
    if full is None:
        return

    try:
        info = await _creator_info(full)
    except tiktok_api.TikTokScopeError:
        await _fail(job_id, "TikTok: нужен повторный вход (scope video.publish)")
        _cleanup(job.local_path)
        await bot.send_message(
            user_id,
            t("pub_tt_reconnect", lang, title=job.title or "video"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=t("btn_reconnect_tiktok", lang), callback_data="connect_tiktok"
                )
            ]]),
        )
        return

    max_sec = info.get("max_video_post_duration_sec") or 0
    duration = await asyncio.to_thread(video_duration, job.local_path or "")
    if max_sec and duration > max_sec:
        await _fail(job_id, f"Видео {int(duration)}с длиннее лимита TikTok {max_sec}с")
        _cleanup(job.local_path)
        await bot.send_message(user_id, t(
            "ttc_too_long", lang, title=job.title or "video",
            duration=int(duration), limit=int(max_sec),
        ))
        return

    text = _card_text(full, info, lang)
    markup = _card_markup(full, info, lang)
    thumb = await asyncio.to_thread(_thumbnail, job.local_path or "")
    try:
        if thumb:
            msg = await bot.send_photo(
                user_id, FSInputFile(thumb), caption=text, reply_markup=markup
            )
        else:
            msg = await bot.send_message(
                user_id, text, reply_markup=markup, link_preview_options=_NO_PREVIEW
            )
    finally:
        _cleanup(thumb)

    async with get_session() as session:
        fresh = await session.get(Job, job_id)
        if fresh:
            fresh.card_message_id = msg.message_id


async def _redraw(
    callback: CallbackQuery, job: Job, lang: str, info: dict | None = None
) -> None:
    """Перерисовать карточку на месте (у фото правим подпись, у текста — текст)."""
    if info is None:
        try:
            info = await _creator_info(job)
        except Exception:  # noqa: BLE001
            await callback.answer(t("ttc_err_creator", lang), show_alert=True)
            return
    text = _card_text(job, info, lang)
    markup = _card_markup(job, info, lang)
    try:
        await callback.message.edit_caption(caption=text, reply_markup=markup)
    except Exception:  # noqa: BLE001 — сообщение без фото
        try:
            await callback.message.edit_text(
                text, reply_markup=markup, link_preview_options=_NO_PREVIEW
            )
        except Exception:  # noqa: BLE001 — текст не изменился, обновим только кнопки
            try:
                await callback.message.edit_reply_markup(reply_markup=markup)
            except Exception:  # noqa: BLE001
                pass


async def _guard(callback: CallbackQuery, lang: str) -> Job | None:
    """Загрузить джоб и убедиться, что он всё ещё ждёт подтверждения."""
    job_id = int(callback.data.split(":")[1])
    job = await _load(job_id, callback.from_user.id)
    if job is None:
        await callback.answer(t("ttc_gone", lang), show_alert=True)
        return None
    if job.status != JOB_AWAITING:
        await callback.answer(t("ttc_stale", lang), show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:  # noqa: BLE001
            pass
        return None
    return job


@router.callback_query(F.data.startswith("ttc_prv:"))
async def set_privacy(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    job = await _guard(callback, lang)
    if job is None:
        return
    level = callback.data.split(":")[2]
    async with get_session() as session:
        fresh = await session.get(Job, job.id)
        if fresh:
            fresh.tt_privacy = level
            if level == "SELF_ONLY" and fresh.tt_brand_content:
                fresh.tt_brand_content = False
            job.tt_privacy = level
            job.tt_brand_content = fresh.tt_brand_content
    await _redraw(callback, job, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("ttc_tog:"))
async def toggle(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    job = await _guard(callback, lang)
    if job is None:
        return
    field = callback.data.split(":")[2]
    allowed = {f for f, _, _ in _TOGGLES} | {"tt_brand_organic", "tt_brand_content"}
    if field not in allowed:
        await callback.answer()
        return

    try:
        info = await _creator_info(job)
    except Exception:  # noqa: BLE001
        await callback.answer(t("ttc_err_creator", lang), show_alert=True)
        return

    blocked_map = {f: b for f, _, b in _TOGGLES}
    if field in blocked_map and info.get(blocked_map[field]):
        await callback.answer(t("ttc_tog_blocked", lang), show_alert=True)
        return

    async with get_session() as session:
        fresh = await session.get(Job, job.id)
        if fresh is None:
            return
        new_value = not getattr(fresh, field)
        if field == "tt_brand_content" and new_value and fresh.tt_privacy == "SELF_ONLY":
            await callback.answer(t("ttc_brand_not_private", lang), show_alert=True)
            return
        setattr(fresh, field, new_value)
        setattr(job, field, new_value)
    await _redraw(callback, job, lang, info)
    await callback.answer()


@router.callback_query(F.data.startswith("ttc_title:"))
async def edit_title(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await user_lang(callback.from_user.id)
    job = await _guard(callback, lang)
    if job is None:
        return
    await state.set_state(TitleFlow.waiting)
    await state.update_data(job_id=job.id, card_message_id=callback.message.message_id)
    await callback.message.answer(t("ttc_ask_title", lang))
    await callback.answer()


@router.message(TitleFlow.waiting)
async def save_title(message: Message, state: FSMContext) -> None:
    lang = await user_lang(message.from_user.id)
    data = await state.get_data()
    await state.clear()
    job_id = data.get("job_id")
    title = (message.text or "").strip()[:150]
    if not job_id or not title:
        return
    job = await _load(int(job_id), message.from_user.id)
    if job is None or job.status != JOB_AWAITING:
        await message.answer(t("ttc_stale", lang))
        return
    async with get_session() as session:
        fresh = await session.get(Job, int(job_id))
        if fresh:
            fresh.title = title
            job.title = title
    card_id = data.get("card_message_id")
    if card_id:
        try:
            info = await _creator_info(job)
            await message.bot.edit_message_caption(
                chat_id=message.from_user.id,
                message_id=int(card_id),
                caption=_card_text(job, info, lang),
                reply_markup=_card_markup(job, info, lang),
            )
        except Exception:  # noqa: BLE001
            logger.warning("Не смог обновить карточку job=%s после смены заголовка", job_id)
    await message.answer(t("ttc_title_saved", lang, title=html.escape(title)))


@router.callback_query(F.data.startswith("ttc_go:"))
async def confirm(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    job = await _guard(callback, lang)
    if job is None:
        return
    if not job.tt_privacy:
        await callback.answer(t("ttc_need_privacy", lang), show_alert=True)
        return

    conn = job.connection
    async with get_session() as session:
        fresh = await session.get(Job, job.id)
        if fresh is None or fresh.status != JOB_AWAITING:
            await callback.answer(t("ttc_stale", lang), show_alert=True)
            return
        last = (
            await session.scalars(
                select(Job.scheduled_at)
                .where(Job.connection_id == conn.id, Job.id != fresh.id)
                .order_by(Job.scheduled_at.desc())
                .limit(1)
            )
        ).first()
        fresh.scheduled_at = compute_scheduled_at(
            mode=conn.schedule_mode,
            interval_minutes=conn.interval_minutes,
            post_times=conn.post_times,
            tz_name=conn.tz,
            last_scheduled=last,
            now=datetime.now(timezone.utc),
        )
        fresh.status = JOB_SCHEDULED
        fresh.awaiting_since = None

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001
        pass
    await callback.message.answer(t("ttc_confirmed", lang, title=html.escape(job.title or "video")))
    await callback.answer()


@router.callback_query(F.data.startswith("ttc_no:"))
async def cancel(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    job = await _guard(callback, lang)
    if job is None:
        return
    path = job.local_path
    await _fail(job.id, "Отменено пользователем")
    _cleanup(path)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001
        pass
    await callback.message.answer(t("ttc_cancelled", lang, title=html.escape(job.title or "video")))
    await callback.answer()
