"""Подключение YouTube-аккаунта клиента через OAuth."""
from __future__ import annotations

import logging

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
from bot.i18n import t, user_lang
from bot.services.crypto import decrypt
from bot.services.oauth_state import encode_simple_state, encode_state
from bot.services.projects import ensure_shared_project, pick_project
from bot.services.subscription import can_add_account
from bot.services.tiktok_oauth import build_auth_url as tiktok_auth_url
from bot.ui import send_with_icon
from bot.services.youtube_oauth import build_auth_url

router = Router(name="accounts")

logger = logging.getLogger("postiqbot.accounts")


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


async def open_connect_youtube(message: Message, telegram_id: int) -> None:
    settings = get_settings()
    await ensure_user(telegram_id)
    lang = await user_lang(telegram_id)
    limit = await _account_limit_reached(telegram_id)
    if limit is not None:
        await message.answer(t("limit_accounts", lang, limit=limit))
        return
    async with get_session() as session:
        await ensure_shared_project(session)
        await session.flush()
        project = await pick_project(session, owner_telegram_id=telegram_id)
        if project is None:
            await message.answer(t("acc_no_project", lang))
            return
        client_id = project.client_id
        client_secret = decrypt(project.client_secret_enc)
        project_id, project_name = project.id, project.name
        state = encode_state(telegram_id, project.id)

    auth_url = build_auth_url(client_id, client_secret, settings.oauth_redirect_uri, state)
    logger.info(
        "OAuth YouTube: user=%s проект #%d (%s) client_id=%s… redirect_uri=%s",
        telegram_id, project_id, project_name, client_id[:20], settings.oauth_redirect_uri,
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("btn_login_google", lang), url=auth_url)]]
    )
    await message.answer(t("oauth_youtube", lang), reply_markup=kb)


async def open_connect_tiktok(message: Message, telegram_id: int) -> None:
    settings = get_settings()
    lang = await user_lang(telegram_id)
    if not settings.tiktok_client_key:
        await message.answer(t("acc_tiktok_off", lang))
        return
    await ensure_user(telegram_id)
    limit = await _account_limit_reached(telegram_id)
    if limit is not None:
        await message.answer(t("limit_accounts", lang, limit=limit))
        return
    auth_url = tiktok_auth_url(encode_simple_state(telegram_id))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("btn_login_tiktok", lang), url=auth_url)]]
    )
    await message.answer(t("oauth_tiktok", lang), reply_markup=kb)


async def open_connect_menu(message: Message, telegram_id: int) -> None:
    """Компактное подключение: выбор платформы инлайн-кнопками."""
    lang = await user_lang(telegram_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("youtube", lang), callback_data="connect_youtube")],
        [InlineKeyboardButton(text=t("tiktok", lang), callback_data="connect_tiktok")],
    ])
    await send_with_icon(message, "connect", t("choose_platform", lang), reply_markup=kb, lang=lang)


@router.callback_query(F.data == "connect_youtube")
async def connect_youtube(callback: CallbackQuery) -> None:
    await open_connect_youtube(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "connect_tiktok")
async def connect_tiktok(callback: CallbackQuery) -> None:
    await open_connect_tiktok(callback.message, callback.from_user.id)
    await callback.answer()
