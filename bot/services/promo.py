"""Промокоды на скидку: правила (без БД) + операции над таблицами."""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from bot.db.models import PromoCode, PromoRedemption, User

MIN_PERCENT = 1
MAX_PERCENT = 90

CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,31}$")
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

NOT_FOUND = "not_found"
INACTIVE = "inactive"
EXPIRED = "expired"
EXHAUSTED = "exhausted"
WRONG_PLAN = "wrong_plan"
ALREADY_USED = "already_used"
REASONS = (NOT_FOUND, INACTIVE, EXPIRED, EXHAUSTED, WRONG_PLAN, ALREADY_USED)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_code(raw: str) -> str:
    """Ввод пользователя → код в каноничном виде: без пробелов, в верхнем регистре."""
    return re.sub(r"\s+", "", raw or "").upper()


def is_valid_code(code: str) -> bool:
    return bool(CODE_RE.match(code or ""))


def parse_percent(raw: str) -> int | None:
    """«30», «30%», «-30%» → 30. Не число → None (диапазон проверяется отдельно)."""
    txt = (raw or "").strip().lstrip("-−–—").rstrip("%").strip()
    return int(txt) if txt.isdigit() else None


def discounted(price: int, percent: int) -> int:
    """Цена со скидкой."""
    if percent <= 0:
        return price
    percent = min(percent, MAX_PERCENT)
    return max(1, price - price * percent // 100)


def generate_code(percent: int) -> str:
    """Читаемый код вида SALE30-K7QM, когда админ не задал свой."""
    tail = "".join(secrets.choice(_ALPHABET) for _ in range(4))
    return f"SALE{percent}-{tail}"


def applies_to(promo_plan: str | None, plan: str | None) -> bool:
    """promo_plan=None → код на все тарифы."""
    return promo_plan is None or plan is None or promo_plan == plan


def check_rules(
    *,
    is_active: bool,
    expires_at: datetime | None,
    used_count: int,
    max_uses: int,
    promo_plan: str | None,
    plan: str | None,
    already_used: bool,
    now: datetime | None = None,
) -> str | None:
    """Причина отказа (одна из REASONS) или None, если код применим."""
    if not is_active:
        return INACTIVE
    if expires_at is not None and expires_at <= (now or _now()):
        return EXPIRED
    if max_uses and used_count >= max_uses:
        return EXHAUSTED
    if not applies_to(promo_plan, plan):
        return WRONG_PLAN
    if already_used:
        return ALREADY_USED
    return None


@dataclass(slots=True)
class NewPromo:
    """Разобранные аргументы «/promo new …»."""

    code: str
    percent: int
    plan: str | None
    max_uses: int
    days: int | None


def parse_new(args: Iterable[str], plans: Iterable[str]) -> tuple[NewPromo | None, str | None]:
    """Разобрать аргументы создания кода в ЛЮБОМ порядке."""
    known_plans = {p.lower() for p in plans}
    code: str | None = None
    percent: int | None = None
    plan: str | None = None
    max_uses = 0
    days: int | None = None

    for token in args:
        low = token.lower()
        if low in ("all", "все", "*"):
            plan = None
            continue
        if low in known_plans:
            plan = low
            continue
        if "=" in low:
            key, _, raw = low.partition("=")
            if key in ("uses", "use", "n"):
                if not raw.isdigit():
                    return None, "bad_uses"
                max_uses = int(raw)
                continue
            if key in ("days", "day", "d"):
                if not raw.isdigit() or int(raw) == 0:
                    return None, "bad_days"
                days = int(raw)
                continue
            return None, "bad_token"
        value = parse_percent(token)
        if value is not None and percent is None:
            percent = value
            continue
        if code is None:
            code = normalize_code(token)
            if not is_valid_code(code):
                return None, "bad_code"
            continue
        return None, "bad_token"

    if percent is None:
        return None, "no_percent"
    if not MIN_PERCENT <= percent <= MAX_PERCENT:
        return None, "bad_percent"
    return NewPromo(code or generate_code(percent), percent, plan, max_uses, days), None


@dataclass(slots=True)
class Applied:
    """Скидка, готовая к применению к цене."""

    code: str
    percent: int


async def get(session, code: str) -> PromoCode | None:
    code = normalize_code(code)
    if not code:
        return None
    return await session.scalar(select(PromoCode).where(PromoCode.code == code))


async def check(
    session, code: str, user_id: int, plan: str | None = None
) -> tuple[PromoCode | None, str | None]:
    """Проверить код для пользователя. Возврат: (код, None) или (код|None, причина)."""
    promo = await get(session, code)
    if promo is None:
        return None, NOT_FOUND
    used = await session.scalar(
        select(func.count())
        .select_from(PromoRedemption)
        .where(PromoRedemption.promo_id == promo.id, PromoRedemption.user_id == user_id)
    )
    reason = check_rules(
        is_active=promo.is_active,
        expires_at=promo.expires_at,
        used_count=promo.used_count,
        max_uses=promo.max_uses,
        promo_plan=promo.plan,
        plan=plan,
        already_used=bool(used),
    )
    return promo, reason


async def applied_for(session, user_id: int, plan: str | None) -> Applied | None:
    """Скидка, действующая для пользователя на этот тариф (None — скидки нет)."""
    user = await session.get(User, user_id)
    if user is None or not user.promo_code:
        return None
    promo, reason = await check(session, user.promo_code, user_id, plan)
    if promo is None or reason is not None:
        return None
    return Applied(promo.code, promo.percent)


async def redeem_in_session(
    session, code: str | None, user_id: int, payment_id: int | None = None
) -> bool:
    """Списать код в ЧУЖОЙ транзакции (той же, что выдаёт подписку)."""
    promo = await get(session, code or "")
    if promo is None:
        return False
    res = await session.execute(
        insert(PromoRedemption)
        .values(promo_id=promo.id, user_id=user_id, payment_id=payment_id)
        .on_conflict_do_nothing(constraint="uq_promo_user")
    )
    user = await session.get(User, user_id)
    if user is not None and normalize_code(user.promo_code or "") == promo.code:
        user.promo_code = None
    if not res.rowcount:
        return False
    await session.execute(
        update(PromoCode)
        .where(PromoCode.id == promo.id)
        .values(used_count=PromoCode.used_count + 1)
    )
    return True


async def create(session, data: NewPromo, created_by: int | None) -> PromoCode:
    promo = PromoCode(
        code=data.code,
        percent=data.percent,
        plan=data.plan,
        max_uses=data.max_uses,
        used_count=0,
        is_active=True,
        expires_at=None if data.days is None else _now() + timedelta(days=data.days),
        created_by=created_by,
    )
    session.add(promo)
    return promo


async def all_codes(session) -> list[PromoCode]:
    return list(await session.scalars(select(PromoCode).order_by(PromoCode.id.desc())))
