"""Подключение YouTube-аккаунта клиента через OAuth."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import get_settings
from bot.db.session import get_session
from bot.handlers.start import ensure_user
from bot.services.crypto import decrypt
from bot.services.oauth_state import encode_state
from bot.services.projects import ensure_shared_project, pick_project
from bot.services.youtube_oauth import build_auth_url

router = Router(name="accounts")


@router.callback_query(F.data == "connect_youtube")
async def connect_youtube(callback: CallbackQuery) -> None:
    settings = get_settings()
    telegram_id = callback.from_user.id
    await ensure_user(telegram_id)

    async with get_session() as session:
        await ensure_shared_project(session)
        await session.flush()
        project = await pick_project(session, owner_telegram_id=telegram_id)
        if project is None:
            await callback.message.answer(
                "⚠️ Нет доступных Google-проектов в пуле. "
                "Админу нужно добавить проект командой /addproject."
            )
            await callback.answer()
            return

        client_id = project.client_id
        client_secret = decrypt(project.client_secret_enc)
        state = encode_state(telegram_id, project.id)

    auth_url = build_auth_url(
        client_id, client_secret, settings.oauth_redirect_uri, state
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Войти через Google", url=auth_url)]
        ]
    )
    await callback.message.answer(
        "Нажми кнопку ниже и разреши доступ к своему YouTube-каналу.\n"
        "После подтверждения я пришлю сообщение, что канал подключён.\n\n"
        "<i>Ссылка действует 10 минут.</i>",
        reply_markup=kb,
    )
    await callback.answer()
