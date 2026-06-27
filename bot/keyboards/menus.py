"""Клавиатуры бота: постоянная нижняя (reply) навигация на нужном языке."""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.i18n import label


def main_reply_kb(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Постоянная нижняя клавиатура — главное меню на языке lang."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label("connect", lang)), KeyboardButton(text=label("source", lang))],
            [KeyboardButton(text=label("connections", lang)), KeyboardButton(text=label("profile", lang))],
            [KeyboardButton(text=label("tariff", lang)), KeyboardButton(text=label("more", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
