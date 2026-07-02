"""Баннеры-иконки над сообщениями меню."""
from __future__ import annotations

import os

from aiogram.types import (
    FSInputFile,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
    ReplyKeyboardMarkup,
)

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")

ICONS: dict[str, str] = {
    "start": "banner_start.png",
    "connect": "banner_connect.png",
    "source": "banner_source.png",
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


_FILE_IDS: dict[str, str] = {}


def _banner_media(icon: str):
    """file_id (если уже заливали) либо файл с диска."""
    return _FILE_IDS.get(icon) or FSInputFile(os.path.join(_ASSETS, ICONS[icon]))


def _remember(icon: str, message) -> None:
    photo = getattr(message, "photo", None)
    if photo:
        _FILE_IDS[icon] = photo[-1].file_id


async def show_screen(
    message: Message,
    icon: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    edit: bool = False,
) -> Message:
    """Отрисовать экран меню (баннер + подпись + inline-кнопки)."""
    media = _banner_media(icon)
    if edit:
        try:
            m = await message.edit_media(
                InputMediaPhoto(media=media, caption=caption, parse_mode="HTML"),
                reply_markup=reply_markup,
            )
            if hasattr(m, "photo"):
                _remember(icon, m)
            return m
        except Exception:  # noqa: BLE001 — не смогли отредактировать, отправим новое
            pass
    m = await message.answer_photo(media, caption=caption, reply_markup=reply_markup)
    _remember(icon, m)
    return m
