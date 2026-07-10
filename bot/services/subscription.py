"""Логика доступа: триал + платная подписка (Telegram Stars)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from bot.config import get_settings
from bot.db.models import JOB_PUBLISHED, Connection, Job, User
from bot.db.session import get_session
from sqlalchemy import func


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _start_of_day(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def published_today_by_user(
    session, telegram_ids: list[int]
) -> dict[int, int]:
    """{user_id: сколько видео опубликовано сегодня} — один запрос."""
    if not telegram_ids:
        return {}
    rows = await session.execute(
        select(Connection.user_id, func.count(Job.id))
        .select_from(Job)
        .join(Connection, Connection.id == Job.connection_id)
        .where(
            Job.status == JOB_PUBLISHED,
            Job.updated_at >= _start_of_day(_now()),
            Connection.user_id.in_(telegram_ids),
        )
        .group_by(Connection.user_id)
    )
    return dict(rows.all())


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
    plan: str | None = None,
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
        if plan is not None:
            p = get_settings().plans.get(plan)
            if p:
                user.tier_accounts = p["accounts"]
                user.tier_videos = p["videos"]
                user.tier_priority = p["priority"]
                user.tier_plan = plan
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
    """Из списка id вернуть тех, кто исчерпал ДНЕВНОЙ лимит видео (без админов)."""
    if not telegram_ids:
        return set()
    admins = get_settings().admin_id_set
    async with get_session() as session:
        users = (
            await session.scalars(
                select(User).where(User.telegram_id.in_(telegram_ids))
            )
        ).all()
        used = await published_today_by_user(session, telegram_ids)
    return {
        u.telegram_id
        for u in users
        if u.telegram_id not in admins and used.get(u.telegram_id, 0) >= u.tier_videos
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
    from bot.config import fmt_limit

    s = get_settings()
    until = access_until(user)
    now = _now()
    forever = until is not None and (until - now).days > 3650
    accs = fmt_limit(user.tier_accounts)
    vids = fmt_limit(user.tier_videos)
    plan_name = s.plans[user.tier_plan]["name"] if user.tier_plan in s.plans else None
    if lang == "en":
        if until is None or until <= now:
            return "❌ Access inactive. Buy a subscription so the bot can publish."
        src = f"{plan_name} plan" if plan_name else "trial"
        expiry = "forever ♾️" if forever else f"until <b>{until:%d.%m.%Y}</b> (~{(until - now).days}d)"
        return (
            f"✅ Access active ({src}) {expiry}\n"
            f"📦 Channels: <b>{accs}</b>\n"
            f"🎬 Daily limit: <b>{vids}</b> videos/day per connection"
        )
    if until is None or until <= now:
        return "❌ Доступ неактивен. Оформи подписку, чтобы бот публиковал видео."
    src = f"тариф {plan_name}" if plan_name else "триал"
    expiry = "навсегда ♾️" if forever else f"до <b>{until:%d.%m.%Y}</b> (~{(until - now).days} дн.)"
    return (
        f"✅ Доступ активен ({src}) {expiry}\n"
        f"📦 Каналов: <b>{accs}</b>\n"
        f"🎬 Дневной лимит: <b>{vids}</b> видео/день на связку"
    )
