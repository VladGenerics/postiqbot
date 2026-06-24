"""Обработка постоянной нижней клавиатуры (reply-кнопки → действия)."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

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
