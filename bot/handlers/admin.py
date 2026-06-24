"""Админ-команды для управления пулом Google-проектов."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select

from bot.config import get_settings
from bot.db.models import OAuthProject
from bot.db.session import get_session
from bot.services.projects import add_project

router = Router(name="admin")


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_id_set


@router.message(Command("addproject"))
async def cmd_addproject(message: Message, command: CommandObject) -> None:
    """/addproject <name> <client_id> <client_secret> — добавить проект в пул."""
    if not _is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if len(parts) != 3:
        await message.answer(
            "Использование:\n"
            "<code>/addproject &lt;name&gt; &lt;client_id&gt; &lt;client_secret&gt;</code>"
        )
        return
    name, client_id, client_secret = parts
    async with get_session() as session:
        exists = await session.scalar(
            select(OAuthProject).where(OAuthProject.client_id == client_id)
        )
        if exists:
            await message.answer("⚠️ Проект с таким client_id уже есть в пуле.")
            return
        await add_project(session, name, client_id, client_secret)
    await message.answer(f"✅ Проект <b>{name}</b> добавлен в пул.")


@router.message(Command("projects"))
async def cmd_projects(message: Message) -> None:
    """/projects — список проектов в пуле (только для админов)."""
    if not _is_admin(message.from_user.id):
        return
    async with get_session() as session:
        projects = (
            await session.scalars(select(OAuthProject).order_by(OAuthProject.id))
        ).all()
    if not projects:
        await message.answer("Пул пуст.")
        return
    lines = [
        f"#{p.id} <b>{p.name}</b> — квота {p.daily_quota}/день "
        f"{'🟢' if p.is_active else '🔴'}"
        for p in projects
    ]
    await message.answer("\n".join(lines))
