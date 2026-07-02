"""Баннеры-иконки над сообщениями меню."""
from __future__ import annotations

import os

from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")

ICONS: dict[str, str] = {
    "start": "banner_start.png",
    "profile": "banner_profile.png",
    "tariffs": "banner_tariffs.png",
    "connections": "banner_connections.png",
    "guide": "banner_guide.png",
    "referral": "banner_referral.png",
    "documents": "banner_documents.png",
    "support": "banner_support.png",
    "lang": "banner_lang.png",
    "more": "banner_more.png",
}

_CAPTION_LIMIT = 1024


async def send_with_icon(
    message: Message,
    icon: str,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
) -> None:
    """Отправить баннер раздела + текст (в подписи, если помещается)."""
    photo = FSInputFile(os.path.join(_ASSETS, ICONS[icon]))
    if len(text) <= _CAPTION_LIMIT:
        await message.answer_photo(photo, caption=text, reply_markup=reply_markup)
    else:
        await message.answer_photo(photo)
        await message.answer(text, reply_markup=reply_markup)
