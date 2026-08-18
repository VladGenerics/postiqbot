"""Настройки автопубликации в TikTok — один раз на связку."""
from __future__ import annotations

import html
import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from bot.db.models import JOB_AWAITING, JOB_SCHEDULED, Connection, Job
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services import tiktok_api, tiktok_tokens
from bot.services.scheduling import compute_scheduled_at
from bot.services.tiktok_policy import POST_FIELDS, is_auto_post, is_direct_post

logger = logging.getLogger("postiqbot.tiktok_settings")

router = Router(name="tiktok_settings")

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

_BRAND_FIELDS = ("tt_brand_organic", "tt_brand_content")


async def _load(conn_id: int, user_id: int) -> Connection | None:
    """Связка с проверкой владельца: conn_id приходит из callback_data."""
    async with get_session() as session:
        return await session.scalar(
            select(Connection)
            .where(Connection.id == conn_id, Connection.user_id == user_id)
            .options(
                joinedload(Connection.publish_account),
                joinedload(Connection.source_channel),
            )
        )


def tt_settings_available(conn: Connection) -> bool:
    """Есть ли у связки экран настроек TikTok (только Direct Post-связки)."""
    return is_direct_post(
        conn.publish_account.platform if conn.publish_account else None,
        conn.source_channel.platform if conn.source_channel else None,
    )


def auto_enabled(conn: Connection) -> bool:
    """Работает ли у связки автопубликация (а не карточка на каждый пост)."""
    return is_auto_post(
        conn.publish_account.platform if conn.publish_account else None,
        conn.source_channel.platform if conn.source_channel else None,
        tt_auto=conn.tt_auto,
        tt_privacy=conn.tt_privacy,
        tt_consent_at=conn.tt_consent_at,
    )


def mode_label(conn: Connection, lang: str) -> str:
    """Короткая подпись режима для кнопки на карточке связки."""
    return t("c_tt_auto" if auto_enabled(conn) else "c_tt_card", lang)


async def _creator_info(conn: Connection) -> dict:
    """Свежие настройки аккаунта."""
    return await tiktok_api.get_creator_info(
        await tiktok_tokens.access_token(conn.publish_account_id)
    )


def _privacy_ok(conn: Connection, info: dict) -> bool:
    """Годится ли выбранный уровень приватности прямо сейчас."""
    return bool(conn.tt_privacy) and conn.tt_privacy in (
        info.get("privacy_level_options") or []
    )


def _screen_text(conn: Connection, info: dict, lang: str) -> str:
    nickname = html.escape(info.get("creator_nickname") or "TikTok")
    url = tiktok_api.profile_url(info)
    account = f'<a href="{url}">{nickname}</a>' if url else nickname
    lines = [
        t("tts_header", lang),
        "",
        t("ttc_account", lang, nickname=account),
        t("tts_mode_auto", lang) if auto_enabled(conn) else t("tts_mode_card", lang),
    ]
    if not conn.tt_privacy:
        lines.append(t("ttc_privacy_ask", lang))
    elif not _privacy_ok(conn, info):
        lines.append(t("tts_privacy_gone", lang))
    else:
        lines.append(t("ttc_privacy_is", lang, value=t(
            _PRIVACY_LABELS.get(conn.tt_privacy, "ttc_prv_private"), lang)))
    if conn.overlay_file_id and conn.overlay_position:
        lines.append(t("tts_overlay_ignored", lang))
    lines += ["", t("tts_consent" if not auto_enabled(conn) else "tts_consent_given", lang)]
    lines.append(t("ttc_music_notice_brand" if conn.tt_brand_content
                   else "ttc_music_notice", lang))
    return "\n".join(lines)


