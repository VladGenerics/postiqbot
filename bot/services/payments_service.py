"""Финализация платежей: подтверждение оплаты и фоновая сверка (reconciliation)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import func, select, update

from bot.config import get_settings
from bot.db.models import PAY_PAID, PAY_PENDING, Payment, User
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services import platega

logger = logging.getLogger("postiqbot.payments")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def grant_in_session(
    session, telegram_id: int, days: int, plan: str | None = None
) -> datetime:
    """Продлить подписку в рамках ЧУЖОЙ сессии (без собственного commit)."""
    user = await session.get(User, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)
    now = _now()
    base = (
        user.subscription_until
        if user.subscription_until and user.subscription_until > now
        else now
    )
    user.subscription_until = base + timedelta(days=days)
    user.expiry_warned = False
    if plan is not None:
        p = get_settings().plans.get(plan)
        if p:
            user.tier_accounts = p["accounts"]
            user.tier_videos = p["videos"]
            user.tier_priority = p["priority"]
            user.tier_plan = plan
            user.videos_used = 0
    return user.subscription_until


async def _claim_and_grant(payment_id: int) -> tuple[int, int, datetime] | None:
    """Клейм pending-платежа + выдача подписки ОДНОЙ транзакцией."""
    async with get_session() as session:
        res = await session.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status != PAY_PAID,
                Payment.granted_at.is_(None),
            )
            .values(
                status=PAY_PAID,
                paid_at=func.coalesce(Payment.paid_at, func.now()),
                granted_at=func.now(),
            )
            .returning(Payment.user_id, Payment.days, Payment.plan)
        )
        row = res.first()
        if row is None:
            return None
        until = await grant_in_session(session, row.user_id, row.days, row.plan)
    return row.user_id, row.days, until


async def _grant_lost(payment_id: int) -> tuple[int, int, datetime] | None:
    """Доделать оборванную выдачу: платёж уже paid, но granted_at не проставлен."""
    async with get_session() as session:
        res = await session.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status == PAY_PAID,
                Payment.granted_at.is_(None),
            )
            .values(granted_at=func.now())
            .returning(Payment.user_id, Payment.days, Payment.plan)
        )
        row = res.first()
        if row is None:
            return None
        until = await grant_in_session(session, row.user_id, row.days, row.plan)
    return row.user_id, row.days, until


async def _notify_and_reward(bot: Bot, user_id: int, until: datetime) -> None:
    """Сообщение об активации + реферальный бонус."""
    try:
        lang = await user_lang(user_id)
        await bot.send_message(
            user_id, t("pay_received", lang, date=f"{until:%d.%m.%Y}")
        )
    except Exception:  # noqa: BLE001
        pass
    from bot.handlers.extras import reward_referrer_public
    try:
        await reward_referrer_public(bot, user_id)
    except Exception:  # noqa: BLE001 — бонус не должен ронять финализацию
        logger.exception("referral reward failed for user %d", user_id)


async def finalize_payment(bot: Bot, payment_id: int) -> bool:
    """Подтвердить платёж Platega (с перепроверкой статуса в API)."""
    async with get_session() as session:
        payment = await session.get(Payment, payment_id)
    if payment is None or payment.status == PAY_PAID:
        return False
    if not payment.provider_payment_id:
        return False

    status = await platega.check_status(payment.provider_payment_id)
    if status != "CONFIRMED":
        return False

    result = await _claim_and_grant(payment_id)
    if result is None:
        return False
    user_id, _days, until = result
    await _notify_and_reward(bot, user_id, until)
    logger.info("Платёж #%d активирован (user=%d)", payment_id, user_id)
    return True


async def grant_missing_subscription(bot: Bot, payment_id: int) -> bool:
    """Выдать подписку по оплаченному платежу, если выдача не успела закоммититься."""
    result = await _grant_lost(payment_id)
    if result is None:
        return False
    user_id, _days, until = result
    await _notify_and_reward(bot, user_id, until)
    logger.info("Довыдана подписка по платежу #%d (user=%d)", payment_id, user_id)
    return True


async def reconcile_payments(bot: Bot) -> int:
    """Сверка: активировать подтверждённые pending и довыдать оборванные выдачи."""
    since = _now() - timedelta(hours=24)
    async with get_session() as session:
        pending_ids = list(
            await session.scalars(
                select(Payment.id).where(
                    Payment.status == PAY_PENDING,
                    Payment.provider == "platega",
                    Payment.created_at >= since,
                )
            )
        )
        lost_ids = list(
            await session.scalars(
                select(Payment.id).where(
                    Payment.status == PAY_PAID, Payment.granted_at.is_(None)
                )
            )
        )
    activated = 0
    for pid in pending_ids:
        try:
            if await finalize_payment(bot, pid):
                activated += 1
        except Exception:  # noqa: BLE001
            logger.exception("reconcile payment #%d failed", pid)
    for pid in lost_ids:
        try:
            if await grant_missing_subscription(bot, pid):
                activated += 1
        except Exception:  # noqa: BLE001
            logger.exception("reconcile lost grant #%d failed", pid)
    return activated
