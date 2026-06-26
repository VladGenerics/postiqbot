"""aiohttp-роут: приём callback от Platega при смене статуса транзакции."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiohttp import web
from sqlalchemy import select

from bot.config import get_settings
from bot.db.models import PAY_PAID, Payment
from bot.db.session import get_session
from bot.handlers.extras import reward_referrer_public
from bot.services import platega
from bot.services.subscription import grant_subscription

logger = logging.getLogger("postiqbot.payments")


def _extract(data: dict) -> tuple[str | None, str]:
    tx_id = data.get("id") or data.get("transactionId") or data.get("paymentId")
    status = (data.get("status") or "").upper()
    return (str(tx_id) if tx_id else None), status


async def payment_callback(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    try:
        data = await request.json()
    except Exception:  # noqa: BLE001
        return web.Response(text="bad json", status=400)

    tx_id, status = _extract(data)
    logger.info("Platega callback: tx=%s status=%s", tx_id, status)
    if not tx_id:
        return web.Response(text="no id")

    async with get_session() as session:
        payment = await session.scalar(
            select(Payment).where(Payment.provider_payment_id == tx_id)
        )
    if payment is None:
        return web.Response(text="unknown")
    if payment.status == PAY_PAID:
        return web.Response(text="already")

    verified = await platega.check_status(tx_id)
    final = verified or status
    if final != "CONFIRMED":
        return web.Response(text="not confirmed")

    tier = get_settings().sub_tiers.get(payment.days, {"accounts": 1, "videos": 5})
    until = await grant_subscription(
        payment.user_id, payment.days, accounts=tier["accounts"], videos=tier["videos"]
    )
    async with get_session() as session:
        p = await session.get(Payment, payment.id)
        if p:
            p.status = PAY_PAID
            p.paid_at = datetime.now(timezone.utc)

    try:
        await bot.send_message(
            payment.user_id,
            f"✅ Оплата получена! Подписка активна до <b>{until:%d.%m.%Y}</b>. Спасибо! 🙌",
        )
    except Exception:  # noqa: BLE001
        pass
    await reward_referrer_public(bot, payment.user_id)
    return web.Response(text="ok")


def add_payment_routes(app: web.Application) -> None:
    app.router.add_post("/payment/callback", payment_callback)
