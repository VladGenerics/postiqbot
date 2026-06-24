"""Форс-тест: берёт САМОЕ СВЕЖЕЕ видео активного источника, создаёт job."""
import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from bot.config import get_settings
from bot.db.models import Connection, Job, SourceChannel
from bot.db.session import get_session
from bot.services.rss import fetch_feed
from bot.services.tiktok_source import fetch_recent_tiktok
from bot.services.downloader import process_pending
from bot.services.publisher import process_scheduled

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main():
    async with get_session() as s:
        row = (
            await s.execute(
                select(
                    Connection.id,
                    SourceChannel.platform,
                    SourceChannel.channel_id,
                    SourceChannel.channel_title,
                )
                .join(SourceChannel, SourceChannel.id == Connection.source_channel_id)
                .where(Connection.is_active.is_(True))
                .order_by(Connection.id.desc())
            )
        ).first()
    if row is None:
        print("Нет активных связок. Подключи канал и источник в боте."); return
    conn_id, platform, src_channel_id, src_title = row
    print(f"Источник [{platform}]: {src_title} ({src_channel_id}), connection={conn_id}")

    if platform == "tiktok":
        feed = await fetch_recent_tiktok(src_channel_id)
    else:
        feed = await fetch_feed(src_channel_id)
    if not feed or not feed.entries:
        print("RSS пуст — нечего публиковать."); return
    e = feed.entries[0]
    print(f"Свежее видео: {e.video_id} | {e.title[:60]} | {e.url}")

    async with get_session() as s:
        await s.execute(
            insert(Job)
            .values(connection_id=conn_id, source_video_id=e.video_id,
                    video_url=e.url, title=e.title, status="pending")
            .on_conflict_do_nothing(constraint="uq_job_source_video")
        )

    n_dl = await process_pending(limit=1)
    print(f"скачано: {n_dl}")

    bot = Bot(token=get_settings().bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        n_pub = await process_scheduled(bot, limit=1)
        print(f"опубликовано: {n_pub}")
    finally:
        await bot.session.close()

    async with get_session() as s:
        jobs = (await s.scalars(select(Job).order_by(Job.id.desc()).limit(3))).all()
        print("\n=== Последние job'ы ===")
        for j in jobs:
            print(f"  job {j.id}: {j.status} | yt={j.youtube_video_id} | err={(j.error or '')[:80]} | {(j.title or '')[:40]}")


if __name__ == "__main__":
    asyncio.run(main())
