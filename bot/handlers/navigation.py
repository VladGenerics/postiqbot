"""Обработка постоянной нижней клавиатуры (reply-кнопки → действия)."""
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
    open_referral,
    open_subscription,
    open_support,
)
from bot.handlers.sources import open_add_source
from bot.keyboards.menus import (
    BTN_CONNECTIONS,
    BTN_GUIDE,
    BTN_REFERRAL,
    BTN_SOURCE,
    BTN_SUPPORT,
    BTN_TARIFF,
    BTN_TIKTOK,
    BTN_YOUTUBE,
)

router = Router(name="navigation")


@router.message(F.text == BTN_YOUTUBE)
async def nav_youtube(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_connect_youtube(message, message.from_user.id)


@router.message(F.text == BTN_TIKTOK)
async def nav_tiktok(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_connect_tiktok(message, message.from_user.id)


@router.message(F.text == BTN_SOURCE)
async def nav_source(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_add_source(message, message.from_user.id, state)


@router.message(F.text == BTN_CONNECTIONS)
async def nav_connections(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_connections(message, message.from_user.id)


@router.message(F.text == BTN_TARIFF)
async def nav_tariff(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_subscription(message, message.from_user.id)


@router.message(F.text == BTN_GUIDE)
async def nav_guide(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_guide(message)


@router.message(F.text == BTN_REFERRAL)
async def nav_referral(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await open_referral(message, bot, message.from_user.id)


@router.message(F.text == BTN_SUPPORT)
async def nav_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_support(message, state)


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
    await open_guide(message)


@router.message(Command("referral"))
async def cmd_referral(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await open_referral(message, bot, message.from_user.id)


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await open_support(message, state)


@router.message(Command("policy"))
async def cmd_policy(message: Message) -> None:
    domain = get_settings().public_domain or "34.34.114.44.sslip.io"
    await message.answer(
        f"🔐 Политика конфиденциальности:\nhttps://{domain}/privacy"
    )


@router.message(Command("terms"))
async def cmd_terms(message: Message) -> None:
    domain = get_settings().public_domain or "34.34.114.44.sslip.io"
    await message.answer(
        f"📄 Пользовательское соглашение:\nhttps://{domain}/terms"
    )
