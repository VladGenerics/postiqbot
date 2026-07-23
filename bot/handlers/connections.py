"""Управление связками клиента: список, пауза/возобновление, приватность, удаление."""
from __future__ import annotations

import asyncio
import os

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from bot.config import get_settings
from bot.db.models import Connection
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services.overlay import make_preview
from bot.ui import send_with_icon

router = Router(name="connections")


class SchedFlow(StatesGroup):
    waiting_interval = State()
    waiting_times = State()


class OverlayFlow(StatesGroup):
    waiting_image = State()


_POSITION_LABELS = {
    "top_left": "↖", "top_center": "⬆", "top_right": "↗",
    "middle_left": "⬅", "center": "⏺", "middle_right": "➡",
    "bottom_left": "↙", "bottom_center": "⬇", "bottom_right": "↘",
}
_POSITION_GRID = [
    ["top_left", "top_center", "top_right"],
    ["middle_left", "center", "middle_right"],
    ["bottom_left", "bottom_center", "bottom_right"],
]


def _sched_desc(conn: Connection, lang: str) -> str:
    if conn.schedule_mode == "interval" and conn.interval_minutes:
        return t("c_sched_interval", lang, n=conn.interval_minutes)
    if conn.schedule_mode == "times" and conn.post_times:
        return t("c_sched_times", lang, times=", ".join(conn.post_times), tz=conn.tz)
    return t("c_sched_now", lang)


def _ovl_desc(conn: Connection, lang: str) -> str:
    if conn.overlay_file_id and conn.overlay_position:
        return t("c_ovl_on", lang, pos=conn.overlay_position, scale=conn.overlay_scale)
    return t("c_ovl_off", lang)


_PRIVACY_NEXT = {"private": "unlisted", "unlisted": "public", "public": "private"}


def _priv_label(privacy: str, lang: str) -> str:
    return t(f"c_priv_{privacy}", lang) if privacy in _PRIVACY_NEXT else privacy


async def _load_connections(user_id: int) -> list[Connection]:
    async with get_session() as session:
        return list(
            await session.scalars(
                select(Connection)
                .where(Connection.user_id == user_id)
                .order_by(Connection.id)
                .options(
                    joinedload(Connection.source_channel),
                    joinedload(Connection.publish_account),
                )
            )
        )


async def _load_one(conn_id: int, user_id: int) -> Connection | None:
    """Загрузить связку с проверкой владельца."""
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection)
            .where(Connection.id == conn_id, Connection.user_id == user_id)
            .options(
                joinedload(Connection.source_channel),
                joinedload(Connection.publish_account),
            )
        )
        return conn


def _list_markup(connections: list[Connection]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{'🟢' if c.is_active else '⏸'} "
                f"{c.source_channel.channel_title} → {c.publish_account.channel_title}",
                callback_data=f"conn:{c.id}",
            )
        ]
        for c in connections
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _card_text(conn: Connection, lang: str) -> str:
    status = t("c_active", lang) if conn.is_active else t("c_paused", lang)
    return t(
        "c_card", lang,
        id=conn.id,
        src=conn.source_channel.channel_title,
        dst=conn.publish_account.channel_title,
        priv=_priv_label(conn.privacy, lang),
        sched=_sched_desc(conn, lang),
        ovl=_ovl_desc(conn, lang),
        status=status,
    )


def _card_markup(conn: Connection, lang: str) -> InlineKeyboardMarkup:
    toggle = InlineKeyboardButton(
        text=t("c_btn_pause" if conn.is_active else "c_btn_resume", lang),
        callback_data=f"conn_toggle:{conn.id}",
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [toggle],
            [InlineKeyboardButton(
                text=t("c_btn_visibility", lang, priv=_priv_label(conn.privacy, lang)),
                callback_data=f"conn_priv:{conn.id}",
            )],
            [InlineKeyboardButton(
                text=t("c_btn_schedule", lang, sched=_sched_desc(conn, lang)),
                callback_data=f"conn_sched:{conn.id}",
            )],
            [InlineKeyboardButton(
                text=t("c_btn_overlay", lang, ovl=_ovl_desc(conn, lang)),
                callback_data=f"conn_ovl:{conn.id}",
            )],
            [InlineKeyboardButton(text=t("c_btn_backfill", lang), callback_data=f"conn_bf:{conn.id}")],
            [InlineKeyboardButton(text=t("c_btn_delete", lang), callback_data=f"conn_del:{conn.id}")],
            [InlineKeyboardButton(text=t("c_btn_back", lang), callback_data="nav:mylist")],
        ]
    )


