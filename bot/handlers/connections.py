"""Управление связками клиента: список, пауза/возобновление, приватность, удаление."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from bot.db.models import Connection
from bot.db.session import get_session

router = Router(name="connections")

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
