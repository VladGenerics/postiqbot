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
from bot.db.models import Connection, Payment, PublishAccount, User
from bot.db.session import get_session
from bot.handlers.start import ensure_user
from bot.i18n import t, user_lang
from bot.services import platega
from bot.ui import send_with_icon
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


async def open_guide(message: Message, user_id: int) -> None:
    lang = await user_lang(user_id)
    await send_with_icon(message, "guide", t("guide", lang), lang=lang)


@router.callback_query(F.data == "guide")
async def show_guide(callback: CallbackQuery) -> None:
    await open_guide(callback.message, callback.from_user.id)
    await callback.answer()


async def open_subscription(message: Message, user_id: int) -> None:
    await ensure_user(user_id)
    settings = get_settings()
    lang = await user_lang(user_id)
    if user_id in settings.admin_id_set:
        status = t("status_admin", lang)
    else:
        async with get_session() as session:
            user = await session.get(User, user_id)
        status = status_text(user, lang) if user else "—"
    rows = [
        [InlineKeyboardButton(
            text=f"{settings.tier_label(days, lang)} — {settings.tier_price(days, lang)}",
            callback_data=f"buy_sub:{days}",
        )]
        for days in settings.sub_tiers
    ]
    prices = "\n".join(
        t("price_line", lang, plan=settings.tier_label(days, lang),
          price=settings.tier_price(days, lang),
          accounts=tier["accounts"], videos=tier["videos"])
        for days, tier in settings.sub_tiers.items()
    )
    caption = t("tariffs_caption", lang, status=status, prices=prices)
    await send_with_icon(
        message, "tariffs", caption,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), lang=lang,
    )


@router.callback_query(F.data == "subscription")
async def subscription_menu(callback: CallbackQuery) -> None:
    await open_subscription(callback.message, callback.from_user.id)
    await callback.answer()


async def open_profile(message: Message, user_id: int) -> None:
    await ensure_user(user_id)
    settings = get_settings()
    lang = await user_lang(user_id)
    async with get_session() as session:
        user = await session.get(User, user_id)
        accounts = await session.scalar(
            select(func.count()).select_from(PublishAccount).where(
                PublishAccount.user_id == user_id
            )
        )
        connections = await session.scalar(
            select(func.count()).select_from(Connection).where(
                Connection.user_id == user_id
            )
        )
        invited = await session.scalar(
            select(func.count()).select_from(User).where(User.referred_by == user_id)
        )
    if user_id in settings.admin_id_set:
        status = t("status_admin", lang)
    else:
        status = status_text(user, lang) if user else "—"
    await send_with_icon(
        message, "profile",
        t("profile_body", lang, status=status, accounts=accounts or 0,
          connections=connections or 0, invited=invited or 0), lang=lang,
    )


@router.callback_query(F.data == "profile")
async def profile_menu(callback: CallbackQuery) -> None:
    await open_profile(callback.message, callback.from_user.id)
    await callback.answer()


async def open_documents(message: Message, user_id: int) -> None:
    lang = await user_lang(user_id)
    s = get_settings()
    contact = f" — {s.support_contact}" if s.support_contact else ""
    text = t("documents_title", lang) + t("support_line", lang, contact=contact)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_privacy", lang), url=s.privacy_url)],
        [InlineKeyboardButton(text=t("btn_terms", lang), url=s.terms_url)],
    ])
    await send_with_icon(message, "documents", text, reply_markup=kb, lang=lang)


@router.callback_query(F.data == "documents")
async def documents_menu(callback: CallbackQuery) -> None:
    await open_documents(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("buy_sub:"))
