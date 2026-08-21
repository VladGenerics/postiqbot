"""Свежий access_token аккаунта TikTok + сохранение провёрнутого refresh_token."""
from __future__ import annotations

import logging

from bot.db.models import PublishAccount
from bot.db.session import get_session
from bot.services.crypto import decrypt, encrypt
from bot.services.tiktok_oauth import refresh_access_token

logger = logging.getLogger("postiqbot.tiktok_tokens")


async def access_token(account_id: int) -> str:
    """Свежий access_token для publish_account. Ротацию refresh сохраняем сразу."""
    async with get_session() as session:
        acc = await session.get(PublishAccount, account_id)
        if acc is None:
            raise ValueError(f"publish_account {account_id} not found")
        current = decrypt(acc.refresh_token_enc)

    tokens = await refresh_access_token(current)

    rotated = tokens.get("refresh_token")
    if rotated and rotated != current:
        async with get_session() as session:
            acc = await session.get(PublishAccount, account_id)
            if acc is not None:
                acc.refresh_token_enc = encrypt(rotated)
        logger.info("TikTok refresh_token провёрнут, account=%d", account_id)
    return tokens["access_token"]
