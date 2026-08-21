"""aiohttp web-приложение: принимает редирект Google после согласия пользователя."""
from __future__ import annotations

import asyncio
import html
import logging

from aiogram import Bot
from aiohttp import web
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from bot.config import get_settings
from bot.db.models import OAuthProject, PublishAccount
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services import login_prompts
from bot.services.crypto import decrypt, encrypt
from bot.services.oauth_state import decode_state
from bot.services.youtube_api import get_my_channel
from bot.services.youtube_oauth import exchange_code
from bot.ui import autodelete
from bot.web.pages import add_pages, result_page, web_lang
from bot.web.payment_callback import add_payment_routes
from bot.web.tiktok_callback import tiktok_callback

logger = logging.getLogger("postiqbot.oauth")

_TXT = {
    "ru": {
        "ok": ("Канал подключён", "Канал «{name}» подключён к боту."),
        "denied": ("Доступ не выдан", "Ты не подтвердил доступ к YouTube-каналу."),
        "bad": ("Некорректный запрос", "Ссылка пришла без кода подтверждения."),
        "expired": ("Ссылка устарела", "Запроси подключение заново в боте."),
        "no_project": ("Проект не найден", "Запроси подключение заново в боте."),
        "failed": ("Ошибка подключения", "Google не выдал доступ. Попробуй ещё раз."),
    },
    "en": {
        "ok": ("Channel connected", "The channel “{name}” is now linked to the bot."),
        "denied": ("Access not granted", "You didn't approve access to your YouTube channel."),
        "bad": ("Invalid request", "The redirect came back without an authorization code."),
        "expired": ("Link expired", "Request the connection again in the bot."),
        "no_project": ("Project not found", "Request the connection again in the bot."),
        "failed": ("Connection failed", "Google didn't grant access. Please try again."),
    },
}


def _fail(
    request: web.Request, key: str, detail: str = "", lang: str | None = None
) -> web.Response:
    lang = lang or web_lang(request)
    title, text = _TXT[lang][key]
    return result_page(
        title, text, lang=lang, ok=False, platform="youtube",
        detail=html.escape(detail) if detail else "",
    )


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
        return _fail(request, "denied", error)

    code = request.query.get("code")
    state = request.query.get("state")
    if not code or not state:
        return _fail(request, "bad")

    try:
        telegram_id, project_id = decode_state(state)
    except Exception:
        return _fail(request, "expired")

    lang = await user_lang(telegram_id)

    async with get_session() as session:
        project = await session.scalar(
            select(OAuthProject).where(OAuthProject.id == project_id)
        )
    if project is None:
        return _fail(request, "no_project", lang=lang)

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
            raise ValueError("Google returned no refresh_token (revoke access and retry)")
        channel_id, channel_title = await asyncio.to_thread(get_my_channel, creds)
    except Exception as exc:  # noqa: BLE001
        logger.exception("OAuth exchange failed")
        return _fail(request, "failed", str(exc), lang=lang)

    await _save_account(
        telegram_id, project.id, channel_id, channel_title, creds.refresh_token
    )

    await login_prompts.clear(bot, telegram_id, "youtube")
    try:
        msg = await bot.send_message(
            telegram_id,
            t("acc_connected_youtube", lang, title=html.escape(channel_title)),
        )
        autodelete(msg, 20.0)
    except Exception:  # noqa: BLE001
        logger.warning("Не смог уведомить пользователя %s", telegram_id)

    title, text = _TXT[lang]["ok"]
    return result_page(
        title, text.format(name=html.escape(channel_title)), lang=lang, platform="youtube"
    )


def build_web_app(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/oauth/callback", oauth_callback)
    app.router.add_get("/tiktok/callback", tiktok_callback)
    app.router.add_get("/healthz", lambda r: web.Response(text="ok"))
    add_pages(app)
    add_payment_routes(app)
    return app
