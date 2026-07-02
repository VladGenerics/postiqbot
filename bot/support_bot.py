"""Отдельный бот поддержки: чат «пользователь ↔ агенты» через форум-темы."""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy import select

from bot.config import get_settings
from bot.db.models import SupportMessage, SupportThread
from bot.db.session import get_session
from bot.i18n import t, user_lang

logger = logging.getLogger("postiqbot.support")

router = Router(name="support_bot")

_username: str | None = None


def set_support_username(username: str) -> None:
    global _username
    _username = username


def support_username() -> str:
    return _username or get_settings().support_bot_username


@router.message(Command("chatid"))
async def chat_id(message: Message) -> None:
    """Показать id чата/темы — чтобы узнать SUPPORT_GROUP_ID."""
    thread = f"\nthread_id: <code>{message.message_thread_id}</code>" if message.message_thread_id else ""
    await message.reply(
        f"chat_id: <code>{message.chat.id}</code>{thread}", parse_mode="HTML"
    )


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start(message: Message) -> None:
    lang = await user_lang(message.from_user.id)
    await message.answer(t("sup_greeting", lang))


async def _topic_for(bot: Bot, user_id: int, title: str) -> int | None:
    """Вернуть topic_id темы пользователя (создать при отсутствии)."""
    async with get_session() as session:
        thr = await session.get(SupportThread, user_id)
        if thr:
            return thr.topic_id
    gid = get_settings().support_group_id
    if not gid:
        return None
    try:
        topic = await bot.create_forum_topic(chat_id=gid, name=title[:120])
    except Exception:  # noqa: BLE001 — группа не форум / бот не админ / нет прав
        logger.exception("Не смог создать тему поддержки для user=%s", user_id)
        return None
    tid = topic.message_thread_id
    async with get_session() as session:
        session.add(SupportThread(user_id=user_id, topic_id=tid))
    return tid


@router.message(F.chat.type == ChatType.PRIVATE)
async def from_user(message: Message, bot: Bot) -> None:
    """Сообщение пользователя → копируем в его тему в группе поддержки."""
    u = message.from_user
    lang = await user_lang(u.id)
    title = f"@{u.username} · {u.id}" if u.username else f"{u.full_name} · {u.id}"
    tid = await _topic_for(bot, u.id, title)
    if tid is None:
        await message.answer(t("sup_unavailable", lang))
        return
    gid = get_settings().support_group_id
    try:
        await bot.copy_message(
            chat_id=gid,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            message_thread_id=tid,
        )
    except Exception:  # noqa: BLE001 — тема могла быть удалена — пересоздадим
        logger.warning("copy в тему %s не удался, пересоздаю", tid)
        async with get_session() as session:
            thr = await session.get(SupportThread, u.id)
            if thr:
                await session.delete(thr)
        tid = await _topic_for(bot, u.id, title)
        if tid is None:
            await message.answer(t("sup_unavailable", lang))
            return
        await bot.copy_message(
            chat_id=gid, from_chat_id=message.chat.id,
            message_id=message.message_id, message_thread_id=tid,
        )
    async with get_session() as session:
        session.add(SupportMessage(
            user_id=u.id, admin_id=None,
            text=message.text or message.caption or "[media]",
            photo_file_id=message.photo[-1].file_id if message.photo else None,
        ))


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.message_thread_id.is_not(None),
)
async def from_agent(message: Message, bot: Bot) -> None:
    """Ответ агента в теме → копируем пользователю в личку."""
    if message.chat.id != get_settings().support_group_id:
        return
    if not message.from_user or message.from_user.is_bot:
        return
    async with get_session() as session:
        thr = await session.scalar(
            select(SupportThread).where(SupportThread.topic_id == message.message_thread_id)
        )
    if thr is None:
        return
    lang = await user_lang(message.from_user.id)
    try:
        await bot.copy_message(
            chat_id=thr.user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except Exception:  # noqa: BLE001 — юзер заблокировал / не начинал чат
        await message.reply(t("sup_undelivered", lang))
        return
    async with get_session() as session:
        session.add(SupportMessage(
            user_id=thr.user_id, admin_id=message.from_user.id,
            text=message.text or message.caption or "[media]",
            photo_file_id=message.photo[-1].file_id if message.photo else None,
        ))


def build_support_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp
