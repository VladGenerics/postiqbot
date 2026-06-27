"""Приватный режим (пред-запуск): пока включён — ботом могут пользоваться только разрешённые id (админы)."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import get_settings

_override: bool | None = None


def set_private(value: bool | None) -> None:
    global _override
    _override = value


def is_private() -> bool:
    if _override is not None:
        return _override
    return get_settings().private_mode


class PrivateModeMiddleware(BaseMiddleware):
    """Блокирует не-разрешённых пользователей, пока активен приватный режим."""

    def __init__(self, allowed: set[int]) -> None:
        self.allowed = set(allowed)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if is_private():
            user = data.get("event_from_user")
            if user is None or user.id not in self.allowed:
                text = get_settings().private_message
                try:
                    if isinstance(event, Message):
                        await event.answer(text)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(text, show_alert=True)
                except Exception:  # noqa: BLE001
                    pass
                return None
        return await handler(event, data)
