"""Хендлер /start — регистрация, гейт подписки на канал и главное меню."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)
from sqlalchemy.dialects.postgresql import insert

from bot.config import get_settings
from bot.db.models import User
from bot.db.session import get_session
from bot.i18n import t, user_lang

router = Router(name="start")


async def ensure_user(telegram_id: int, referred_by: int | None = None) -> None:
    """Зарегистрировать пользователя, если его ещё нет (идемпотентно)."""
    settings = get_settings()
    trial_until = (
        None if settings.gate_active
        else datetime.now(timezone.utc) + timedelta(days=settings.trial_days)
    )
    async with get_session() as session:
        stmt = (
            insert(User)
            .values(
                telegram_id=telegram_id,
                trial_until=trial_until,
                referred_by=referred_by,
                tier_accounts=settings.trial_accounts,
                tier_videos=settings.trial_videos,
            )
            .on_conflict_do_nothing(index_elements=["telegram_id"])
        )
        await session.execute(stmt)


async def grant_trial(telegram_id: int) -> None:
    """Начислить триал, если у пользователя ещё нет никакого доступа."""
    settings = get_settings()
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if user and user.trial_until is None and user.subscription_until is None:
            user.trial_until = datetime.now(timezone.utc) + timedelta(days=settings.trial_days)


async def _is_verified(telegram_id: int) -> bool:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        return bool(user and user.channel_verified)


def _gate_kb(lang: str) -> InlineKeyboardMarkup:
    s = get_settings()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("gate_btn_join", lang), url=s.gate_link)],
        [InlineKeyboardButton(text=t("gate_btn_check", lang), callback_data="gate:check")],
    ])


async def send_gate_prompt(bot: Bot, user_id: int, message: Message | None = None) -> None:
    """Показать приглашение подписаться на канал (с двумя кнопками)."""
    lang = await user_lang(user_id)
    kb = _gate_kb(lang)
    if message is not None:
        await message.answer(t("gate_prompt", lang), reply_markup=kb)
    else:
        await bot.send_message(user_id, t("gate_prompt", lang), reply_markup=kb)


async def _parse_referrer(command: CommandObject, self_id: int) -> int | None:
    """Из deep-link /start ref_<id> вернуть валидного существующего реферера."""
    arg = (command.args or "").strip()
    if not arg.startswith("ref_"):
        return None
    ref = arg[4:]
    if not ref.isdigit() or int(ref) == self_id:
        return None
    referrer_id = int(ref)
    async with get_session() as session:
        exists = await session.get(User, referrer_id)
    return referrer_id if exists else None


async def _open_main(message: Message, user_id: int) -> None:
    from bot.handlers.menu import open_menu

    lang = await user_lang(user_id)
    await message.answer(t("welcome", lang), reply_markup=ReplyKeyboardRemove())
    await open_menu(message, user_id, "root")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    referred_by = await _parse_referrer(command, message.from_user.id)
    await ensure_user(message.from_user.id, referred_by=referred_by)

    s = get_settings()
    if s.gate_active and message.from_user.id not in s.admin_id_set:
        if not await _is_verified(message.from_user.id):
            await send_gate_prompt(message.bot, message.from_user.id, message)
            return

    await _open_main(message, message.from_user.id)


@router.callback_query(F.data == "gate:check")
async def gate_check(callback: CallbackQuery) -> None:
    """Проверить подписку. Если подтверждена — начислить триал и открыть меню."""
    from bot.services.membership import is_subscribed

    uid = callback.from_user.id
    lang = await user_lang(uid)
    if not await is_subscribed(callback.bot, uid):
        await callback.answer(t("gate_fail", lang), show_alert=True)
        return

    async with get_session() as session:
        user = await session.get(User, uid)
        if user:
            user.channel_verified = True
    await grant_trial(uid)

    await callback.answer()
    await callback.message.answer(t("gate_ok", lang), reply_markup=ReplyKeyboardRemove())
    await _open_main(callback.message, uid)
