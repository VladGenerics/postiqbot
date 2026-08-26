"""Гайд, подписка (Telegram Stars) и поддержка."""
from __future__ import annotations

import logging
import re
from datetime import datetime

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
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from bot.config import get_settings
from bot.db.models import PAY_PAID, Connection, Payment, PublishAccount, User
from bot.db.session import get_session
from bot.handlers.start import ensure_user
from bot.i18n import t, user_lang
from bot.services import platega, promo
from bot.services.payments_service import grant_in_session
from bot.ui import cleanup_ask, remember_prompt, send_with_icon
from bot.services.subscription import grant_referral_bonus, grant_subscription, status_text

logger = logging.getLogger("postiqbot.extras")

router = Router(name="extras")


async def open_guide(message: Message, user_id: int) -> None:
    lang = await user_lang(user_id)
    await send_with_icon(message, "guide", t("guide", lang), lang=lang)


@router.callback_query(F.data == "guide")
async def show_guide(callback: CallbackQuery) -> None:
    await open_guide(callback.message, callback.from_user.id)
    await callback.answer()


async def open_subscription(message: Message, user_id: int) -> None:
    await ensure_user(user_id)
    s = get_settings()
    lang = await user_lang(user_id)
    rows = [
        [InlineKeyboardButton(
            text=f"{s.plan_label(pl)} — {s.plans[pl]['month']['rub']} "
                 f"{t('per_month_short', lang)}",
            callback_data=f"nav:plan_{pl}",
        )]
        for pl in s.plans
    ]
    await send_with_icon(
        message, "tariffs", t("buy_caption", lang),
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


def _parse_buy(data: str) -> tuple[str, str, str] | None:
    """buy:<plan>:<period>:<currency> → (plan, period, currency) с валидацией."""
    parts = data.split(":")
    if len(parts) != 4:
        return None
    _, plan, period, currency = parts
    s = get_settings()
    if plan not in s.plans or period not in ("month", "forever") or currency not in ("rub", "stars"):
        return None
    return plan, period, currency


@router.callback_query(F.data.startswith("buy:"))
async def buy_plan(callback: CallbackQuery, bot: Bot) -> None:
    parsed = _parse_buy(callback.data)
    lang = await user_lang(callback.from_user.id)
    if not parsed:
        await callback.answer(t("bad_tariff", lang), show_alert=True)
        return
    plan, period, currency = parsed
    s = get_settings()
    days = s.plan_days(period)
    label = s.plan_label(plan)
    period_txt = t("inv_period_forever", lang) if period == "forever" else t("inv_period_month", lang)
    async with get_session() as session:
        applied = await promo.applied_for(session, callback.from_user.id, plan)
    percent = applied.percent if applied else 0
    promo_code = applied.code if applied else None

    if currency == "stars":
        stars = promo.discounted(s.plan_price(plan, period, "stars"), percent)
        async with get_session() as session:
            payment = Payment(
                user_id=callback.from_user.id,
                days=days,
                plan=plan,
                amount=stars,
                currency="XTR",
                provider="stars",
                provider_payment_id=None,
                promo_code=promo_code,
            )
            session.add(payment)
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=t("inv_title", lang, plan=label),
            description=t("inv_desc", lang, period=period_txt),
            payload=f"stars:{payment.id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=t("inv_label", lang, plan=label), amount=stars)],
        )
        await callback.answer()
        return

    if not platega.is_configured():
        await callback.message.answer(t("rub_soon", lang))
        await callback.answer()
        return
    amount = promo.discounted(s.plan_price(plan, period, "rub"), percent)
    me = await bot.get_me()
    try:
        tx_id, redirect = await platega.create_payment(
            amount=amount,
            description=f"PosttiqBot {label} ({period_txt})",
            user_id=callback.from_user.id,
            username=f"@{callback.from_user.username}" if callback.from_user.username else "",
            return_url=f"https://t.me/{me.username}",
        )
    except Exception:  # noqa: BLE001
        logger.exception("Platega create_payment failed")
        await callback.message.answer(t("pay_error", lang))
        await callback.answer()
        return
    async with get_session() as session:
        session.add(Payment(
            user_id=callback.from_user.id, days=days, plan=plan, amount=amount,
            currency="RUB", provider="platega", provider_payment_id=tx_id,
            promo_code=promo_code,
        ))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_pay_now", lang, amount=amount), url=redirect)]
    ])
    await callback.message.answer(t("pay_link", lang, amount=amount, plan=label), reply_markup=kb)
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(query.id, ok=True)


