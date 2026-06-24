"""Управление пулом Google-проектов (oauth_projects)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.db.models import OAuthProject, PublishAccount
from bot.services.crypto import encrypt


async def ensure_shared_project(session: AsyncSession) -> None:
    """Засеять общий проект из .env в пул, если его там ещё нет."""
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        return
    exists = await session.scalar(
        select(OAuthProject).where(
            OAuthProject.client_id == settings.google_client_id
        )
    )
    if exists:
        return
    session.add(
        OAuthProject(
            name="shared (env)",
            client_id=settings.google_client_id,
            client_secret_enc=encrypt(settings.google_client_secret),
            owner_telegram_id=None,
            daily_quota=settings.daily_upload_quota,
            is_active=True,
        )
    )


async def add_project(
    session: AsyncSession,
    name: str,
    client_id: str,
    client_secret: str,
    owner_telegram_id: int | None = None,
) -> OAuthProject:
    """Добавить проект в пул (секрет шифруется)."""
    project = OAuthProject(
        name=name,
        client_id=client_id,
        client_secret_enc=encrypt(client_secret),
        owner_telegram_id=owner_telegram_id,
        daily_quota=get_settings().daily_upload_quota,
        is_active=True,
    )
    session.add(project)
    await session.flush()
    return project


async def pick_project(
    session: AsyncSession, owner_telegram_id: int | None = None
) -> OAuthProject | None:
    """Выбрать активный проект с наименьшим числом привязанных аккаунтов."""
    if owner_telegram_id is not None:
        own = await session.scalar(
            select(OAuthProject).where(
                OAuthProject.owner_telegram_id == owner_telegram_id,
                OAuthProject.is_active.is_(True),
            )
        )
        if own:
            return own

    count = func.count(PublishAccount.id)
    stmt = (
        select(OAuthProject)
        .outerjoin(PublishAccount, PublishAccount.project_id == OAuthProject.id)
        .where(OAuthProject.is_active.is_(True))
        .group_by(OAuthProject.id)
        .order_by(count.asc(), OAuthProject.id.asc())
        .limit(1)
    )
    return await session.scalar(stmt)
