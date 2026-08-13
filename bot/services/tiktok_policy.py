"""Правила TikTok Direct Post, собранные в одном месте."""
from __future__ import annotations

from bot.config import get_settings


def is_direct_post(dest_platform: str | None, source_platform: str | None) -> bool:
    """Публиковать через Direct Post (сразу в ленту), а не в черновики."""
    return (
        dest_platform == "tiktok"
        and source_platform == "tiktok"
        and get_settings().tiktok_direct_post
    )


def overlay_allowed(dest_platform: str | None, source_platform: str | None) -> bool:
    """Можно ли накладывать оверлей на видео этой связки."""
    return not is_direct_post(dest_platform, source_platform)