def _screen_markup(conn: Connection, info: dict, lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for level in info.get("privacy_level_options") or []:
        mark = "🔘 " if conn.tt_privacy == level else "⚪ "
        rows.append([InlineKeyboardButton(
            text=mark + t(_PRIVACY_LABELS.get(level, "ttc_prv_private"), lang),
            callback_data=f"ttsp:{conn.id}:{level}",
        )])
    for field, label_key, blocked_key in _TOGGLES:
        if info.get(blocked_key):
            mark = "🚫"
        else:
            mark = "☑️" if not getattr(conn, field) else "⬜️"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {t(label_key, lang)}",
            callback_data=f"ttst:{conn.id}:{field}",
        )])
    for field, label_key in (
        ("tt_brand_organic", "ttc_brand_organic"),
        ("tt_brand_content", "ttc_brand_content"),
    ):
        rows.append([InlineKeyboardButton(
            text=("☑️ " if getattr(conn, field) else "⬜️ ") + t(label_key, lang),
            callback_data=f"ttst:{conn.id}:{field}",
        )])
    if auto_enabled(conn):
        rows.append([InlineKeyboardButton(
            text=t("tts_btn_off", lang), callback_data=f"ttsa:{conn.id}:0"
        )])
    else:
        rows.append([InlineKeyboardButton(
            text=t("tts_btn_on", lang), callback_data=f"ttsa:{conn.id}:1"
        )])
    rows.append([InlineKeyboardButton(
        text=t("c_btn_back", lang), callback_data=f"conn:{conn.id}"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render(
    callback: CallbackQuery, conn: Connection, lang: str, info: dict | None = None
) -> None:
    """Отрисовать экран на месте: у фото-баннера правим подпись, у текста — текст."""
    if info is None:
        try:
            info = await _creator_info(conn)
        except Exception:  # noqa: BLE001 — TikTok не ответил / токен без scope
            await callback.answer(t("ttc_err_creator", lang), show_alert=True)
            return
    text = _screen_text(conn, info, lang)
    markup = _screen_markup(conn, info, lang)
    message = callback.message
    try:
        await message.edit_text(
            text, reply_markup=markup, link_preview_options=_NO_PREVIEW
        )
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        await message.edit_caption(caption=text, reply_markup=markup)
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        await message.edit_reply_markup(reply_markup=markup)
    except Exception:  # noqa: BLE001
        pass


async def _guard(callback: CallbackQuery, lang: str) -> Connection | None:
    """Загрузить связку и убедиться, что экран настроек ей вообще положен."""
    conn = await _load(int(callback.data.split(":")[1]), callback.from_user.id)
    if conn is None:
        await callback.answer(t("c_not_found", lang), show_alert=True)
        return None
    if not tt_settings_available(conn):
        await callback.answer(t("tts_unavailable", lang), show_alert=True)
        return None
    return conn


@router.callback_query(F.data.startswith("tts:"))
async def open_settings(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn = await _guard(callback, lang)
    if conn is None:
        return
    parts = callback.data.split(":")
    if len(parts) > 2 and parts[2] == "new":
        try:
            info = await _creator_info(conn)
        except Exception:  # noqa: BLE001
            await callback.answer(t("ttc_err_creator", lang), show_alert=True)
            return
        await callback.message.answer(
            _screen_text(conn, info, lang),
            reply_markup=_screen_markup(conn, info, lang),
            link_preview_options=_NO_PREVIEW,
        )
    else:
        await _render(callback, conn, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("ttsp:"))
async def set_privacy(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn = await _guard(callback, lang)
    if conn is None:
        return
    level = callback.data.split(":")[2]
    if level not in _PRIVACY_LABELS:
        await callback.answer()
        return
    async with get_session() as session:
        fresh = await session.get(Connection, conn.id)
        if fresh is None:
            await callback.answer(t("c_not_found", lang), show_alert=True)
            return
        fresh.tt_privacy = level
        if level == "SELF_ONLY" and fresh.tt_brand_content:
            fresh.tt_brand_content = False
        conn.tt_privacy, conn.tt_brand_content = level, fresh.tt_brand_content
    await _render(callback, conn, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("ttst:"))
async def toggle(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn = await _guard(callback, lang)
    if conn is None:
        return
    field = callback.data.split(":")[2]
    if field not in {f for f, _, _ in _TOGGLES} | set(_BRAND_FIELDS):
        await callback.answer()
        return
    try:
        info = await _creator_info(conn)
    except Exception:  # noqa: BLE001
        await callback.answer(t("ttc_err_creator", lang), show_alert=True)
        return
    blocked = {f: b for f, _, b in _TOGGLES}
    if field in blocked and info.get(blocked[field]):
        await callback.answer(t("ttc_tog_blocked", lang), show_alert=True)
        return
    async with get_session() as session:
        fresh = await session.get(Connection, conn.id)
        if fresh is None:
            await callback.answer(t("c_not_found", lang), show_alert=True)
            return
        value = not getattr(fresh, field)
        if field == "tt_brand_content" and value and fresh.tt_privacy == "SELF_ONLY":
            await callback.answer(t("ttc_brand_not_private", lang), show_alert=True)
            return
        setattr(fresh, field, value)
        setattr(conn, field, value)
    await _render(callback, conn, lang, info)
    await callback.answer()


async def _release_awaiting(conn: Connection) -> tuple[int, list[int]]:
    """Отпустить в публикацию видео этой связки, которые ждут подтверждения."""
    now = datetime.now(timezone.utc)
    async with get_session() as session:
        jobs = list(
            await session.scalars(
                select(Job)
                .where(Job.connection_id == conn.id, Job.status == JOB_AWAITING)
                .order_by(Job.created_at)
                .with_for_update(skip_locked=True)
            )
        )
        if not jobs:
            return 0, []
        last = (
            await session.scalars(
                select(Job.scheduled_at)
                .where(
                    Job.connection_id == conn.id,
                    Job.status.notin_((JOB_AWAITING,)),
                    Job.scheduled_at.isnot(None),
                )
                .order_by(Job.scheduled_at.desc())
                .limit(1)
            )
        ).first()
        cards: list[int] = []
        for job in jobs:
            for field in POST_FIELDS:
                setattr(job, field, getattr(conn, field))
            last = compute_scheduled_at(
                mode=conn.schedule_mode,
                interval_minutes=conn.interval_minutes,
                post_times=conn.post_times,
                tz_name=conn.tz,
                last_scheduled=last,
                now=now,
            )
            job.scheduled_at = last
            job.status = JOB_SCHEDULED
            job.awaiting_since = None
            if job.card_message_id:
                cards.append(job.card_message_id)
        return len(jobs), cards


async def _hold_scheduled(conn: Connection) -> list[int]:
    """Вернуть на подтверждение видео, которые уже ждут своего слота публикации."""
    now = datetime.now(timezone.utc)
    async with get_session() as session:
        jobs = list(
            await session.scalars(
                select(Job)
                .where(
                    Job.connection_id == conn.id,
                    Job.status == JOB_SCHEDULED,
                    Job.local_path.isnot(None),
                )
                .order_by(Job.scheduled_at)
                .with_for_update(skip_locked=True)
            )
        )
        for job in jobs:
            job.status = JOB_AWAITING
            job.awaiting_since = now
            job.card_message_id = None
        return [job.id for job in jobs]


@router.callback_query(F.data.startswith("ttsa:"))
async def switch_auto(callback: CallbackQuery) -> None:
    """Включить/выключить авто-режим. Включение = согласие на публикацию."""
    lang = await user_lang(callback.from_user.id)
    conn = await _guard(callback, lang)
    if conn is None:
        return
    on = callback.data.split(":")[2] == "1"
    if on and not conn.tt_privacy:
        await callback.answer(t("ttc_need_privacy", lang), show_alert=True)
        return
    info = None
    if on:
        try:
            info = await _creator_info(conn)
        except Exception:  # noqa: BLE001
            await callback.answer(t("ttc_err_creator", lang), show_alert=True)
            return
        if not _privacy_ok(conn, info):
            await callback.answer(t("ttc_need_privacy", lang), show_alert=True)
            await _render(callback, conn, lang, info)
            return
    async with get_session() as session:
        fresh = await session.get(Connection, conn.id)
        if fresh is None:
            await callback.answer(t("c_not_found", lang), show_alert=True)
            return
        fresh.tt_auto = on
        fresh.tt_consent_at = datetime.now(timezone.utc) if on else None
        conn.tt_auto, conn.tt_consent_at = fresh.tt_auto, fresh.tt_consent_at
    released, cards, held = 0, [], []
    if on:
        released, cards = await _release_awaiting(conn)
    else:
        held = await _hold_scheduled(conn)
    for message_id in cards:
        try:
            await callback.bot.edit_message_reply_markup(
                chat_id=callback.from_user.id, message_id=message_id, reply_markup=None
            )
        except Exception:  # noqa: BLE001 — сообщение старое/удалено
            pass
    logger.info(
        "conn=%d: автопубликация TikTok %s (отпущено: %d, возвращено на карточку: %d)",
        conn.id, "включена" if on else "выключена", released, len(held),
    )
    await _render(callback, conn, lang, info)
    if on:
        await callback.message.answer(
            t("tts_on_released", lang, n=released) if released
            else t("tts_on", lang)
        )
    else:
        await callback.message.answer(
            t("tts_off_held", lang, n=len(held)) if held else t("tts_off", lang)
        )
    await callback.answer()
    if held:
        from bot.handlers.tiktok_confirm import send_confirm_card

        for job_id in held:
            try:
                await send_confirm_card(callback.bot, job_id)
            except Exception:  # noqa: BLE001 — не дошло, дошлёт sweep_awaiting
                logger.exception("Не смог прислать карточку job=%d", job_id)
