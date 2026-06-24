"""Гайд, подписка (Telegram Stars) и поддержка."""
from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy import func, select

from bot.config import get_settings
from bot.db.models import User
from bot.db.session import get_session
from bot.handlers.start import ensure_user
from bot.services.subscription import grant_subscription, status_text

logger = logging.getLogger("postiqbot.extras")

router = Router(name="extras")


_GUIDE = (
    "📖 <b>Как пользоваться PostiqBot</b>\n\n"
    "Бот автоматически забирает новые видео с канала-источника и публикует их "
    "на твой канал (YouTube или TikTok) по расписанию.\n\n"
    "<b>1. Подключи свой канал</b>\n"
    "«🔗 Подключить YouTube» или «🎵 Подключить TikTok» — вход через официальный "
    "OAuth. Это куда бот будет публиковать.\n\n"
    "<b>2. Добавь источник</b>\n"
    "«📡 Добавить источник» → пришли ссылку на канал (YouTube @handle или "
    "ссылку на профиль TikTok). Бот начнёт следить за новыми видео.\n\n"
    "<b>3. Настрой связку</b>\n"
    "«📋 Мои подключения» → выбери связку:\n"
    "• ⏰ <b>Расписание</b> — сразу / интервал / по времени\n"
    "• 🖼 <b>Оверлей</b> — картинка или GIF поверх видео (с превью)\n"
    "• 👁 <b>Доступ</b> — для YouTube: приватное/по ссылке/публичное\n"
    "• ⏸ пауза / 🗑 удаление\n\n"
    "<b>Что важно знать</b>\n"
    "• Бот публикует только <b>новые</b> видео (старые не заливает).\n"
    "• TikTok-публикация приходит в «черновики/инбокс» — финально публикуешь сам.\n"
    "• Видео заливаются как <b>private</b> по умолчанию (YouTube) — проверь перед открытием.\n\n"
    "<b>Доступ</b>\n"
    "Первые дни — бесплатный триал. Дальше — подписка («💳 Подписка»).\n"
    "Вопросы — «✍️ Поддержка»."
)


@router.callback_query(F.data == "guide")
async def show_guide(callback: CallbackQuery) -> None:
    await callback.message.answer(_GUIDE)
    await callback.answer()


@router.callback_query(F.data == "subscription")
async def subscription_menu(callback: CallbackQuery) -> None:
    await ensure_user(callback.from_user.id)
    settings = get_settings()
    if callback.from_user.id in settings.admin_id_set:
        status = "♾ Безлимитный доступ (админ)"
    else:
        async with get_session() as session:
            user = await session.get(User, callback.from_user.id)
        status = status_text(user) if user else "Доступ не найден."
    lines = [f"💳 <b>Подписка</b>\n\n{status}\n"]
    rows = []
    for days, t in settings.sub_tiers.items():
        lines.append(
            f"\n<b>{days} дней — {t['stars']} ⭐</b>\n"
            f"  • до {t['accounts']} аккаунтов\n"
            f"  • до {t['videos']} видео за период"
        )
        rows.append([InlineKeyboardButton(
            text=f"⭐ {t['stars']} — {days} дн.", callback_data=f"buy_sub:{days}"
        )])
    lines.append("\n\nОплата через Telegram Stars. Выбери тариф:")
    await callback.message.answer(
        "".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_sub:"))
async def buy_subscription(callback: CallbackQuery, bot: Bot) -> None:
    days = int(callback.data.split(":", 1)[1])
    stars = get_settings().sub_tiers.get(days)
    if stars is None:
        await callback.answer("Неверный тариф", show_alert=True)
        return
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Подписка PostiqBot — {days} дней",
        description=f"Доступ к авто-репостингу на {days} дней.",
        payload=f"sub:{days}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Подписка {days} дн.", amount=stars)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message, bot: Bot) -> None:
    payload = message.successful_payment.invoice_payload
    try:
        days = int(payload.split(":", 1)[1])
    except (IndexError, ValueError):
        days = 30
    tier = get_settings().sub_tiers.get(days, {"accounts": 5, "videos": 300})
    until = await grant_subscription(
        message.from_user.id, days, accounts=tier["accounts"], videos=tier["videos"]
    )
    await message.answer(
        f"✅ Оплата прошла! Подписка активна до <b>{until:%d.%m.%Y}</b>. Спасибо! 🙌"
    )
    await _reward_referrer(bot, message.from_user.id)


