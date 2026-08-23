"""aiohttp-роут: приём callback от Platega при смене статуса транзакции."""
from __future__ import annotations

import logging
import time

from aiogram import Bot
from aiohttp import web
from sqlalchemy import select

from bot.db.models import Payment
from bot.db.session import get_session
from bot.services.payments_service import finalize_payment

logger = logging.getLogger("postiqbot.payments")

_DEBOUNCE_TTL = 30.0
_DEBOUNCE_MAX = 1000

_seen_cb: dict[str, float] = {}


def _debounce_hit(tx_id: str) -> bool:
    """True, если по этому tx уже был колбэк в последние _DEBOUNCE_TTL секунд."""
    now = time.monotonic()
    if len(_seen_cb) >= _DEBOUNCE_MAX:
        cutoff = now - _DEBOUNCE_TTL
        stale = [k for k, ts in _seen_cb.items() if ts < cutoff]
        for k in stale:
            del _seen_cb[k]
        if len(_seen_cb) >= _DEBOUNCE_MAX:
            _seen_cb.clear()
    last = _seen_cb.get(tx_id)
    _seen_cb[tx_id] = now
    return last is not None and now - last < _DEBOUNCE_TTL


def _extract(data: dict) -> tuple[str | None, str]:
    tx_id = data.get("id") or data.get("transactionId") or data.get("paymentId")
    status = (data.get("status") or "").upper()
    return (str(tx_id) if tx_id else None), status


async def payment_callback(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    try:
        data = await request.json()
    except Exception:  # noqa: BLE001
        return web.Response(text="ok")

    tx_id, status = _extract(data)
    logger.info("Platega callback: tx=%s status=%s", tx_id, status)
    if not tx_id:
        return web.Response(text="ok")

    if _debounce_hit(tx_id):
        return web.Response(text="ok")

    async with get_session() as session:
        payment = await session.scalar(
            select(Payment).where(Payment.provider_payment_id == tx_id)
        )
    if payment is None or payment.provider != "platega" or not payment.provider_payment_id:
        return web.Response(text="ok")
    await finalize_payment(bot, payment.id)
    return web.Response(text="ok")


async def payment_callback_ping(_: web.Request) -> web.Response:
    """GET на тот же URL — для валидации/health-check провайдером (всегда 200)."""
    return web.Response(text="ok")


def add_payment_routes(app: web.Application) -> None:
    app.router.add_post("/payment/callback", payment_callback)
    app.router.add_get("/payment/callback", payment_callback_ping)
