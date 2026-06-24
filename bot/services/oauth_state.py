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
