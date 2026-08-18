"""Сообщения «Войти через …»: помним их, чтобы убрать после входа."""
from __future__ import annotations

import logging

from aiogram import Bot

logger = logging.getLogger("postiqbot.login_prompts")

_PROMPTS: dict[tuple[int, str], int] = {}

_MAX_PROMPTS = 5000


async def _delete(bot: Bot, telegram_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=telegram_id, message_id=message_id)
    except Exception:  # noqa: BLE001 — уже удалено / старше 48 ч / чат недоступен
        logger.debug("Не удалил приглашение %s у %s", message_id, telegram_id)


async def remember(bot: Bot, telegram_id: int, platform: str, message_id: int) -> None:
    """Запомнить новое приглашение, погасив предыдущее по этой же платформе."""
    key = (telegram_id, platform)
    previous = _PROMPTS.get(key)
    if previous and previous != message_id:
        await _delete(bot, telegram_id, previous)
    _PROMPTS[key] = message_id
    while len(_PROMPTS) > _MAX_PROMPTS:
        _PROMPTS.pop(next(iter(_PROMPTS)))


async def clear(bot: Bot, telegram_id: int, platform: str) -> None:
    """Убрать приглашение: аккаунт подключён, кнопка «Войти» больше не нужна."""
    message_id = _PROMPTS.pop((telegram_id, platform), None)
    if message_id:
        await _delete(bot, telegram_id, message_id)


def forget(telegram_id: int, platform: str) -> int | None:
    """Забыть приглашение, не удаляя сообщение (для тестов и диагностики)."""
    return _PROMPTS.pop((telegram_id, platform), None)
