"""Админ-команды для управления пулом Google-проектов."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert

from bot.config import get_settings
from bot.db.models import (
    JOB_FAILED,
    JOB_PENDING,
    JOB_PUBLISHED,
    Connection,
    Job,
    OAuthProject,
    PublishAccount,
    SourceChannel,
    User,
)
from bot.db.session import get_session
from bot.services.archive import fetch_channel_archive
from bot.services.projects import add_project
from bot.services.rss_monitor import _fetch_for
from bot.services.scheduling import compute_scheduled_at
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


async def _last_scheduled_at(connection_id: int) -> datetime | None:
    async with get_session() as session:
        return await session.scalar(
            select(func.max(Job.scheduled_at)).where(
                Job.connection_id == connection_id, Job.status != JOB_FAILED
            )
        )


@router.message(Command("backfill"))
async def cmd_backfill(message: Message, command: CommandObject) -> None:
    """/backfill <connection_id> [N] — залить архив источника СТАРЫЕ→НОВЫЕ по расписанию связки (по одному видео за интервал)."""
    if not _is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if not parts or not parts[0].isdigit():
        await message.answer(
            "Использование: <code>/backfill &lt;connection_id&gt; [N]</code>\n"
            "N — сколько самых старых видео взять (по умолчанию 50, максимум 1000)."
        )
        return
    conn_id = int(parts[0])
    n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 50
    n = max(1, min(n, 1000))

    async with get_session() as session:
        conn = await session.get(Connection, conn_id)
        if conn is None:
            await message.answer("⚠️ Связка не найдена.")
            return
        source = await session.get(SourceChannel, conn.source_channel_id)
        sched_mode = conn.schedule_mode
        interval = conn.interval_minutes
        post_times = conn.post_times
        tz = conn.tz
    if source is None:
        await message.answer("⚠️ У связки нет источника.")
        return
    if source.platform != "youtube":
        await message.answer("⚠️ Бэкфилл архива пока поддержан только для YouTube.")
        return

    await message.answer(f"⏳ Собираю архив «{source.channel_title}» (до {n} видео)…")
    try:
        entries = await asyncio.to_thread(
            fetch_channel_archive, source.channel_id, n
        )
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"❌ Не удалось получить архив: {exc}")
        return
    if not entries:
        await message.answer("⚠️ Архив пуст или канал недоступен.")
        return

    now = datetime.now(timezone.utc)
    running = await _last_scheduled_at(conn_id)
    created = 0
    first_at = last_at = None
    async with get_session() as session:
        for entry in entries:
            sched = compute_scheduled_at(
                mode=sched_mode,
                interval_minutes=interval,
                post_times=post_times,
                tz_name=tz,
                last_scheduled=running,
                now=now,
            )
            stmt = (
                insert(Job)
                .values(
                    connection_id=conn_id,
                    source_video_id=entry.video_id,
                    video_url=entry.url,
                    title=entry.title,
                    status=JOB_PENDING,
                    scheduled_at=sched,
                )
                .on_conflict_do_nothing(constraint="uq_job_source_video")
            )
            res = await session.execute(stmt)
            if res.rowcount:
                created += 1
                first_at = first_at or sched
                last_at = sched
            running = sched

    if not created:
        await message.answer(
            "ℹ️ Новых видео не добавлено — все архивные ролики уже в очереди/опубликованы."
        )
        return
    tail = (
        f"\nПервое: {first_at:%d.%m %H:%M} · последнее: {last_at:%d.%m %H:%M} (UTC)"
        if first_at and last_at else ""
    )
    note = (
        "\n⚠️ Расписание связки «immediate» — видео пойдут так быстро, как "
        "позволит дневная квота проекта (6/день). Для ровного потока поставь "
        "интервал в настройках связки."
        if sched_mode not in ("interval", "times") else ""
    )
    await message.answer(
        f"✅ В очередь поставлено <b>{created}</b> видео из архива "
        f"«{source.channel_title}» (старые → новые).{tail}{note}"
    )


@router.message(Command("republish"))
async def cmd_republish(message: Message, command: CommandObject) -> None:
    """/republish <connection_id> — заново опубликовать ПОСЛЕДНЕЕ видео связки (сбросить опубликованный job в очередь)."""
    if not _is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: <code>/republish &lt;connection_id&gt;</code>")
        return
    conn_id = int(arg)
    async with get_session() as session:
        job = await session.scalar(
            select(Job)
            .where(Job.connection_id == conn_id, Job.status == JOB_PUBLISHED)
            .order_by(Job.id.desc())
            .limit(1)
        )
        if job is None:
            await message.answer(
                "⚠️ У связки нет опубликованных видео для повторной заливки."
            )
            return
        title = job.title
        job.status = JOB_PENDING
        job.scheduled_at = datetime.now(timezone.utc)
        job.youtube_video_id = None
        job.error = None
    await message.answer(
        f"♻️ «{title}» снова в очереди (связка #{conn_id}).\n"
        "Бот заново скачает и опубликует в ближайшие ~5–10 мин."
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """/stats — сводка по боту: пользователи, аккаунты, связки, публикации."""
    if not _is_admin(message.from_user.id):
        return
    now = datetime.now(timezone.utc)
    async with get_session() as session:
        users = await session.scalar(select(func.count()).select_from(User)) or 0
        active = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(or_(User.trial_until > now, User.subscription_until > now))
        ) or 0
        paid = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.subscription_until > now)
        ) or 0
        accounts = await session.scalar(
            select(func.count()).select_from(PublishAccount)
        ) or 0
        conns_total = await session.scalar(
            select(func.count()).select_from(Connection)
        ) or 0
        conns_active = await session.scalar(
            select(func.count())
            .select_from(Connection)
            .where(Connection.is_active.is_(True))
        ) or 0
        published = await session.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.status == JOB_PUBLISHED)
        ) or 0
    await message.answer(
        "📊 <b>Статистика PostiqBot</b>\n\n"
        f"👥 Пользователей всего: <b>{users}</b>\n"
        f"✅ С активным доступом: <b>{active}</b> (из них платных: {paid})\n"
        f"🔗 Подключённых аккаунтов: <b>{accounts}</b>\n"
        f"🔁 Связок: <b>{conns_active}</b> активных / {conns_total} всего\n"
        f"🎬 Опубликовано видео: <b>{published}</b>"
    )


@router.message(Command("private"))
async def cmd_private(message: Message, command: CommandObject) -> None:
    """/private on|off — приватный режим (пред-запуск): бот только для админов."""
    if not _is_admin(message.from_user.id):
        return
    from bot.middlewares.private_mode import is_private, set_private

    arg = (command.args or "").strip().lower()
    if arg in ("on", "вкл", "1", "true"):
        set_private(True)
        await message.answer("🔒 Приватный режим <b>ВКЛЮЧЁН</b> — бот отвечает только админам.")
    elif arg in ("off", "выкл", "0", "false"):
        set_private(False)
        await message.answer("🌍 Приватный режим <b>ВЫКЛЮЧЕН</b> — бот открыт для всех.")
    else:
        now = "🔒 ВКЛ" if is_private() else "🌍 ВЫКЛ"
        await message.answer(
            f"Приватный режим сейчас: <b>{now}</b>\n"
            "Использование: <code>/private on</code> или <code>/private off</code>\n\n"
            "⚠️ Команда действует до перезапуска. Чтобы режим переживал рестарт — "
            "выстави <code>PRIVATE_MODE=true</code> в <code>.env</code>."
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
        "<b>/backfill</b> &lt;connection_id&gt; [N] — залить архив источника "
        "старые→новые по расписанию (по одному за интервал); N — сколько брать "
        "(умолч. 50, макс. 1000)\n"
        "<b>/republish</b> &lt;connection_id&gt; — заново опубликовать последнее "
        "видео связки (если удалил вручную)\n"
        "<b>/stats</b> — сводка: пользователи, аккаунты, связки, публикации\n"
        "<b>/private</b> on|off — пред-запуск: бот только для админов\n"
        "<b>/help</b> — этот список\n\n"
        "<i>Команды видны только админам из ADMIN_IDS; остальным бот не отвечает.</i>"
    )
