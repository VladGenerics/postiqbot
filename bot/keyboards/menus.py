"""Клавиатуры бота."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    """Главное меню."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="🔗 Подключить YouTube", callback_data="connect_youtube"
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="📡 Добавить источник", callback_data="add_source"
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="📋 Мои подключения", callback_data="my_connections"
        )
    )
    return kb.as_markup()
