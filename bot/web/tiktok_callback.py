"""aiohttp-роут: приём редиректа TikTok после согласия и сохранение аккаунта."""
from __future__ import annotations

import html
import logging

from aiogram import Bot
from aiohttp import web
from sqlalchemy.dialects.postgresql import insert

from bot.db.models import PublishAccount
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services import login_prompts
from bot.services.crypto import encrypt
from bot.services.oauth_state import decode_simple_state
from bot.services.tiktok_oauth import exchange_code, get_user_info
from bot.ui import autodelete
from bot.web.pages import result_page, web_lang

logger = logging.getLogger("postiqbot.tiktok_oauth")

_TXT = {
    "ru": {
        "ok": ("TikTok подключён", "Аккаунт «{name}» подключён к боту."),
        "denied": ("Доступ не выдан", "Ты не подтвердил доступ к аккаунту TikTok."),
        "bad": ("Некорректный запрос", "Ссылка пришла без кода подтверждения."),
        "expired": ("Ссылка устарела", "Запроси подключение заново в боте."),
        "failed": ("Ошибка подключения", "TikTok не выдал доступ. Попробуй ещё раз."),
    },
    "en": {
        "ok": ("TikTok connected", "The account “{name}” is now linked to the bot."),
        "denied": ("Access not granted", "You didn't approve access to your TikTok account."),
        "bad": ("Invalid request", "The redirect came back without an authorization code."),
        "expired": ("Link expired", "Request the connection again in the bot."),
        "failed": ("Connection failed", "TikTok didn't grant access. Please try again."),
    },
}


def _fail(request: web.Request, key: str, detail: str = "") -> web.Response:
    lang = web_lang(request)
    title, text = _TXT[lang][key]
    return result_page(
        title, text, lang=lang, ok=False, platform="tiktok",
        detail=html.escape(detail) if detail else "",
    )


async def _save_account(
    telegram_id: int, open_id: str, name: str, refresh_token: str
) -> None:
    async with get_session() as session:
        stmt = (
            insert(PublishAccount)
            .values(
                user_id=telegram_id,
                project_id=None,
                platform="tiktok",
                channel_id=open_id,
                channel_title=name,
                refresh_token_enc=encrypt(refresh_token),
            )
            .on_conflict_do_update(
                constraint="uq_publish_channel",
                set_={"channel_title": name, "refresh_token_enc": encrypt(refresh_token)},
            )
        )
        await session.execute(stmt)


async def tiktok_callback(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]

    if request.query.get("error"):
        return _fail(request, "denied", request.query.get("error_description", ""))

    code = request.query.get("code")
    state = request.query.get("state")
    if not code or not state:
        return _fail(request, "bad")

    try:
        telegram_id = decode_simple_state(state)
    except Exception:
        return _fail(request, "expired")

    try:
        tokens = await exchange_code(code)
        refresh_token = tokens.get("refresh_token")
        open_id = tokens.get("open_id")
        if not refresh_token or not open_id:
            raise ValueError("TikTok не вернул refresh_token/open_id")
        try:
            _, name = await get_user_info(tokens["access_token"])
        except Exception:  # noqa: BLE001
            name = "TikTok"
    except Exception as exc:  # noqa: BLE001
        logger.exception("TikTok OAuth failed")
        return _fail(request, "failed", str(exc))

    await _save_account(telegram_id, open_id, name, refresh_token)

    await login_prompts.clear(bot, telegram_id, "tiktok")
    try:
        lang = await user_lang(telegram_id)
        msg = await bot.send_message(
            telegram_id,
            t("acc_connected_tiktok", lang, title=html.escape(name)),
        )
        autodelete(msg, 20.0)
    except Exception:  # noqa: BLE001
        logger.warning("Не смог уведомить пользователя %s", telegram_id)

    lang = web_lang(request)
    title, text = _TXT[lang]["ok"]
    return result_page(
        title, text.format(name=html.escape(name)), lang=lang, platform="tiktok"
    )
