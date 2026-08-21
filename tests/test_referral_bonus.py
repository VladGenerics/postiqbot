"""Реферальный бонус: фиксированные 14 дней Starter, без понижения тарифа."""
from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timedelta, timezone

import pytest

from bot.config import get_settings
from bot.db.models import User
from bot.services import subscription

NOW = datetime.now(timezone.utc)
REFERRER = 777


class _Session:
    """Дублёр сессии: session.get(User, id) отдаёт заранее заданного юзера."""

    def __init__(self, user: User | None) -> None:
        self._user = user

    async def get(self, model, pk):  # noqa: ANN001, ANN201
        return self._user


def _spy(monkeypatch: pytest.MonkeyPatch, user: User | None) -> list[tuple]:
    """Подменить БД и grant_subscription, вернуть список его вызовов."""

    @contextlib.asynccontextmanager
    async def fake_session():
        yield _Session(user)

    calls: list[tuple] = []

    async def fake_grant(telegram_id: int, days: int, plan: str | None = None):
        calls.append((telegram_id, days, plan))
        return NOW + timedelta(days=days)

    monkeypatch.setattr(subscription, "get_session", fake_session)
    monkeypatch.setattr(subscription, "grant_subscription", fake_grant)
    return calls


def test_settings_hold_the_promised_bonus():
    s = get_settings()
    assert s.referral_bonus_days == 14
    assert s.referral_bonus_plan == "starter"
    assert "Starter" in s.referral_bonus_label


def test_bonus_is_fourteen_days_of_starter(monkeypatch):
    """Пригласивший без подписки получает ровно 14 дней Starter."""
    calls = _spy(monkeypatch, None)
    asyncio.run(subscription.grant_referral_bonus(REFERRER))
    assert calls == [(REFERRER, 14, "starter")]


def test_bonus_does_not_depend_on_what_the_invitee_bought(monkeypatch):
    """Купили forever — бонус всё равно 14 дней, а не вечный доступ."""
    calls = _spy(monkeypatch, None)
    asyncio.run(subscription.grant_referral_bonus(REFERRER))
    (_, days, _plan), = calls
    assert days == 14 < get_settings().forever_days


def test_active_premium_keeps_its_plan(monkeypatch):
    """Тариф выше бонусного не понижаем — продлеваем только срок (plan=None)."""
    user = User(
        telegram_id=REFERRER, tier_plan="premium",
        subscription_until=NOW + timedelta(days=30),
    )
    calls = _spy(monkeypatch, user)
    asyncio.run(subscription.grant_referral_bonus(REFERRER))
    assert calls == [(REFERRER, 14, None)]


def test_expired_premium_gets_the_starter_bonus(monkeypatch):
    """Подписка кончилась — бонус возвращает доступ, пусть и на Starter."""
    user = User(
        telegram_id=REFERRER, tier_plan="premium",
        subscription_until=NOW - timedelta(days=1),
    )
    calls = _spy(monkeypatch, user)
    asyncio.run(subscription.grant_referral_bonus(REFERRER))
    assert calls == [(REFERRER, 14, "starter")]


def test_active_starter_is_only_extended(monkeypatch):
    """Тот же тариф: лимиты переставлять не нужно (и не сбрасывать видео)."""
    user = User(
        telegram_id=REFERRER, tier_plan="starter",
        subscription_until=NOW + timedelta(days=3),
    )
    calls = _spy(monkeypatch, user)
    asyncio.run(subscription.grant_referral_bonus(REFERRER))
    assert calls == [(REFERRER, 14, None)]
