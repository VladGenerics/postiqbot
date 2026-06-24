"""Логика доступа: триал + платная подписка (Telegram Stars)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from bot.config import get_settings
from bot.db.models import User
from bot.db.session import get_session


def _now() -> datetime:
    return datetime.now(timezone.utc)


def access_until(user: User) -> datetime | None:
    """Максимальная из дат доступа (триал/подписка), или None."""
    dates = [d for d in (user.trial_until, user.subscription_until) if d is not None]
    return max(dates) if dates else None


def is_user_active(user: User) -> bool:
    until = access_until(user)
    return until is not None and until > _now()


async def is_active(telegram_id: int) -> bool:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        return bool(user and is_user_active(user))


async def active_user_ids(telegram_ids: list[int]) -> set[int]:
    """Из списка id вернуть тех, у кого доступ активен (один запрос)."""
    if not telegram_ids:
        return set()
    admins = get_settings().admin_id_set
    async with get_session() as session:
        users = (
            await session.scalars(
                select(User).where(User.telegram_id.in_(telegram_ids))
            )
        ).all()
    result = {u.telegram_id for u in users if is_user_active(u)}
    result |= {tid for tid in telegram_ids if tid in admins}
    return result


async def grant_subscription(telegram_id: int, days: int) -> datetime:
    """Продлить подписку на days дней (от max(now, текущей даты)). Вернуть новую дату."""
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
        base = user.subscription_until if (
            user.subscription_until and user.subscription_until > _now()
        ) else _now()
        user.subscription_until = base + timedelta(days=days)
        return user.subscription_until


def status_text(user: User) -> str:
    until = access_until(user)
    now = _now()
    if until is None or until <= now:
        return "❌ Доступ неактивен. Оформи подписку, чтобы бот публиковал видео."
    days = (until - now).days
    src = "подписка" if (user.subscription_until and user.subscription_until > now) else "триал"
    return f"✅ Доступ активен ({src}) до <b>{until:%d.%m.%Y}</b> (осталось ~{days} дн.)"
