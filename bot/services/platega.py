"""Platega API — создание платежа (СБП) и проверка статуса."""
from __future__ import annotations

import httpx

from bot.config import get_settings

PROCESS_PATH = "/transaction/process"
METHOD_SBP_QR = 2


def _headers() -> dict:
    s = get_settings()
    return {
        "X-MerchantId": s.platega_merchant_id,
        "X-Secret": s.platega_secret,
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    s = get_settings()
    return bool(s.platega_merchant_id and s.platega_secret)


async def create_payment(
    *,
    amount: int,
    description: str,
    user_id: int,
    username: str,
    return_url: str,
) -> tuple[str, str]:
    """Создать платёж СБП. Вернуть (transaction_id, redirect_url)."""
    s = get_settings()
    body = {
        "paymentMethod": METHOD_SBP_QR,
        "paymentDetails": {"amount": amount, "currency": "RUB"},
        "description": description,
        "return": return_url,
        "failedUrl": return_url,
        "payload": f"user:{user_id}",
        "metadata": {"userId": str(user_id), "userName": username or str(user_id)},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(s.platega_base_url + PROCESS_PATH, json=body, headers=_headers())
    data = resp.json()
    tx_id = data.get("transactionId")
    redirect = data.get("redirect")
    if not tx_id or not redirect:
        raise ValueError(f"Platega create error: {resp.status_code} {data}")
    return tx_id, redirect


async def check_status(transaction_id: str) -> str | None:
    """Проверить статус транзакции (PENDING|CONFIRMED|CANCELED|CHARGEBACKED)."""
    s = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{s.platega_base_url}/transaction/{transaction_id}", headers=_headers()
        )
    if resp.status_code != 200:
        return None
    return (resp.json().get("status") or "").upper() or None
