"""Клавиатуры бота: постоянная нижняя (reply) навигация + инлайн-меню."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

BTN_YOUTUBE = "🔗 Подключить YouTube"
BTN_TIKTOK = "🎵 Подключить TikTok"
BTN_SOURCE = "📡 Добавить источник"
BTN_CONNECTIONS = "📋 Мои подключения"
BTN_TARIFF = "💳 Тарифы"
BTN_GUIDE = "📖 Как пользоваться"
BTN_REFERRAL = "🎁 Пригласить друга"
BTN_SUPPORT = "✍️ Поддержка"


def main_reply_kb() -> ReplyKeyboardMarkup:
    """Постоянная нижняя клавиатура — главное меню."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_YOUTUBE), KeyboardButton(text=BTN_TIKTOK)],
            [KeyboardButton(text=BTN_SOURCE), KeyboardButton(text=BTN_CONNECTIONS)],
            [KeyboardButton(text=BTN_TARIFF), KeyboardButton(text=BTN_GUIDE)],
            [KeyboardButton(text=BTN_REFERRAL), KeyboardButton(text=BTN_SUPPORT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выбери действие в меню ниже…",
    )


def main_menu() -> InlineKeyboardMarkup:
    """Инлайн-меню (используется, где нужно прямо в сообщении)."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text=BTN_YOUTUBE, callback_data="connect_youtube"),
        InlineKeyboardButton(text=BTN_TIKTOK, callback_data="connect_tiktok"),
    )
    kb.row(
        InlineKeyboardButton(text=BTN_SOURCE, callback_data="add_source"),
        InlineKeyboardButton(text=BTN_CONNECTIONS, callback_data="my_connections"),
    )
    kb.row(
        InlineKeyboardButton(text=BTN_TARIFF, callback_data="subscription"),
        InlineKeyboardButton(text=BTN_GUIDE, callback_data="guide"),
    )
    kb.row(
        InlineKeyboardButton(text=BTN_REFERRAL, callback_data="referral"),
        InlineKeyboardButton(text=BTN_SUPPORT, callback_data="support"),
    )
    return kb.as_markup()
