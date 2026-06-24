"""Хендлер /start — регистрация пользователя и главное меню."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy.dialects.postgresql import insert

from bot.config import get_settings
from bot.db.models import User
from bot.db.session import get_session
from bot.keyboards.menus import main_reply_kb

router = Router(name="start")


async def ensure_user(telegram_id: int, referred_by: int | None = None) -> None:
    """Зарегистрировать пользователя с триалом, если его ещё нет (идемпотентно)."""
    settings = get_settings()
    trial_until = datetime.now(timezone.utc) + timedelta(days=settings.trial_days)
    async with get_session() as session:
        stmt = (
            insert(User)
            .values(
                telegram_id=telegram_id,
                trial_until=trial_until,
                referred_by=referred_by,
                tier_accounts=settings.trial_accounts,
                tier_videos=settings.trial_videos,
            )
            .on_conflict_do_nothing(index_elements=["telegram_id"])
        )
        await session.execute(stmt)


async def _parse_referrer(command: CommandObject, self_id: int) -> int | None:
    """Из deep-link /start ref_<id> вернуть валидного существующего реферера."""
    arg = (command.args or "").strip()
    if not arg.startswith("ref_"):
        return None
    ref = arg[4:]
    if not ref.isdigit() or int(ref) == self_id:
        return None
    referrer_id = int(ref)
    async with get_session() as session:
        exists = await session.get(User, referrer_id)
    return referrer_id if exists else None


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    referred_by = await _parse_referrer(command, message.from_user.id)
    await ensure_user(message.from_user.id, referred_by=referred_by)
    await message.answer(
        "👋 Привет! Я <b>PostiqBot</b>.\n\n"
        "Я слежу за каналами-источниками и автоматически перезаливаю новые "
        "видео (включая Shorts) на твои YouTube/TikTok по расписанию.\n\n"
        "Пользуйся кнопками меню внизу 👇\n"
        "Начни с подключения своего канала, потом добавь источник.",
        reply_markup=main_reply_kb(),
    )
