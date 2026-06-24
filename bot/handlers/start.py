"""Хендлер /start — регистрация пользователя и главное меню."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.dialects.postgresql import insert

from bot.db.models import User
from bot.db.session import get_session
from bot.keyboards.menus import main_menu

router = Router(name="start")


async def ensure_user(telegram_id: int) -> None:
    """Зарегистрировать пользователя, если его ещё нет (идемпотентно)."""
    async with get_session() as session:
        stmt = (
            insert(User)
            .values(telegram_id=telegram_id)
            .on_conflict_do_nothing(index_elements=["telegram_id"])
        )
        await session.execute(stmt)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await ensure_user(message.from_user.id)
    await message.answer(
        "👋 Привет! Я <b>PostiqBot</b>.\n\n"
        "Я слежу за каналами-источниками и автоматически перезаливаю новые "
        "видео на твой YouTube по расписанию.\n\n"
        "Начни с подключения своего YouTube-канала 👇",
        reply_markup=main_menu(),
    )
