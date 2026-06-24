"""Шифрование секретов (refresh-токены, client_secret) через Fernet."""
from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet

from bot.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_settings().fernet_key.encode())


def encrypt(plaintext: str) -> str:
    """Зашифровать строку → base64-токен для хранения в БД."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str, ttl: int | None = None) -> str:
    """Расшифровать строку. ttl (сек) — максимальный возраст токена (для OAuth state)."""
    return _fernet().decrypt(token.encode(), ttl=ttl).decode()
