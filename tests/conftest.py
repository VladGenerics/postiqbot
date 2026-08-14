"""Общая обвязка тестов."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.update(
    {
        "BOT_TOKEN": "123456:test-token",
        "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:5432/test",
        "FERNET_KEY": Fernet.generate_key().decode(),
        "TIKTOK_DIRECT_POST": "false",
        "ADMIN_IDS": "",
    }
)

import pytest  # noqa: E402 — только после подмены окружения

from bot.config import get_settings  # noqa: E402
from bot.services import crypto  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_caches():
    """Сбросить кэши настроек до и после каждого теста."""
    get_settings.cache_clear()
    crypto._fernet.cache_clear()
    yield
    get_settings.cache_clear()
    crypto._fernet.cache_clear()
