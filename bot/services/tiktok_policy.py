"""Правила TikTok Direct Post, собранные в одном месте."""
from __future__ import annotations

from datetime import datetime

from bot.config import get_settings

INTERACTION_BLOCKERS = {
    "tt_disable_comment": "comment_disabled",
    "tt_disable_duet": "duet_disabled",
    "tt_disable_stitch": "stitch_disabled",
}

POST_FIELDS = (
    "tt_privacy",
    "tt_disable_comment",
    "tt_disable_duet",
    "tt_disable_stitch",
    "tt_brand_organic",
    "tt_brand_content",
)


def is_direct_post(dest_platform: str | None, source_platform: str | None) -> bool:
    """Публиковать через Direct Post (сразу в ленту), а не в черновики."""
    settings = get_settings()
    if dest_platform != "tiktok" or not settings.tiktok_direct_post:
        return False
    if source_platform == "tiktok":
        return True
    return settings.tiktok_direct_any_source


def is_auto_post(
    dest_platform: str | None,
    source_platform: str | None,
    *,
    tt_auto: bool,
    tt_privacy: str | None,
    tt_consent_at: datetime | None,
) -> bool:
    """Публиковать сразу после скачивания, без карточки на каждый пост."""
    return (
        is_direct_post(dest_platform, source_platform)
        and bool(tt_auto)
        and bool(tt_privacy)
        and tt_consent_at is not None
    )


def needs_confirm_card(
    dest_platform: str | None,
    source_platform: str | None,
    *,
    tt_auto: bool,
    tt_privacy: str | None,
    tt_consent_at: datetime | None,
) -> bool:
    """Нужна ли карточка подтверждения перед публикацией этого видео."""
    if not is_direct_post(dest_platform, source_platform):
        return False
    return not is_auto_post(
        dest_platform,
        source_platform,
        tt_auto=tt_auto,
        tt_privacy=tt_privacy,
        tt_consent_at=tt_consent_at,
    )


def effective_toggles(info: dict, **flags: bool) -> dict[str, bool]:
    """Свести сохранённые настройки взаимодействий со свежим creator_info."""
    result = dict(flags)
    for field, blocked_key in INTERACTION_BLOCKERS.items():
        if field in result and info.get(blocked_key):
            result[field] = True
    return result


def overlay_allowed(dest_platform: str | None, source_platform: str | None) -> bool:
    """Можно ли накладывать оверлей на видео этой связки."""
    return not is_direct_post(dest_platform, source_platform)
