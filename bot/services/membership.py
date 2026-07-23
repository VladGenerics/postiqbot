"""Живая проверка подписки пользователя на обязательный канал (gate)."""
from __future__ import annotations

import logging

from aiogram import Bot

from bot.config import get_settings

logger = logging.getLogger("postiqbot.gate")

_SUBSCRIBED = {"member", "administrator", "creator"}


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """True, если пользователь состоит в gate_channel. Гейт выключен → всегда True."""
    s = get_settings()
    if not s.gate_active:
        return True
    try:
        member = await bot.get_chat_member(s.gate_channel, user_id)
    except Exception:  # noqa: BLE001 — бот не админ канала / канал недоступен
        logger.warning("get_chat_member failed (user=%s, chat=%s)", user_id, s.gate_channel, exc_info=True)
        return False
    status = getattr(member, "status", None)
    if status in _SUBSCRIBED:
        return True
    return status == "restricted" and getattr(member, "is_member", False)
