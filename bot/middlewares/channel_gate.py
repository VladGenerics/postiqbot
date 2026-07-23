"""Гейт обязательной подписки на канал."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import get_settings
from bot.db.models import User
from bot.db.session import get_session


async def _is_verified(telegram_id: int) -> bool:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        return bool(user and user.channel_verified)


class ChannelGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        s = get_settings()
        if not s.gate_active:
            return await handler(event, data)

        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if user.id in s.admin_id_set:
            return await handler(event, data)

        if await _is_verified(user.id):
            return await handler(event, data)

        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and event.data == "gate:check":
            return await handler(event, data)

        from bot.handlers.start import send_gate_prompt
        if isinstance(event, Message):
            await send_gate_prompt(event.bot, user.id, event)
        elif isinstance(event, CallbackQuery):
            await event.answer("Сначала подпишитесь на канал 👇", show_alert=True)
        return None
