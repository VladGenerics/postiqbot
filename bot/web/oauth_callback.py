"""aiohttp web-приложение: принимает редирект Google после согласия пользователя."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiohttp import web
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from bot.config import get_settings
from bot.db.models import OAuthProject, PublishAccount
from bot.db.session import get_session
from bot.services.crypto import decrypt, encrypt
from bot.services.oauth_state import decode_state
from bot.services.youtube_api import get_my_channel
from bot.services.youtube_oauth import exchange_code
from bot.web.pages import add_pages

logger = logging.getLogger("postiqbot.oauth")


def _html(message: str) -> web.Response:
    body = (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>PostiqBot</title></head>"
        "<body style='font-family:sans-serif;max-width:480px;margin:60px auto;"
        "text-align:center'>"
        f"{message}"
        "<p style='color:#888'>Можно вернуться в Telegram.</p></body></html>"
    )
    return web.Response(text=body, content_type="text/html")


async def _save_account(
    telegram_id: int, project_id: int, channel_id: str, channel_title: str, refresh: str
) -> None:
    async with get_session() as session:
        stmt = (
            insert(PublishAccount)
            .values(
                user_id=telegram_id,
                project_id=project_id,
                platform="youtube",
                channel_id=channel_id,
                channel_title=channel_title,
                refresh_token_enc=encrypt(refresh),
            )
            .on_conflict_do_update(
                constraint="uq_publish_channel",
                set_={
                    "project_id": project_id,
                    "channel_title": channel_title,
                    "refresh_token_enc": encrypt(refresh),
                },
            )
        )
        await session.execute(stmt)


async def oauth_callback(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    settings = get_settings()

    error = request.query.get("error")
    if error:
        return _html(f"<h2>❌ Доступ не выдан</h2><p>{error}</p>")

    code = request.query.get("code")
    state = request.query.get("state")
    if not code or not state:
        return _html("<h2>❌ Некорректный запрос</h2>")

    try:
        telegram_id, project_id = decode_state(state)
    except Exception:
        return _html("<h2>❌ Ссылка устарела</h2><p>Запроси подключение заново в боте.</p>")

    async with get_session() as session:
        project = await session.scalar(
            select(OAuthProject).where(OAuthProject.id == project_id)
        )
    if project is None:
        return _html("<h2>❌ Проект не найден</h2>")

    client_secret = decrypt(project.client_secret_enc)

    try:
        creds = await asyncio.to_thread(
            exchange_code,
            project.client_id,
            client_secret,
            settings.oauth_redirect_uri,
            code,
        )
        if not creds.refresh_token:
            raise ValueError("Google не вернул refresh_token (отзови доступ и попробуй снова)")
        channel_id, channel_title = await asyncio.to_thread(get_my_channel, creds)
    except Exception as exc:  # noqa: BLE001
        logger.exception("OAuth exchange failed")
        return _html(f"<h2>❌ Ошибка подключения</h2><p>{exc}</p>")

    await _save_account(
        telegram_id, project.id, channel_id, channel_title, creds.refresh_token
    )

    try:
        await bot.send_message(
            telegram_id,
            f"✅ Канал <b>{channel_title}</b> подключён!\n"
            "Теперь добавь источник, за которым следить.",
        )
    except Exception:  # noqa: BLE001
        logger.warning("Не смог уведомить пользователя %s", telegram_id)

    return _html(f"<h2>✅ Канал «{channel_title}» подключён</h2>")


def build_web_app(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/oauth/callback", oauth_callback)
    app.router.add_get("/healthz", lambda r: web.Response(text="ok"))
    add_pages(app)
    return app
