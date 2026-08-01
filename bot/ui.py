"""Баннеры-иконки над сообщениями меню."""
from __future__ import annotations

import asyncio
import os

from aiogram.fsm.context import FSMContext
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    LinkPreviewOptions,
    Message,
    ReplyKeyboardMarkup,
)

_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

_AUTODEL_TASKS: set[asyncio.Task] = set()


def autodelete(message: Message, delay: float = 5.0) -> None:
    """Удалить сообщение через delay секунд (fire-and-forget)."""
    async def _later() -> None:
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except Exception:  # noqa: BLE001 — уже удалено / нет прав
            pass

    task = asyncio.create_task(_later())
    _AUTODEL_TASKS.add(task)
    task.add_done_callback(_AUTODEL_TASKS.discard)

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
) -> Message:
    """Отправить баннер раздела + текст (в подписи, если помещается)."""
    photo = _banner_media(icon, lang)
    if len(text) <= _CAPTION_LIMIT:
        m = await message.answer_photo(photo, caption=text, reply_markup=reply_markup)
        _remember(icon, lang, m)
        return m
    m = await message.answer_photo(photo)
    _remember(icon, lang, m)
    return await message.answer(text, reply_markup=reply_markup)


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


_PROMPT_KEY = "_prompt_id"
_ANCHOR_KEY = "_anchor_id"


async def ask(
    message: Message,
    state: FSMContext,
    text: str,
    lang: str = "ru",
    *,
    cancel_data: str = "ask_cancel",
    cancel_text: str = "« Отмена",
) -> None:
    """Спросить текст: отправить приглашение с «Отмена» и запомнить, что убрать."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cancel_text, callback_data=cancel_data)]
    ])
    prompt = await message.answer(text, reply_markup=kb, link_preview_options=_NO_PREVIEW)
    await state.update_data(**{_PROMPT_KEY: prompt.message_id, _ANCHOR_KEY: message.message_id})


async def cleanup_ask(message: Message, state: FSMContext) -> None:
    """Убрать приглашение и ответ пользователя — вызывать в message-хендлере FSM."""
    data = await state.get_data()
    prompt_id = data.get(_PROMPT_KEY)
    if prompt_id:
        try:
            await message.bot.delete_message(message.chat.id, prompt_id)
        except Exception:  # noqa: BLE001 — уже удалено / старше 48ч / нет прав
            pass
    try:
        await message.delete()
    except Exception:  # noqa: BLE001 — нет прав администратора в чате
        pass


async def remember_prompt(state: FSMContext, prompt: Message) -> None:
    """Запомнить уже отправленное приглашение (когда его шлёт send_with_icon)."""
    await state.update_data(**{_PROMPT_KEY: prompt.message_id})


async def edit_anchor(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """Вписать результат в окно, из которого начинали ввод."""
    data = await state.get_data()
    anchor_id = data.get(_ANCHOR_KEY)
    if not anchor_id:
        return False
    for edit in ("edit_message_caption", "edit_message_text"):
        try:
            fn = getattr(message.bot, edit)
            kwargs = {"caption" if "caption" in edit else "text": text}
            await fn(chat_id=message.chat.id, message_id=anchor_id,
                     reply_markup=reply_markup, **kwargs)
            return True
        except Exception:  # noqa: BLE001 — не тот тип сообщения либо правка невозможна
            continue
    return False
