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


async def grant_subscription(
    telegram_id: int,
    days: int,
    accounts: int | None = None,
    videos: int | None = None,
) -> datetime:
    """Продлить подписку на days дней."""
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
        base = user.subscription_until if (
            user.subscription_until and user.subscription_until > _now()
        ) else _now()
        user.subscription_until = base + timedelta(days=days)
        if accounts is not None and videos is not None:
            user.tier_accounts = accounts
            user.tier_videos = videos
            user.videos_used = 0
        return user.subscription_until


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_id_set


async def can_add_account(telegram_id: int, current_count: int) -> tuple[bool, int]:
    """Можно ли подключить ещё аккаунт. Вернуть (можно, лимит)."""
    if _is_admin(telegram_id):
        return True, 999
    async with get_session() as session:
        user = await session.get(User, telegram_id)
    limit = user.tier_accounts if user else get_settings().trial_accounts
    return current_count < limit, limit


async def video_limited_users(telegram_ids: list[int]) -> set[int]:
    """Из списка id вернуть тех, кто исчерпал лимит видео за период (без админов)."""
    if not telegram_ids:
        return set()
    admins = get_settings().admin_id_set
    async with get_session() as session:
        users = (
            await session.scalars(
                select(User).where(User.telegram_id.in_(telegram_ids))
            )
        ).all()
    return {
        u.telegram_id
        for u in users
        if u.telegram_id not in admins and u.videos_used >= u.tier_videos
    }


async def inc_videos_used(telegram_id: int) -> None:
    """+1 к расходу видео (кроме админов)."""
    if _is_admin(telegram_id):
        return
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.videos_used += 1


def status_text(user: User, lang: str = "ru") -> str:
    until = access_until(user)
    now = _now()
    videos_left = max(0, user.tier_videos - user.videos_used)
    if lang == "en":
        if until is None or until <= now:
            return "❌ Access inactive. Buy a subscription so the bot can publish."
        days = (until - now).days
        src = "subscription" if (user.subscription_until and user.subscription_until > now) else "trial"
        return (
            f"✅ Access active ({src}) until <b>{until:%d.%m.%Y}</b> (~{days}d)\n"
            f"📦 Accounts limit: <b>{user.tier_accounts}</b>\n"
            f"🎬 Videos left: <b>{videos_left}</b> of {user.tier_videos}"
        )
    if until is None or until <= now:
        return "❌ Доступ неактивен. Оформи подписку, чтобы бот публиковал видео."
    days = (until - now).days
    src = "подписка" if (user.subscription_until and user.subscription_until > now) else "триал"
    return (
        f"✅ Доступ активен ({src}) до <b>{until:%d.%m.%Y}</b> (~{days} дн.)\n"
        f"📦 Лимит аккаунтов: <b>{user.tier_accounts}</b>\n"
        f"🎬 Видео осталось: <b>{videos_left}</b> из {user.tier_videos}"
    )
