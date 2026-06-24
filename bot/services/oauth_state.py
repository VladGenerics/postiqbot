"""Подписанный OAuth state: переносит telegram_id и project_id через редирект Google."""
from __future__ import annotations

from bot.services.crypto import decrypt, encrypt

STATE_TTL_SECONDS = 600


def encode_state(telegram_id: int, project_id: int) -> str:
    return encrypt(f"{telegram_id}:{project_id}")


def decode_state(state: str) -> tuple[int, int]:
    """Вернуть (telegram_id, project_id). Бросает при истёкшем/невалидном state."""
    raw = decrypt(state, ttl=STATE_TTL_SECONDS)
    tid, pid = raw.split(":")
    return int(tid), int(pid)


def encode_simple_state(telegram_id: int) -> str:
    """State только с telegram_id (для TikTok — там нет project_id)."""
    return encrypt(str(telegram_id))


def decode_simple_state(state: str) -> int:
    return int(decrypt(state, ttl=STATE_TTL_SECONDS))
