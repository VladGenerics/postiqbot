"""Постоянная нижняя клавиатура (reply-кнопки → действия) + команды + язык."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import get_settings
from bot.handlers.accounts import open_connect_menu
from bot.handlers.connections import open_connections
from bot.handlers.extras import (
    open_documents,
    open_guide,
    open_profile,
    open_referral,
    open_subscription,
    open_support,
)
from bot.handlers.sources import open_add_source
from bot.i18n import label, labels, set_user_lang, t, user_lang
from bot.keyboards.menus import main_reply_kb

router = Router(name="navigation")


@router.message(F.text.in_(labels("connect")))
async def nav_connect(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_connect_menu(message, message.from_user.id)


@router.message(F.text.in_(labels("source")))
async def nav_source(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_add_source(message, message.from_user.id, state)


@router.message(F.text.in_(labels("connections")))
async def nav_connections(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_connections(message, message.from_user.id)


@router.message(F.text.in_(labels("profile")))
async def nav_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_profile(message, message.from_user.id)


@router.message(F.text.in_(labels("tariff")))
async def nav_tariff(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_subscription(message, message.from_user.id)


@router.message(F.text.in_(labels("more")))
async def nav_more(message: Message, state: FSMContext) -> None:
    """Подменю «Ещё» — второстепенные разделы инлайн-кнопками."""
    await state.clear()
    lang = await user_lang(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label("guide", lang), callback_data="guide")],
        [InlineKeyboardButton(text=label("referral", lang), callback_data="referral")],
        [InlineKeyboardButton(text=label("documents", lang), callback_data="documents")],
        [InlineKeyboardButton(text=label("support", lang), callback_data="support")],
        [InlineKeyboardButton(text=label("lang", lang), callback_data="toggle_lang")],
    ])
    await message.answer(t("more_title", lang), reply_markup=kb)


@router.callback_query(F.data == "toggle_lang")
async def cb_toggle_lang(callback) -> None:
    new = "en" if (await user_lang(callback.from_user.id)) == "ru" else "ru"
    await set_user_lang(callback.from_user.id, new)
    await callback.message.answer(t("lang_switched", new), reply_markup=main_reply_kb(new))
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_profile(message, message.from_user.id)


@router.message(Command("tariffs"))
async def cmd_tariffs(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_subscription(message, message.from_user.id)


@router.message(Command("connections"))
async def cmd_connections(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_connections(message, message.from_user.id)


@router.message(Command("guide"))
async def cmd_guide(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_guide(message, message.from_user.id)


@router.message(Command("referral"))
async def cmd_referral(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await open_referral(message, bot, message.from_user.id)


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_support(message, state, message.from_user.id)


@router.message(Command("policy"))
async def cmd_policy(message: Message) -> None:
    await message.answer(f"🔐 Политика конфиденциальности:\n{get_settings().privacy_url}")


@router.message(Command("terms"))
async def cmd_terms(message: Message) -> None:
    await message.answer(f"📄 Пользовательское соглашение:\n{get_settings().terms_url}")


@router.message(Command("docs"))
async def cmd_docs(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_documents(message, message.from_user.id)