async def open_connections(message: Message, user_id: int) -> None:
    lang = await user_lang(user_id)
    connections = await _load_connections(user_id)
    if not connections:
        await send_with_icon(message, "connections", t("mylist_empty", lang), lang=lang)
        return
    await send_with_icon(
        message, "connections", t("mylist_title", lang),
        reply_markup=_list_markup(connections), lang=lang,
    )


@router.callback_query(F.data == "my_connections")
async def show_connections(callback: CallbackQuery) -> None:
    await open_connections(callback.message, callback.from_user.id)
    await callback.answer()


async def _edit(message: Message, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    """Отредактировать сообщение «на месте»: если это фото-баннер — правим его подпись, если текст — текст."""
    try:
        await message.edit_text(text, reply_markup=markup)
        return
    except Exception:  # noqa: BLE001 — у фото нет текста, пробуем подпись
        pass
    try:
        await message.edit_caption(caption=text, reply_markup=markup)
        return
    except Exception:  # noqa: BLE001
        pass
    await message.answer(text, reply_markup=markup)


async def _show_card(callback: CallbackQuery, conn: Connection, lang: str) -> None:
    """Показать карточку в том же окне (текст или подпись баннера)."""
    await _edit(callback.message, _card_text(conn, lang), _card_markup(conn, lang))


@router.callback_query(F.data.startswith("conn:"))
async def show_card(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    conn = await _load_one(conn_id, callback.from_user.id)
    if conn is None:
        await callback.answer(t("c_not_found", lang), show_alert=True)
        return
    await _show_card(callback, conn, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("conn_toggle:"))
async def toggle_connection(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection)
            .where(Connection.id == conn_id, Connection.user_id == callback.from_user.id)
            .options(
                joinedload(Connection.source_channel),
                joinedload(Connection.publish_account),
            )
        )
        if conn is None:
            await callback.answer(t("c_not_found", lang), show_alert=True)
            return
        conn.is_active = not conn.is_active
        text, markup = _card_text(conn, lang), _card_markup(conn, lang)
    await _edit(callback.message, text, markup)
    await callback.answer(t("c_resumed", lang) if conn.is_active else t("c_paused_toast", lang))


@router.callback_query(F.data.startswith("conn_priv:"))
async def cycle_privacy(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection)
            .where(Connection.id == conn_id, Connection.user_id == callback.from_user.id)
            .options(
                joinedload(Connection.source_channel),
                joinedload(Connection.publish_account),
            )
        )
        if conn is None:
            await callback.answer(t("c_not_found", lang), show_alert=True)
            return
        conn.privacy = _PRIVACY_NEXT.get(conn.privacy, "private")
        text, markup = _card_text(conn, lang), _card_markup(conn, lang)
    await _edit(callback.message, text, markup)
    await callback.answer()


@router.callback_query(F.data.startswith("conn_del:"))
async def confirm_delete(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("c_btn_del_yes", lang), callback_data=f"conn_delyes:{conn_id}"),
                InlineKeyboardButton(text=t("c_btn_cancel", lang), callback_data=f"conn:{conn_id}"),
            ]
        ]
    )
    await _edit(callback.message, t("c_del_confirm", lang), kb)
    await callback.answer()


async def _backfill_count_kb(conn_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(n), callback_data=f"bf_n:{conn_id}:{n}") for n in (25, 50, 100)],
        [InlineKeyboardButton(text="300", callback_data=f"bf_n:{conn_id}:300"),
         InlineKeyboardButton(text=t("bf_all", lang), callback_data=f"bf_n:{conn_id}:1000")],
        [InlineKeyboardButton(text=t("c_btn_back", lang), callback_data=f"conn:{conn_id}")],
    ])


