"""Подключение YouTube-аккаунта клиента через OAuth."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import func, select

from bot.config import get_settings
from bot.db.models import PublishAccount
from bot.db.session import get_session
from bot.handlers.start import ensure_user
from bot.services.crypto import decrypt
from bot.services.oauth_state import encode_simple_state, encode_state
from bot.services.projects import ensure_shared_project, pick_project
from bot.services.subscription import can_add_account
from bot.services.tiktok_oauth import build_auth_url as tiktok_auth_url
from bot.services.youtube_oauth import build_auth_url

router = Router(name="accounts")


async def _account_limit_reached(telegram_id: int) -> int | None:
    """Если лимит аккаунтов достигнут — вернуть лимит, иначе None."""
    async with get_session() as session:
        count = await session.scalar(
            select(func.count()).select_from(PublishAccount).where(
                PublishAccount.user_id == telegram_id
            )
        )
    allowed, limit = await can_add_account(telegram_id, count or 0)
    return None if allowed else limit


_LIMIT_MSG = (
    "⚠️ На твоём тарифе можно подключить до <b>{limit}</b> аккаунтов. "
    "Удали лишний или оформи тариф побольше («💳 Тарифы»)."
)


async def open_connect_youtube(message: Message, telegram_id: int) -> None:
    settings = get_settings()
    await ensure_user(telegram_id)
    limit = await _account_limit_reached(telegram_id)
    if limit is not None:
        await message.answer(_LIMIT_MSG.format(limit=limit))
        return
    async with get_session() as session:
        await ensure_shared_project(session)
        await session.flush()
        project = await pick_project(session, owner_telegram_id=telegram_id)
        if project is None:
            await message.answer(
                "⚠️ Нет доступных Google-проектов в пуле. "
                "Админу нужно добавить проект командой /addproject."
            )
            return
        client_id = project.client_id
        client_secret = decrypt(project.client_secret_enc)
        state = encode_state(telegram_id, project.id)

    auth_url = build_auth_url(client_id, client_secret, settings.oauth_redirect_uri, state)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔓 Войти через Google", url=auth_url)]]
    )
    await message.answer(
        "Нажми кнопку ниже и разреши доступ к своему YouTube-каналу.\n"
        "После подтверждения я пришлю сообщение, что канал подключён.\n\n"
        "<i>Ссылка действует 10 минут.</i>",
        reply_markup=kb,
    )


async def open_connect_tiktok(message: Message, telegram_id: int) -> None:
    settings = get_settings()
    if not settings.tiktok_client_key:
        await message.answer("⚠️ TikTok пока не настроен на сервере.")
        return
    await ensure_user(telegram_id)
    limit = await _account_limit_reached(telegram_id)
    if limit is not None:
        await message.answer(_LIMIT_MSG.format(limit=limit))
        return
    auth_url = tiktok_auth_url(encode_simple_state(telegram_id))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔓 Войти через TikTok", url=auth_url)]]
    )
    await message.answer(
        "Нажми кнопку ниже и разреши доступ к своему TikTok-аккаунту.\n"
        "После подтверждения я пришлю сообщение, что аккаунт подключён.\n\n"
        "<i>Ссылка действует 10 минут.</i>",
        reply_markup=kb,
    )


@router.callback_query(F.data == "connect_youtube")
async def connect_youtube(callback: CallbackQuery) -> None:
    await open_connect_youtube(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "connect_tiktok")
async def connect_tiktok(callback: CallbackQuery) -> None:
    await open_connect_tiktok(callback.message, callback.from_user.id)
    await callback.answer()
