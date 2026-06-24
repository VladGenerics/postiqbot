"""Постоянная нижняя клавиатура (reply-кнопки → действия) + команды + язык."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import get_settings
from bot.handlers.accounts import open_connect_tiktok, open_connect_youtube
from bot.handlers.connections import open_connections
from bot.handlers.extras import (
    open_guide,
    open_profile,
    open_referral,
    open_subscription,
    open_support,
)
from bot.handlers.sources import open_add_source
from bot.i18n import labels, set_user_lang, t, user_lang
from bot.keyboards.menus import main_reply_kb

router = Router(name="navigation")


@router.message(F.text.in_(labels("youtube")))
async def nav_youtube(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_connect_youtube(message, message.from_user.id)


@router.message(F.text.in_(labels("tiktok")))
async def nav_tiktok(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_connect_tiktok(message, message.from_user.id)


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


@router.message(F.text.in_(labels("guide")))
async def nav_guide(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_guide(message, message.from_user.id)


@router.message(F.text.in_(labels("referral")))
async def nav_referral(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await open_referral(message, bot, message.from_user.id)


@router.message(F.text.in_(labels("support")))
async def nav_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_support(message, state, message.from_user.id)


@router.message(F.text.in_(labels("lang")))
async def nav_lang(message: Message, state: FSMContext) -> None:
    await state.clear()
    new = "en" if (await user_lang(message.from_user.id)) == "ru" else "ru"
    await set_user_lang(message.from_user.id, new)
    await message.answer(t("lang_switched", new), reply_markup=main_reply_kb(new))


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
    domain = get_settings().public_domain or "34.34.114.44.sslip.io"
    await message.answer(f"🔐 Privacy Policy:\nhttps://{domain}/privacy")


@router.message(Command("terms"))
async def cmd_terms(message: Message) -> None:
    domain = get_settings().public_domain or "34.34.114.44.sslip.io"
    await message.answer(f"📄 Terms of Service:\nhttps://{domain}/terms")
