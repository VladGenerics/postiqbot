"""Управление связками клиента: список, пауза/возобновление, приватность, удаление."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from bot.db.models import Connection
from bot.db.session import get_session

router = Router(name="connections")


class SchedFlow(StatesGroup):
    waiting_interval = State()
    waiting_times = State()


def _sched_desc(conn: Connection) -> str:
    if conn.schedule_mode == "interval" and conn.interval_minutes:
        return f"⏱ каждые {conn.interval_minutes} мин"
    if conn.schedule_mode == "times" and conn.post_times:
        return f"🕐 в {', '.join(conn.post_times)} ({conn.tz})"
    return "⚡ сразу"

_PRIVACY_NEXT = {"private": "unlisted", "unlisted": "public", "public": "private"}
_PRIVACY_LABEL = {"private": "🔒 приватное", "unlisted": "🔗 по ссылке", "public": "🌍 публичное"}


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


def _card_text(conn: Connection) -> str:
    status = "🟢 активна" if conn.is_active else "⏸ на паузе"
    return (
        f"<b>Связка #{conn.id}</b>\n\n"
        f"📡 Источник: <b>{conn.source_channel.channel_title}</b>\n"
        f"📤 Публикую на: <b>{conn.publish_account.channel_title}</b>\n"
        f"👁 Доступ публикаций: {_PRIVACY_LABEL.get(conn.privacy, conn.privacy)}\n"
        f"⏰ Расписание: {_sched_desc(conn)}\n"
        f"⚙️ Статус: {status}"
    )


def _card_markup(conn: Connection) -> InlineKeyboardMarkup:
    toggle = (
        InlineKeyboardButton(text="⏸ Поставить на паузу", callback_data=f"conn_toggle:{conn.id}")
        if conn.is_active
        else InlineKeyboardButton(text="▶️ Возобновить", callback_data=f"conn_toggle:{conn.id}")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [toggle],
            [
                InlineKeyboardButton(
                    text=f"👁 Доступ: {_PRIVACY_LABEL.get(conn.privacy, conn.privacy)}",
                    callback_data=f"conn_priv:{conn.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⏰ Расписание: {_sched_desc(conn)}",
                    callback_data=f"conn_sched:{conn.id}",
                )
            ],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"conn_del:{conn.id}")],
            [InlineKeyboardButton(text="« К списку", callback_data="my_connections")],
        ]
    )


@router.callback_query(F.data == "my_connections")
async def show_connections(callback: CallbackQuery) -> None:
    connections = await _load_connections(callback.from_user.id)
    if not connections:
        await callback.message.answer(
            "У тебя пока нет связок. Подключи канал и добавь источник 👇"
        )
        await callback.answer()
        return
    await callback.message.answer(
        "📋 <b>Твои связки</b> (источник → твой канал).\nВыбери, чтобы настроить:",
        reply_markup=_list_markup(connections),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("conn:"))
async def show_card(callback: CallbackQuery) -> None:
    conn_id = int(callback.data.split(":", 1)[1])
    conn = await _load_one(conn_id, callback.from_user.id)
    if conn is None:
        await callback.answer("Связка не найдена", show_alert=True)
        return
    await callback.message.edit_text(_card_text(conn), reply_markup=_card_markup(conn))
    await callback.answer()


@router.callback_query(F.data.startswith("conn_toggle:"))
async def toggle_connection(callback: CallbackQuery) -> None:
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
            await callback.answer("Связка не найдена", show_alert=True)
            return
        conn.is_active = not conn.is_active
        text, markup = _card_text(conn), _card_markup(conn)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer("Возобновлено" if conn.is_active else "Поставлено на паузу")


@router.callback_query(F.data.startswith("conn_priv:"))
async def cycle_privacy(callback: CallbackQuery) -> None:
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
            await callback.answer("Связка не найдена", show_alert=True)
            return
        conn.privacy = _PRIVACY_NEXT.get(conn.privacy, "private")
        text, markup = _card_text(conn), _card_markup(conn)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("conn_del:"))
async def confirm_delete(callback: CallbackQuery) -> None:
    conn_id = int(callback.data.split(":", 1)[1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"conn_delyes:{conn_id}"),
                InlineKeyboardButton(text="« Отмена", callback_data=f"conn:{conn_id}"),
            ]
        ]
    )
    await callback.message.edit_text(
        "Удалить эту связку? Новые видео из источника публиковаться не будут.\n"
        "<i>Уже опубликованные видео останутся на твоём канале.</i>",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("conn_sched:"))
async def schedule_menu(callback: CallbackQuery) -> None:
    conn_id = int(callback.data.split(":", 1)[1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Сразу", callback_data=f"sched_now:{conn_id}")],
            [InlineKeyboardButton(text="⏱ Интервал", callback_data=f"sched_int:{conn_id}")],
            [InlineKeyboardButton(text="🕐 По времени", callback_data=f"sched_times:{conn_id}")],
            [InlineKeyboardButton(text="« Назад", callback_data=f"conn:{conn_id}")],
        ]
    )
    await callback.message.edit_text(
        "⏰ <b>Расписание публикаций</b>\n\n"
        "• <b>Сразу</b> — публиковать как только видео скачано\n"
        "• <b>Интервал</b> — не чаще раза в N минут (растягивает очередь)\n"
        "• <b>По времени</b> — в заданные часы дня",
        reply_markup=kb,
    )
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
    conn_id = int(callback.data.split(":", 1)[1])
    conn = await _set_schedule(
        conn_id, callback.from_user.id, schedule_mode="immediate", interval_minutes=0
    )
    if conn is None:
        await callback.answer("Связка не найдена", show_alert=True)
        return
    await callback.message.edit_text(_card_text(conn), reply_markup=_card_markup(conn))
    await callback.answer("Публикую сразу")


@router.callback_query(F.data.startswith("sched_int:"))
async def sched_int(callback: CallbackQuery, state: FSMContext) -> None:
    conn_id = int(callback.data.split(":", 1)[1])
    await state.update_data(conn_id=conn_id)
    await state.set_state(SchedFlow.waiting_interval)
    await callback.message.answer(
        "Пришли интервал между публикациями в <b>минутах</b> (например <code>120</code> = раз в 2 часа)."
    )
    await callback.answer()


@router.message(SchedFlow.waiting_interval)
async def got_interval(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("Нужно положительное число минут. Попробуй ещё раз.")
        return
    data = await state.get_data()
    conn = await _set_schedule(
        data["conn_id"], message.from_user.id,
        schedule_mode="interval", interval_minutes=int(text),
    )
    await state.clear()
    if conn is None:
        await message.answer("Связка не найдена.")
        return
    await message.answer(_card_text(conn), reply_markup=_card_markup(conn))


@router.callback_query(F.data.startswith("sched_times:"))
async def sched_times(callback: CallbackQuery, state: FSMContext) -> None:
    conn_id = int(callback.data.split(":", 1)[1])
    await state.update_data(conn_id=conn_id)
    await state.set_state(SchedFlow.waiting_times)
    await callback.message.answer(
        "Пришли времена публикаций через запятую в формате ЧЧ:ММ.\n"
        "Можно добавить таймзону.\n\n"
        "Примеры:\n<code>10:00, 15:00, 19:30</code>\n"
        "<code>09:00, 21:00 Europe/Moscow</code>"
    )
    await callback.answer()


@router.message(SchedFlow.waiting_times)
async def got_times(message: Message, state: FSMContext) -> None:
    import re

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
        await message.answer("Не нашёл корректных времён. Формат: <code>10:00, 15:00</code>")
        return
    data = await state.get_data()
    conn = await _set_schedule(
        data["conn_id"], message.from_user.id,
        schedule_mode="times", post_times=sorted(set(times)), tz=tz,
    )
    await state.clear()
    if conn is None:
        await message.answer("Связка не найдена.")
        return
    await message.answer(_card_text(conn), reply_markup=_card_markup(conn))


@router.callback_query(F.data.startswith("conn_delyes:"))
async def do_delete(callback: CallbackQuery) -> None:
    conn_id = int(callback.data.split(":", 1)[1])
    async with get_session() as session:
        conn = await session.scalar(
            select(Connection).where(
                Connection.id == conn_id, Connection.user_id == callback.from_user.id
            )
        )
        if conn is None:
            await callback.answer("Связка не найдена", show_alert=True)
            return
        await session.delete(conn)
    await callback.message.edit_text("🗑 Связка удалена.")
    await callback.answer("Удалено")
