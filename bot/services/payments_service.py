"""Финализация платежей: подтверждение оплаты и фоновая сверка (reconciliation)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select, update

from bot.config import get_settings
from bot.db.models import PAY_PAID, PAY_PENDING, Payment
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services import platega
from bot.services.subscription import grant_subscription

logger = logging.getLogger("postiqbot.payments")


async def finalize_payment(bot: Bot, payment_id: int) -> bool:
    """Подтвердить платёж (с перепроверкой статуса в API)."""
    async with get_session() as session:
        payment = await session.get(Payment, payment_id)
    if payment is None or payment.status == PAY_PAID:
        return False

    status = await platega.check_status(payment.provider_payment_id or "")
    if status != "CONFIRMED":
        return False

    async with get_session() as session:
        res = await session.execute(
            update(Payment)
            .where(Payment.id == payment_id, Payment.status != PAY_PAID)
            .values(status=PAY_PAID, paid_at=datetime.now(timezone.utc))
        )
        claimed = res.rowcount or 0
    if not claimed:
        return False

    until = await grant_subscription(payment.user_id, payment.days, plan=payment.plan)
    try:
        lang = await user_lang(payment.user_id)
        await bot.send_message(
            payment.user_id,
            t("pay_received", lang, date=f"{until:%d.%m.%Y}"),
        )
    except Exception:  # noqa: BLE001
        pass
    from bot.handlers.extras import reward_referrer_public
    await reward_referrer_public(bot, payment.user_id)
    logger.info("Платёж #%d активирован (user=%d)", payment_id, payment.user_id)
    return True


async def reconcile_payments(bot: Bot) -> int:
    """Проверить висящие платежи за последние сутки и активировать оплаченные."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    async with get_session() as session:
        ids = list(
            await session.scalars(
                select(Payment.id).where(
                    Payment.status == PAY_PENDING, Payment.created_at >= since
                )
            )
        )
    activated = 0
    for pid in ids:
        try:
            if await finalize_payment(bot, pid):
                activated += 1
        except Exception:  # noqa: BLE001
            logger.exception("reconcile payment #%d failed", pid)
    return activated
