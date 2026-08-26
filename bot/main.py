"""Точка входа PostiqBot."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent, Update
from aiohttp import web

from bot.config import get_settings
from bot.handlers import (
    accounts,
    admin,
    connections,
    extras,
    menu,
    navigation,
    promo,
    sources,
    start,
    tiktok_confirm,
    tiktok_settings,
)
from bot.keyboards.commands import set_global_commands
from bot.middlewares.channel_gate import ChannelGateMiddleware
from bot.middlewares.private_mode import PrivateModeMiddleware
from bot.scheduler import setup_scheduler
from bot.web.oauth_callback import build_web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("postiqbot")

_ERROR_TEXT = "Произошла ошибка, попробуйте ещё раз."


def _extract_chat_id(update: Update | None) -> int | None:
    """Достать chat_id из апдейта — куда слать отчёт об ошибке."""
    if update is None:
        return None
    for field in update.model_fields:
        obj = getattr(update, field, None)
        if obj is None:
            continue
        chat = getattr(obj, "chat", None)
        if chat is not None:
            return chat.id
        nested = getattr(obj, "message", None)
        if nested is not None and getattr(nested, "chat", None) is not None:
            return nested.chat.id
    return None


async def _global_error_handler(event: ErrorEvent, bot: Bot) -> None:
    """Последний рубеж: исключение из хендлера не должно съедать апдейт молча."""
    logger.error(
        "Необработанное исключение в апдейте update_id=%s",
        event.update.update_id if event.update else None,
        exc_info=event.exception,
    )
    chat_id = _extract_chat_id(event.update)
    if chat_id is None:
        return
    try:
        await bot.send_message(chat_id, _ERROR_TEXT)
    except Exception:  # noqa: BLE001 — юзер заблокировал бота / флуд-лимит / сеть
        logger.warning("Не смог отправить отчёт об ошибке в chat=%s", chat_id)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    allowed = get_settings().admin_id_set
    dp.message.outer_middleware(PrivateModeMiddleware(allowed))
    dp.callback_query.outer_middleware(PrivateModeMiddleware(allowed))
    dp.message.outer_middleware(ChannelGateMiddleware())
    dp.callback_query.outer_middleware(ChannelGateMiddleware())
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(navigation.router)
    dp.include_router(accounts.router)
    dp.include_router(sources.router)
    dp.include_router(connections.router)
    dp.include_router(tiktok_confirm.router)
    dp.include_router(tiktok_settings.router)
    dp.include_router(extras.router)
    dp.include_router(promo.router)
    dp.include_router(admin.router)
    dp.errors.register(_global_error_handler)
    return dp


async def _start_web(bot: Bot) -> web.AppRunner:
    settings = get_settings()
    app = build_web_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.web_host, settings.web_port)
    await site.start()
    logger.info("OAuth web-сервер слушает %s:%s", settings.web_host, settings.web_port)
    return runner


async def main() -> None:
    settings = get_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    runner = await _start_web(bot)
    scheduler = setup_scheduler(bot)
    support_bot: Bot | None = None
    support_task: asyncio.Task | None = None

    try:
        scheduler.start()

        await set_global_commands(bot)

        if settings.support_bot_token:
            from bot.support_bot import build_support_dispatcher, set_support_username

            support_bot = Bot(
                token=settings.support_bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
            me = await support_bot.get_me()
            set_support_username(me.username)
            support_dp = build_support_dispatcher()
            await support_bot.delete_webhook(drop_pending_updates=True)
            support_task = asyncio.create_task(support_dp.start_polling(support_bot))
            logger.info("Бот поддержки @%s запущен", me.username)

        logger.info("PostiqBot запускается (long polling)…")
        await bot.delete_webhook()
        await dp.start_polling(bot)
    finally:
        if support_task is not None:
            support_task.cancel()
            await asyncio.gather(support_task, return_exceptions=True)
        if support_bot is not None:
            await support_bot.session.close()
        scheduler.shutdown(wait=False)
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("PostiqBot остановлен.")