def _backfill_daily_kb(conn_id: int, total: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(n), callback_data=f"bf:{conn_id}:{total}:{n}") for n in (1, 2, 4)],
        [InlineKeyboardButton(text="8", callback_data=f"bf:{conn_id}:{total}:8"),
         InlineKeyboardButton(text=t("bf_all", lang), callback_data=f"bf:{conn_id}:{total}:1000")],
        [InlineKeyboardButton(text=t("c_btn_back", lang), callback_data=f"conn_bf:{conn_id}")],
    ])


@router.callback_query(F.data.startswith("conn_bf:"))
async def backfill_menu(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    await _edit(callback.message, t("bf_choose", lang), await _backfill_count_kb(conn_id, lang))
    await callback.answer()


@router.callback_query(F.data.startswith("bf_n:"))
async def backfill_daily_menu(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    _, conn_id, total = callback.data.split(":", 2)
    await _edit(callback.message, t("bf_choose_daily", lang), _backfill_daily_kb(int(conn_id), int(total), lang))
    await callback.answer()


@router.callback_query(F.data.startswith("bf:"))
async def backfill_do(callback: CallbackQuery) -> None:
    from bot.services.backfill import backfill_connection

    lang = await user_lang(callback.from_user.id)
    parts = callback.data.split(":")
    conn_id, total = int(parts[1]), int(parts[2])
    daily = int(parts[3]) if len(parts) >= 4 else get_settings().per_account_daily_limit
    await callback.answer(t("bf_working", lang))
    await _edit(callback.message, t("bf_working", lang))
    res = await backfill_connection(conn_id, total, user_id=callback.from_user.id, daily_limit=daily)
    if not res.ok:
        txt = t("bf_empty", lang) if res.error in ("empty", "unsupported", "no_source") else t("c_not_found", lang)
    elif res.created == 0:
        txt = t("bf_none", lang)
    else:
        txt = t("bf_done", lang, created=res.created, title=res.title)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("c_btn_back", lang), callback_data=f"conn:{conn_id}")],
    ])
    await _edit(callback.message, txt, kb)


@router.callback_query(F.data.startswith("conn_sched:"))
async def schedule_menu(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("c_sched_btn_now", lang), callback_data=f"sched_now:{conn_id}")],
            [InlineKeyboardButton(text=t("c_sched_btn_int", lang), callback_data=f"sched_int:{conn_id}")],
            [InlineKeyboardButton(text=t("c_sched_btn_times", lang), callback_data=f"sched_times:{conn_id}")],
            [InlineKeyboardButton(text=t("c_btn_back", lang), callback_data=f"conn:{conn_id}")],
        ]
    )
    await _edit(callback.message, t("c_sched_menu", lang), kb)
    await callback.answer()


async def _set_schedule(conn_id: int, user_id: int, **fields) -> Connection | None:
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection)
            .where(Connection.id == conn_id, Connection.user_id == user_id)
            .options(
                joinedload(Connection.source_channel),
                joinedload(Connection.publish_account),
            )
        )
        if conn is None:
            return None
        for k, v in fields.items():
            setattr(conn, k, v)
        return conn


