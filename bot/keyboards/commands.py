"""Меню команд («три полоски») на языке пользователя."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat

from bot.i18n import LANGS, command_descriptions

logger = logging.getLogger("postiqbot.commands")


def bot_commands(lang: str) -> list[BotCommand]:
    """Список команд для set_my_commands на языке lang."""
    return [
        BotCommand(command=cmd, description=desc)
        for cmd, desc in command_descriptions(lang)
    ]


async def set_global_commands(bot: Bot) -> None:
    """Глобальное меню команд: en по умолчанию + перевод по языку клиента."""
    await bot.set_my_commands(bot_commands("en"))
    for lang in LANGS:
        if lang != "en":
            await bot.set_my_commands(bot_commands(lang), language_code=lang)


async def sync_user_commands(bot: Bot, user_id: int, lang: str) -> None:
    """Меню команд в чате user_id — на языке, выбранном в боте."""
    try:
        await bot.set_my_commands(
            bot_commands(lang), scope=BotCommandScopeChat(chat_id=user_id)
        )
    except Exception:  # noqa: BLE001 — меню команд не стоит падения хендлера
        logger.warning("Не смог обновить меню команд для %s", user_id)
