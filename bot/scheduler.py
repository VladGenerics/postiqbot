"""Настройка фоновых задач APScheduler: мониторинг источников и воркер конвейера."""
from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from bot.config import get_settings
from bot.services.downloader import process_pending
from bot.services.payments_service import reconcile_payments
from bot.services.publisher import process_scheduled
from bot.services.rss_monitor import poll_sources

logger = logging.getLogger("postiqbot.scheduler")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        poll_sources,
        IntervalTrigger(minutes=settings.monitor_interval_minutes),
        id="monitor",
        max_instances=1,
        coalesce=True,
        next_run_time=None,
    )

    async def pipeline_tick() -> None:
        await process_pending()
        await process_scheduled(bot)

    scheduler.add_job(
        pipeline_tick,
        IntervalTrigger(minutes=settings.publish_interval_minutes),
        id="pipeline",
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        reconcile_payments,
        IntervalTrigger(minutes=10),
        id="reconcile_payments",
        args=[bot],
        max_instances=1,
        coalesce=True,
    )

    logger.info(
        "Планировщик: монитор каждые %d мин, конвейер каждые %d мин",
        settings.monitor_interval_minutes,
        settings.publish_interval_minutes,
    )
    return scheduler