_ALREADY_PAID_TXT = {
    "ru": "✅ Эта оплата уже засчитана — подписка активна.",
    "en": "✅ This payment was already applied — the subscription is active.",
}


async def _activate_stars(
    telegram_id: int, payment_id: int, charge_id: str
) -> tuple[int, str | None, datetime] | None:
    """Клейм Stars-платежа по charge_id + выдача подписки одной транзакцией."""
    async with get_session() as session:
        try:
            res = await session.execute(
                update(Payment)
                .where(
                    Payment.id == payment_id,
                    Payment.user_id == telegram_id,
                    Payment.provider == "stars",
                    Payment.status != PAY_PAID,
                )
                .values(
                    status=PAY_PAID,
                    provider_payment_id=charge_id or None,
                    paid_at=func.now(),
                    granted_at=func.now(),
                )
                .returning(Payment.days, Payment.plan, Payment.promo_code)
            )
            row = res.first()
        except IntegrityError:
            return None
        if row is None:
            return None
        until = await grant_in_session(session, telegram_id, row.days, row.plan)
        await promo.redeem_in_session(session, row.promo_code, telegram_id, payment_id)
    return row.days, row.plan, until


@router.message(F.successful_payment)
async def on_paid(message: Message, bot: Bot) -> None:
    sp = message.successful_payment
    payload = sp.invoice_payload
    user_id = message.from_user.id
    lang = await user_lang(user_id)

    parts = payload.split(":")
    if len(parts) == 2 and parts[0] == "stars" and parts[1].isdigit():
        activated = await _activate_stars(
            user_id, int(parts[1]), sp.telegram_payment_charge_id or ""
        )
        if activated is None:
            await message.answer(_ALREADY_PAID_TXT[lang])
            return
        days, _plan, until = activated
    else:
        plan = parts[1] if len(parts) >= 3 and parts[1] in get_settings().plans else "starter"
        try:
            days = int(parts[2])
        except (IndexError, ValueError):
            days = 30
        until = await grant_subscription(user_id, days, plan=plan)

    if days >= get_settings().forever_days:
        active = t("paid_forever", lang)
    else:
        active = t("paid_until", lang, date=f"{until:%d.%m.%Y}")
    await message.answer(t("paid_ok", lang, active=active))
    await _reward_referrer(bot, user_id)


async def reward_referrer_public(bot: Bot, payer_id: int) -> None:
    """Публичная обёртка для вызова из payment_callback."""
    await _reward_referrer(bot, payer_id)


async def _reward_referrer(bot: Bot, payer_id: int) -> None:
    """Начислить бонус пригласившему при ПЕРВОЙ оплате приглашённого."""
    async with get_session() as session:
        payer = await session.get(User, payer_id)
        if not payer or not payer.referred_by or payer.referral_rewarded:
            return
        payer.referral_rewarded = True
        referrer_id = payer.referred_by
    settings = get_settings()
    days, plan = settings.referral_bonus_days, settings.referral_bonus_plan
    until = await grant_referral_bonus(referrer_id, days, plan)
    lang = await user_lang(referrer_id)
    plan_name = settings.referral_bonus_label
    try:
        await bot.send_message(
            referrer_id,
            t("ref_reward", lang, plan=plan_name, days=days, date=f"{until:%d.%m.%Y}"),
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
        t("referral", lang, bonus=settings.referral_bonus_days,
          plan=settings.referral_bonus_label, link=link,
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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("c_btn_cancel", lang), callback_data="ask_cancel")]
    ])
    prompt = await send_with_icon(
        message, "support", t("support_prompt", lang), reply_markup=kb, lang=lang
    )
    await remember_prompt(state, prompt)


@router.callback_query(F.data == "support")
async def support_start(callback: CallbackQuery, state: FSMContext) -> None:
    await open_support(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.message(SupportFlow.waiting_message)
async def support_forward(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.text:
        await message.answer(t("support_send_text", await user_lang(message.from_user.id)))
        return
    text = message.text
    await cleanup_ask(message, state)
    await state.clear()
    sent = False
    for admin_id in get_settings().admin_id_set:
        try:
            await bot.send_message(
                admin_id,
                f"✍️ <b>Поддержка</b> (id <code>{message.from_user.id}</code>):\n\n"
                f"{text}",
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
        lang = await user_lang(user_id)
        await bot.send_message(user_id, t("sup_reply", lang, text=message.text))
        await message.reply("✅ Доставлено пользователю.")
    except Exception:  # noqa: BLE001
        await message.reply("⚠️ Не удалось доставить (юзер не писал боту / заблокировал).")
