"""Админ-команды для управления пулом Google-проектов."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, select

from bot.config import get_settings
from bot.db.models import OAuthProject, PublishAccount
from bot.db.session import get_session
from bot.services.projects import add_project
from bot.services.subscription import grant_subscription

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


@router.message(Command("grant"))
async def cmd_grant(message: Message, command: CommandObject) -> None:
    """/grant <user_id> <дней> — вручную продлить подписку пользователю."""
    if not _is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not all(p.lstrip("-").isdigit() for p in parts):
        await message.answer("Использование: <code>/grant &lt;user_id&gt; &lt;дней&gt;</code>")
        return
    user_id, days = int(parts[0]), int(parts[1])
    top = get_settings().sub_tiers.get(30, {"accounts": 5, "videos": 300})
    until = await grant_subscription(
        user_id, days, accounts=top["accounts"], videos=top["videos"]
    )
    await message.answer(
        f"✅ Пользователю <code>{user_id}</code> доступ продлён до <b>{until:%d.%m.%Y}</b>."
    )


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


@router.message(Command("toggleproject"))
async def cmd_toggleproject(message: Message, command: CommandObject) -> None:
    """/toggleproject <id> — включить/выключить проект в пуле."""
    if not _is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: <code>/toggleproject &lt;id&gt;</code>")
        return
    async with get_session() as session:
        project = await session.get(OAuthProject, int(arg))
        if project is None:
            await message.answer("⚠️ Проект не найден.")
            return
        project.is_active = not project.is_active
        state = "🟢 включён" if project.is_active else "🔴 выключен"
    await message.answer(f"Проект <b>{project.name}</b> (#{project.id}) — {state}.")


@router.message(Command("delproject"))
async def cmd_delproject(message: Message, command: CommandObject) -> None:
    """/delproject <id> — удалить проект из пула."""
    if not _is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: <code>/delproject &lt;id&gt;</code>")
        return
    async with get_session() as session:
        project = await session.get(OAuthProject, int(arg))
        if project is None:
            await message.answer("⚠️ Проект не найден.")
            return
        attached = await session.scalar(
            select(func.count())
            .select_from(PublishAccount)
            .where(PublishAccount.project_id == project.id)
        )
        if attached:
            await message.answer(
                f"⚠️ К проекту <b>{project.name}</b> привязано аккаунтов: {attached}. "
                "Удаление сломает их публикацию.\n"
                f"Если нужно просто убрать из ротации — <code>/toggleproject {project.id}</code>."
            )
            return
        name = project.name
        await session.delete(project)
    await message.answer(f"🗑 Проект <b>{name}</b> удалён из пула.")
