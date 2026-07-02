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
_FALLBACK_LANG = "ru"

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

_FILE_IDS: dict[str, str] = {}


def _banner_path(icon: str, lang: str) -> str:
    """Путь к баннеру для языка; если EN-версии нет — русский запасной."""
    fname = ICONS[icon]
    p = os.path.join(_ASSETS, lang, fname)
    if os.path.exists(p):
        return p
    return os.path.join(_ASSETS, _FALLBACK_LANG, fname)


def _banner_media(icon: str, lang: str):
    """file_id (если уже заливали) либо файл с диска."""
    path = _banner_path(icon, lang)
    return _FILE_IDS.get(path) or FSInputFile(path)


def _remember(icon: str, lang: str, message) -> None:
    photo = getattr(message, "photo", None)
    if photo:
        _FILE_IDS[_banner_path(icon, lang)] = photo[-1].file_id


async def send_with_icon(
    message: Message,
    icon: str,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
    lang: str = "ru",
) -> None:
    """Отправить баннер раздела + текст (в подписи, если помещается)."""
    photo = _banner_media(icon, lang)
    if len(text) <= _CAPTION_LIMIT:
        m = await message.answer_photo(photo, caption=text, reply_markup=reply_markup)
    else:
        m = await message.answer_photo(photo)
        await message.answer(text, reply_markup=reply_markup)
    _remember(icon, lang, m)


async def show_screen(
    message: Message,
    icon: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    edit: bool = False,
    lang: str = "ru",
) -> Message:
    """Отрисовать экран меню (баннер + подпись + inline-кнопки)."""
    media = _banner_media(icon, lang)
    if edit:
        try:
            m = await message.edit_media(
                InputMediaPhoto(media=media, caption=caption, parse_mode="HTML"),
                reply_markup=reply_markup,
            )
            if hasattr(m, "photo"):
                _remember(icon, lang, m)
            return m
        except Exception:  # noqa: BLE001 — не смогли отредактировать, отправим новое
            pass
    m = await message.answer_photo(media, caption=caption, reply_markup=reply_markup)
    _remember(icon, lang, m)
    return m