async def _reward_referrer(bot: Bot, payer_id: int) -> None:
    """Начислить бонус пригласившему при ПЕРВОЙ оплате приглашённого."""
    settings = get_settings()
    async with get_session() as session:
        payer = await session.get(User, payer_id)
        if not payer or not payer.referred_by or payer.referral_rewarded:
            return
        payer.referral_rewarded = True
        referrer_id = payer.referred_by
    until = await grant_subscription(referrer_id, settings.referral_bonus_days)
    try:
        await bot.send_message(
            referrer_id,
            f"🎁 Твой приглашённый оформил подписку — тебе <b>+{settings.referral_bonus_days} дней</b>!\n"
            f"Доступ активен до <b>{until:%d.%m.%Y}</b>.",
        )
    except Exception:  # noqa: BLE001
        pass


@router.callback_query(F.data == "referral")
async def referral_menu(callback: CallbackQuery, bot: Bot) -> None:
    await ensure_user(callback.from_user.id)
    settings = get_settings()
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    async with get_session() as session:
        invited = await session.scalar(
            select(func.count()).select_from(User).where(
                User.referred_by == callback.from_user.id
            )
        )
        paid = await session.scalar(
            select(func.count()).select_from(User).where(
                User.referred_by == callback.from_user.id,
                User.referral_rewarded.is_(True),
            )
        )
    await callback.message.answer(
        "🎁 <b>Реферальная программа</b>\n\n"
        f"Приглашай друзей! Когда приглашённый оформит подписку — тебе "
        f"<b>+{settings.referral_bonus_days} дней</b> доступа.\n\n"
        f"Твоя ссылка:\n{link}\n\n"
        f"👥 Приглашено: <b>{invited or 0}</b>\n"
        f"💳 Оплатили (бонус начислен): <b>{paid or 0}</b>"
    )
    await callback.answer()


class SupportFlow(StatesGroup):
    waiting_message = State()


@router.callback_query(F.data == "support")
async def support_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupportFlow.waiting_message)
    await callback.message.answer(
        "✍️ Напиши своё сообщение/вопрос одним сообщением — я передам в поддержку."
    )
    await callback.answer()


@router.message(SupportFlow.waiting_message)
async def support_forward(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    if not message.text:
        await message.answer("Пришли текстом, пожалуйста.")
        return
    sent = False
    for admin_id in get_settings().admin_id_set:
        try:
            await bot.send_message(
                admin_id,
                f"✍️ <b>Поддержка</b> (id <code>{message.from_user.id}</code>):\n\n"
                f"{message.text}",
            )
            sent = True
        except Exception:  # noqa: BLE001
            logger.warning("Не смог доставить сообщение поддержки админу %s", admin_id)
    await message.answer(
        "✅ Отправлено в поддержку — ответим как сможем."
        if sent
        else "⚠️ Поддержка временно недоступна, попробуй позже."
    )


@router.message(F.reply_to_message.text.contains("Поддержка"))
async def admin_reply(message: Message, bot: Bot) -> None:
    """Админ отвечает Reply на пересланное сообщение поддержки → доставляем юзеру."""
    if message.from_user.id not in get_settings().admin_id_set:
        return
    if not message.text:
        return
    m = re.search(r"id\s+(\d+)", message.reply_to_message.text or "")
    if not m:
        await message.reply("Не нашёл id пользователя в исходном сообщении.")
        return
    user_id = int(m.group(1))
    try:
        await bot.send_message(user_id, f"💬 <b>Ответ поддержки:</b>\n\n{message.text}")
        await message.reply("✅ Доставлено пользователю.")
    except Exception:  # noqa: BLE001
        await message.reply("⚠️ Не удалось доставить (юзер не писал боту / заблокировал).")
