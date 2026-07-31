"""aiohttp-роут: приём редиректа TikTok после согласия и сохранение аккаунта."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiohttp import web
from sqlalchemy.dialects.postgresql import insert

from bot.config import get_settings
from bot.db.models import PublishAccount
from bot.db.session import get_session
from bot.services.crypto import encrypt
from bot.services.oauth_state import decode_simple_state
from bot.services.tiktok_oauth import exchange_code, get_user_info
from bot.ui import autodelete

logger = logging.getLogger("postiqbot.tiktok_oauth")


def _html(message: str) -> web.Response:
    app = get_settings().site_app_name or "PosttiqBot"
    body = (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{app}</title></head>"
        "<body style='font-family:sans-serif;max-width:480px;margin:60px auto;"
        f"text-align:center'>{message}"
        "<p style='color:#888'>Можно вернуться в Telegram.</p></body></html>"
    )
    return web.Response(text=body, content_type="text/html")


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
        return _html(f"<h2>❌ Доступ не выдан</h2><p>{request.query.get('error_description', '')}</p>")

    code = request.query.get("code")
    state = request.query.get("state")
    if not code or not state:
        return _html("<h2>❌ Некорректный запрос</h2>")

    try:
        telegram_id = decode_simple_state(state)
    except Exception:
        return _html("<h2>❌ Ссылка устарела</h2><p>Запроси подключение заново в боте.</p>")

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
        return _html(f"<h2>❌ Ошибка подключения</h2><p>{exc}</p>")

    await _save_account(telegram_id, open_id, name, refresh_token)

    try:
        msg = await bot.send_message(
            telegram_id,
            f"✅ TikTok <b>{name}</b> подключён!\n"
            "Теперь можно выбрать его как канал публикации при создании связки.",
        )
        autodelete(msg)
    except Exception:  # noqa: BLE001
        logger.warning("Не смог уведомить пользователя %s", telegram_id)

    return _html(f"<h2>✅ TikTok «{name}» подключён</h2>")
