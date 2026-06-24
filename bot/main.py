"""Точка входа PostiqBot."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiohttp import web

from bot.config import get_settings
from bot.handlers import (
    accounts,
    admin,
    connections,
    extras,
    navigation,
    sources,
    start,
)
from bot.scheduler import setup_scheduler
from bot.web.oauth_callback import build_web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("postiqbot")


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(navigation.router)
    dp.include_router(accounts.router)
    dp.include_router(sources.router)
    dp.include_router(connections.router)
    dp.include_router(extras.router)
    dp.include_router(admin.router)
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
    scheduler.start()

    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="tariffs", description="💳 Тарифы"),
        BotCommand(command="connections", description="📋 Мои подключения"),
        BotCommand(command="guide", description="📖 Как пользоваться"),
        BotCommand(command="referral", description="🎁 Пригласить друга"),
        BotCommand(command="support", description="✍️ Поддержка"),
        BotCommand(command="policy", description="🔐 Политика конфиденциальности"),
        BotCommand(command="terms", description="📄 Пользовательское соглашение"),
    ])

    logger.info("PostiqBot запускается (long polling)…")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("PostiqBot остановлен.")