@router.callback_query(F.data.startswith("sched_now:"))
async def sched_now(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    conn = await _set_schedule(
        conn_id, callback.from_user.id, schedule_mode="immediate", interval_minutes=0
    )
    if conn is None:
        await callback.answer(t("c_not_found", lang), show_alert=True)
        return
    await _edit(callback.message, _card_text(conn, lang), _card_markup(conn, lang))
    await callback.answer(t("c_sched_now_toast", lang))


@router.callback_query(F.data.startswith("sched_int:"))
async def sched_int(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    await state.update_data(conn_id=conn_id)
    await state.set_state(SchedFlow.waiting_interval)
    await callback.message.answer(t("c_int_prompt", lang))
    await callback.answer()


@router.message(SchedFlow.waiting_interval)
async def got_interval(message: Message, state: FSMContext) -> None:
    lang = await user_lang(message.from_user.id)
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer(t("c_int_bad", lang))
        return
    data = await state.get_data()
    conn = await _set_schedule(
        data["conn_id"], message.from_user.id,
        schedule_mode="interval", interval_minutes=int(text),
    )
    await state.clear()
    if conn is None:
        await message.answer(t("c_not_found_dot", lang))
        return
    await message.answer(_card_text(conn, lang), reply_markup=_card_markup(conn, lang))


@router.callback_query(F.data.startswith("sched_times:"))
async def sched_times(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    await state.update_data(conn_id=conn_id)
    await state.set_state(SchedFlow.waiting_times)
    await callback.message.answer(t("c_times_prompt", lang))
    await callback.answer()


@router.message(SchedFlow.waiting_times)
async def got_times(message: Message, state: FSMContext) -> None:
    import re

    lang = await user_lang(message.from_user.id)
    raw = (message.text or "").strip()
    tz = "UTC"
    tokens = raw.replace(",", " ").split()
    times = []
    for tok in tokens:
        if "/" in tok:
            tz = tok
        elif re.fullmatch(r"\d{1,2}:\d{2}", tok):
            h, m = tok.split(":")
            if 0 <= int(h) <= 23 and 0 <= int(m) <= 59:
                times.append(f"{int(h):02d}:{int(m):02d}")
    if not times:
        await message.answer(t("c_times_bad", lang))
        return
    data = await state.get_data()
    conn = await _set_schedule(
        data["conn_id"], message.from_user.id,
        schedule_mode="times", post_times=sorted(set(times)), tz=tz,
    )
    await state.clear()
    if conn is None:
        await message.answer(t("c_not_found_dot", lang))
        return
    await message.answer(_card_text(conn, lang), reply_markup=_card_markup(conn, lang))


def _overlay_markup(conn: Connection, lang: str) -> InlineKeyboardMarkup:
    rows = []
    for grid_row in _POSITION_GRID:
        rows.append([
            InlineKeyboardButton(
                text=("• " if conn.overlay_position == p else "") + _POSITION_LABELS[p],
                callback_data=f"ovl_pos:{conn.id}:{p}",
            )
            for p in grid_row
        ])
    rows.append([
        InlineKeyboardButton(
            text=("• " if conn.overlay_scale == s else "") + f"{s}%",
            callback_data=f"ovl_scale:{conn.id}:{s}",
        )
        for s in (20, 35, 50, 75, 100)
    ])
    rows.append([
        InlineKeyboardButton(text=t("c_ovl_btn_replace", lang), callback_data=f"ovl_replace:{conn.id}"),
        InlineKeyboardButton(text=t("c_ovl_btn_remove", lang), callback_data=f"ovl_del:{conn.id}"),
    ])
    rows.append([InlineKeyboardButton(text=t("c_btn_back", lang), callback_data=f"conn:{conn.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _ovl_file_id(message: Message) -> str | None:
    if message.photo:
        return message.photo[-1].file_id
    if message.animation:
        return message.animation.file_id
    if message.document:
        return message.document.file_id
    if message.sticker:
        return message.sticker.file_id
    return None


async def _build_preview(bot: Bot, conn: Connection) -> tuple[str, list[str]]:
    """Скачать оверлей и собрать JPG-превью. Вернуть (путь_превью, temp-файлы)."""
    dl = get_settings().download_dir
    os.makedirs(dl, exist_ok=True)
    file = await bot.get_file(conn.overlay_file_id)
    ext = os.path.splitext(file.file_path or "")[1] or ".bin"
    src = os.path.join(dl, f"ovlprev_src_{file.file_unique_id}{ext}")
    await bot.download_file(file.file_path, src)
    preview = os.path.join(dl, f"ovlprev_{conn.id}.jpg")
    await asyncio.to_thread(
        make_preview, src, conn.overlay_position or "bottom_right",
        conn.overlay_scale, preview,
    )
    return preview, [src, preview]


def _cleanup(paths: list[str]) -> None:
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


@router.callback_query(F.data.startswith("conn_ovl:"))
async def overlay_menu(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    conn = await _load_one(conn_id, callback.from_user.id)
    if conn is None:
        await callback.answer(t("c_not_found", lang), show_alert=True)
        return
    if conn.overlay_file_id:
        await _refresh_preview(callback, conn, lang)
    else:
        await state.update_data(conn_id=conn_id)
        await state.set_state(OverlayFlow.waiting_image)
        await callback.message.answer(t("c_ovl_prompt", lang) + t("c_ovl_hint", lang))
    await callback.answer()


@router.callback_query(F.data.startswith("ovl_replace:"))
async def overlay_replace(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    await state.update_data(conn_id=conn_id)
    await state.set_state(OverlayFlow.waiting_image)
    await callback.message.answer(t("c_ovl_prompt_replace", lang) + t("c_ovl_hint", lang))
    await callback.answer()


@router.message(OverlayFlow.waiting_image)
async def overlay_got_image(message: Message, state: FSMContext) -> None:
    lang = await user_lang(message.from_user.id)
    file_id = _ovl_file_id(message)
    if not file_id:
        await message.answer(t("c_ovl_not_image", lang))
        return
    data = await state.get_data()
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection)
            .where(Connection.id == data["conn_id"], Connection.user_id == message.from_user.id)
            .options(
                joinedload(Connection.source_channel),
                joinedload(Connection.publish_account),
            )
        )
        if conn is None:
            await state.clear()
            await message.answer(t("c_not_found_dot", lang))
            return
        conn.overlay_file_id = file_id
        if not conn.overlay_position:
            conn.overlay_position = "bottom_right"
        markup = _overlay_markup(conn, lang)
        conn_copy = conn
    await state.clear()
    preview, temps = await _build_preview(message.bot, conn_copy)
    await message.answer_photo(
        FSInputFile(preview),
        caption=t("c_ovl_saved", lang),
        reply_markup=markup,
    )
    _cleanup(temps)


async def _update_overlay(conn_id: int, user_id: int, **fields) -> Connection | None:
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection)
            .where(Connection.id == conn_id, Connection.user_id == user_id)
            .options(
                joinedload(Connection.source_channel),
                joinedload(Connection.publish_account),
            )
        )
        if conn is None:
            return None
        for k, v in fields.items():
            setattr(conn, k, v)
        return conn


async def _refresh_preview(callback: CallbackQuery, conn: Connection, lang: str) -> None:
    """Перерисовать превью-фото с новыми позицией/размером."""
    preview, temps = await _build_preview(callback.bot, conn)
    try:
        await callback.message.edit_media(
            InputMediaPhoto(media=FSInputFile(preview), caption=t("c_ovl_text", lang)),
            reply_markup=_overlay_markup(conn, lang),
        )
    except Exception:  # noqa: BLE001 — сообщение не фото / не изменилось
        await callback.message.answer_photo(
            FSInputFile(preview), caption=t("c_ovl_text", lang), reply_markup=_overlay_markup(conn, lang)
        )
    _cleanup(temps)


@router.callback_query(F.data.startswith("ovl_pos:"))
async def overlay_set_position(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    _, conn_id, pos = callback.data.split(":", 2)
    conn = await _update_overlay(int(conn_id), callback.from_user.id, overlay_position=pos)
    if conn is None:
        await callback.answer(t("c_not_found_short", lang), show_alert=True)
        return
    await _refresh_preview(callback, conn, lang)
    await callback.answer(t("c_ovl_pos_toast", lang))


@router.callback_query(F.data.startswith("ovl_scale:"))
async def overlay_set_scale(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    _, conn_id, scale = callback.data.split(":", 2)
    conn = await _update_overlay(int(conn_id), callback.from_user.id, overlay_scale=int(scale))
    if conn is None:
        await callback.answer(t("c_not_found_short", lang), show_alert=True)
        return
    await _refresh_preview(callback, conn, lang)
    await callback.answer(t("c_ovl_scale_toast", lang))


@router.callback_query(F.data.startswith("ovl_del:"))
async def overlay_remove(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    conn = await _update_overlay(
        conn_id, callback.from_user.id, overlay_file_id=None, overlay_position=None
    )
    if conn is None:
        await callback.answer(t("c_not_found_short", lang), show_alert=True)
        return
    await _show_card(callback, conn, lang)
    await callback.answer(t("c_ovl_removed_toast", lang))


@router.callback_query(F.data.startswith("conn_delyes:"))
async def do_delete(callback: CallbackQuery) -> None:
    lang = await user_lang(callback.from_user.id)
    conn_id = int(callback.data.split(":", 1)[1])
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection).where(
                Connection.id == conn_id, Connection.user_id == callback.from_user.id
            )
        )
        if conn is None:
            await callback.answer(t("c_not_found", lang), show_alert=True)
            return
        await session.delete(conn)
    await _edit(callback.message, t("c_deleted", lang))
    await callback.answer(t("c_deleted_toast", lang))