async def buy_subscription(callback: CallbackQuery) -> None:
    days = int(callback.data.split(":", 1)[1])
    lang = await user_lang(callback.from_user.id)
    tier = get_settings().sub_tiers.get(days)
    if not tier:
        await callback.answer(t("bad_tariff", lang), show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t("btn_pay_rub", lang, price=get_settings().tier_price(days, lang)),
            callback_data=f"pay_rub:{days}"
        )],
        [InlineKeyboardButton(
            text=t("btn_pay_stars", lang, stars=tier["stars"]), callback_data=f"pay_stars:{days}"
        )],
    ])
    plan = get_settings().tier_label(days, lang)
    await callback.message.answer(t("pay_choose", lang, plan=plan), reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars:"))
async def pay_stars(callback: CallbackQuery, bot: Bot) -> None:
    days = int(callback.data.split(":", 1)[1])
    lang = await user_lang(callback.from_user.id)
    tier = get_settings().sub_tiers.get(days)
    if not tier:
        await callback.answer(t("bad_tariff", lang), show_alert=True)
        return
    plan = get_settings().tier_label(days, lang)
    forever = days >= get_settings().forever_days
    period = t("inv_period_forever", lang) if forever else t("inv_period_days", lang, days=days)
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=t("inv_title", lang, plan=plan),
        description=t("inv_desc", lang, period=period),
        payload=f"sub:{days}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=t("inv_label", lang, plan=plan), amount=tier["stars"])],
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_rub:"))
async def pay_rub(callback: CallbackQuery, bot: Bot) -> None:
    days = int(callback.data.split(":", 1)[1])
    tier = get_settings().sub_tiers.get(days)
    lang = await user_lang(callback.from_user.id)
    if not tier:
        await callback.answer(t("bad_tariff", lang), show_alert=True)
        return
    if not platega.is_configured():
        await callback.message.answer(t("rub_soon", lang))
        await callback.answer()
        return

    amount = tier["rub"]
    plan = get_settings().tier_label(days, lang)
    me = await bot.get_me()
    return_url = f"https://t.me/{me.username}"
    try:
        tx_id, redirect = await platega.create_payment(
            amount=amount,
            description=f"PostiqBot подписка — {plan}",
            user_id=callback.from_user.id,
            username=f"@{callback.from_user.username}" if callback.from_user.username else "",
            return_url=return_url,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Platega create_payment failed")
        await callback.message.answer(t("pay_error", lang))
        await callback.answer()
        return

    async with get_session() as session:
        session.add(Payment(
            user_id=callback.from_user.id, days=days, amount=amount,
            currency="RUB", provider="platega", provider_payment_id=tx_id,
        ))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_pay_now", lang, amount=amount), url=redirect)]
    ])
    await callback.message.answer(
        t("pay_link", lang, amount=amount, plan=plan), reply_markup=kb
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
    settings = get_settings()
    tier = settings.sub_tiers.get(days, {"accounts": 5, "videos": 40})
    until = await grant_subscription(
        message.from_user.id, days, accounts=tier["accounts"], videos=tier["videos"]
    )
    lang = await user_lang(message.from_user.id)
    if days >= settings.forever_days:
        active = t("paid_forever", lang)
    else:
        active = t("paid_until", lang, date=f"{until:%d.%m.%Y}")
    await message.answer(t("paid_ok", lang, active=active))
    await _reward_referrer(bot, message.from_user.id)


async def reward_referrer_public(bot: Bot, payer_id: int) -> None:
    """Публичная обёртка для вызова из payment_callback."""
    await _reward_referrer(bot, payer_id)


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
    lang = await user_lang(referrer_id)
    try:
        await bot.send_message(
            referrer_id,
            t("ref_reward", lang, days=settings.referral_bonus_days, date=f"{until:%d.%m.%Y}"),
        )
    except Exception:  # noqa: BLE001
        pass


async def open_referral(message: Message, bot: Bot, user_id: int) -> None:
    await ensure_user(user_id)
    settings = get_settings()
    lang = await user_lang(user_id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user_id}"
    async with get_session() as session:
        invited = await session.scalar(
            select(func.count()).select_from(User).where(User.referred_by == user_id)
        )
        paid = await session.scalar(
            select(func.count()).select_from(User).where(
                User.referred_by == user_id, User.referral_rewarded.is_(True)
            )
        )
    await send_with_icon(
        message, "referral",
        t("referral", lang, bonus=settings.referral_bonus_days, link=link,
          invited=invited or 0, paid=paid or 0), lang=lang,
    )


@router.callback_query(F.data == "referral")
async def referral_menu(callback: CallbackQuery, bot: Bot) -> None:
    await open_referral(callback.message, bot, callback.from_user.id)
    await callback.answer()


class SupportFlow(StatesGroup):
    waiting_message = State()


async def open_support(message: Message, state: FSMContext, user_id: int) -> None:
    lang = await user_lang(user_id)
    await state.set_state(SupportFlow.waiting_message)
    await send_with_icon(message, "support", t("support_prompt", lang), lang=lang)


@router.callback_query(F.data == "support")
async def support_start(callback: CallbackQuery, state: FSMContext) -> None:
    await open_support(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.message(SupportFlow.waiting_message)
async def support_forward(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    if not message.text:
        await message.answer(t("support_send_text", await user_lang(message.from_user.id)))
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
    lang = await user_lang(message.from_user.id)
    await message.answer(t("support_sent" if sent else "support_unavailable", lang))


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
