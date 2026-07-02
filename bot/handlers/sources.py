"""Подключение исходного канала (за которым следим) и создание связки."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from bot.db.models import Connection, PublishAccount, SourceChannel
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services.source_resolver import resolve_source_channel
from bot.ui import send_with_icon

router = Router(name="sources")


class SourceFlow(StatesGroup):
    waiting_link = State()
    waiting_account = State()


async def _user_accounts(telegram_id: int) -> list[PublishAccount]:
    async with get_session() as session:
        return list(
            await session.scalars(
                select(PublishAccount).where(PublishAccount.user_id == telegram_id)
            )
        )


async def _get_or_create_source(platform: str, channel_id: str, title: str) -> int:
    """Вернуть id source_channel (создать при отсутствии)."""
    async with get_session() as session:
        stmt = (
            insert(SourceChannel)
            .values(platform=platform, channel_id=channel_id, channel_title=title)
            .on_conflict_do_update(
                constraint="uq_source_channel", set_={"channel_title": title}
            )
            .returning(SourceChannel.id)
        )
        return (await session.execute(stmt)).scalar_one()


async def _create_connection(
    telegram_id: int, publish_account_id: int, source_id: int
) -> bool:
    """Создать связку. False — если такая уже существует."""
    async with get_session() as session:
        stmt = (
            insert(Connection)
            .values(
                user_id=telegram_id,
                publish_account_id=publish_account_id,
                source_channel_id=source_id,
            )
            .on_conflict_do_nothing(constraint="uq_connection")
            .returning(Connection.id)
        )
        return (await session.execute(stmt)).scalar_one_or_none() is not None


async def open_add_source(message: Message, user_id: int, state: FSMContext) -> None:
    from bot.i18n import t, user_lang

    lang = await user_lang(user_id)
    accounts = await _user_accounts(user_id)
    if not accounts:
        await send_with_icon(message, "source", t("source_need_account", lang), lang=lang)
        return
    await state.set_state(SourceFlow.waiting_link)
    await send_with_icon(message, "source", t("source_prompt", lang), lang=lang)


@router.callback_query(F.data == "add_source")
async def add_source(callback: CallbackQuery, state: FSMContext) -> None:
    await open_add_source(callback.message, callback.from_user.id, state)
    await callback.answer()


@router.message(SourceFlow.waiting_link)
async def got_link(message: Message, state: FSMContext) -> None:
    lang = await user_lang(message.from_user.id)
    resolved = await resolve_source_channel(message.text or "")
    if resolved is None:
        await message.answer(t("src_bad_link", lang))
        return
    platform, channel_id, title = resolved
    source_id = await _get_or_create_source(platform, channel_id, title)

    accounts = await _user_accounts(message.from_user.id)
    if len(accounts) == 1:
        await _finish(message, state, accounts[0].id, source_id, title)
        return

    await state.update_data(source_id=source_id, source_title=title)
    await state.set_state(SourceFlow.waiting_account)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=a.channel_title, callback_data=f"src_dest:{a.id}"
                )
            ]
            for a in accounts
        ]
    )
    await message.answer(t("src_choose_dest", lang, title=title), reply_markup=kb)


@router.callback_query(SourceFlow.waiting_account, F.data.startswith("src_dest:"))
async def chose_account(callback: CallbackQuery, state: FSMContext) -> None:
    account_id = int(callback.data.split(":", 1)[1])
    lang = await user_lang(callback.from_user.id)
    data = await state.get_data()
    source_id = data["source_id"]
    title = data.get("source_title", t("src_default_title", lang))
    await _finish(callback.message, state, account_id, source_id, title)
    await callback.answer()


async def _finish(
    message: Message,
    state: FSMContext,
    account_id: int,
    source_id: int,
    title: str,
) -> None:
    lang = await user_lang(message.chat.id)
    created = await _create_connection(message.chat.id, account_id, source_id)
    await state.clear()
    if created:
        await message.answer(t("src_connected", lang, title=title))
    else:
        await message.answer(t("src_exists", lang))
