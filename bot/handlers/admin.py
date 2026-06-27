"""Админ-команды для управления пулом Google-проектов."""
from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from bot.config import get_settings
from bot.db.models import (
    JOB_PENDING,
    Connection,
    Job,
    OAuthProject,
    PublishAccount,
    SourceChannel,
)
from bot.db.session import get_session
from bot.services.projects import add_project
from bot.services.rss_monitor import _fetch_for
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


@router.message(Command("forcepublish"))
async def cmd_forcepublish(message: Message, command: CommandObject) -> None:
    """/forcepublish <connection_id> — взять ПОСЛЕДНЕЕ видео источника и поставить на публикацию сейчас."""
    if not _is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: <code>/forcepublish &lt;connection_id&gt;</code>")
        return
    async with get_session() as session:
        conn = await session.get(Connection, int(arg))
        if conn is None:
            await message.answer("⚠️ Связка не найдена.")
            return
        source = await session.get(SourceChannel, conn.source_channel_id)
    if source is None:
        await message.answer("⚠️ У связки нет источника.")
        return

    feed = await _fetch_for(source)
    if feed is None or not feed.entries:
        await message.answer(
            f"⚠️ Не удалось получить видео источника «{source.channel_title}»."
        )
        return

    entry = feed.entries[0]
    async with get_session() as session:
        stmt = (
            insert(Job)
            .values(
                connection_id=conn.id,
                source_video_id=entry.video_id,
                video_url=entry.url,
                title=entry.title,
                status=JOB_PENDING,
                scheduled_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(constraint="uq_job_source_video")
        )
        res = await session.execute(stmt)

    if res.rowcount:
        await message.answer(
            f"✅ «{entry.title}» поставлено в очередь (связка #{conn.id}).\n"
            "Опубликует в ближайшие ~5–10 мин (скачивание → загрузка)."
        )
    else:
        await message.answer(
            "ℹ️ Это видео уже обрабатывалось ранее (job существует). "
            "Дождись нового ролика на источнике."
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """/help — список админ-команд. Виден и работает ТОЛЬКО для админов."""
    if not _is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 <b>Админ-команды</b> (только для админов)\n\n"
        "<b>/projects</b> — список Google-проектов в пуле и их квоты\n"
        "<b>/addproject</b> &lt;name&gt; &lt;client_id&gt; &lt;secret&gt; — добавить проект "
        "в пул (+6 видео/день)\n"
        "<b>/toggleproject</b> &lt;id&gt; — вкл/выкл проект (выключенный не раздаётся "
        "новым подключениям, привязанные аккаунты работают)\n"
        "<b>/delproject</b> &lt;id&gt; — удалить проект (только если к нему 0 аккаунтов)\n"
        "<b>/grant</b> &lt;user_id&gt; &lt;дней&gt; — продлить подписку пользователю\n"
        "<b>/forcepublish</b> &lt;connection_id&gt; — опубликовать последнее видео "
        "источника сейчас, минуя защиту от бэклога (тест/демо)\n"
        "<b>/help</b> — этот список\n\n"
        "<i>Команды видны только админам из ADMIN_IDS; остальным бот не отвечает.</i>"
    )
