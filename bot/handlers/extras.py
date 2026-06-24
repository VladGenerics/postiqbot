"""Гайд, подписка (Telegram Stars) и поддержка."""
from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from bot.config import get_settings
from bot.db.models import User
from bot.db.session import get_session
from bot.handlers.start import ensure_user
from bot.services.subscription import grant_subscription, status_text

logger = logging.getLogger("postiqbot.extras")

router = Router(name="extras")


_GUIDE = (
    "📖 <b>Как пользоваться PostiqBot</b>\n\n"
    "Бот автоматически забирает новые видео с канала-источника и публикует их "
    "на твой канал (YouTube или TikTok) по расписанию.\n\n"
    "<b>1. Подключи свой канал</b>\n"
    "«🔗 Подключить YouTube» или «🎵 Подключить TikTok» — вход через официальный "
    "OAuth. Это куда бот будет публиковать.\n\n"
    "<b>2. Добавь источник</b>\n"
    "«📡 Добавить источник» → пришли ссылку на канал (YouTube @handle или "
    "ссылку на профиль TikTok). Бот начнёт следить за новыми видео.\n\n"
    "<b>3. Настрой связку</b>\n"
    "«📋 Мои подключения» → выбери связку:\n"
    "• ⏰ <b>Расписание</b> — сразу / интервал / по времени\n"
    "• 🖼 <b>Оверлей</b> — картинка или GIF поверх видео (с превью)\n"
    "• 👁 <b>Доступ</b> — для YouTube: приватное/по ссылке/публичное\n"
    "• ⏸ пауза / 🗑 удаление\n\n"
    "<b>Что важно знать</b>\n"
    "• Бот публикует только <b>новые</b> видео (старые не заливает).\n"
    "• TikTok-публикация приходит в «черновики/инбокс» — финально публикуешь сам.\n"
    "• Видео заливаются как <b>private</b> по умолчанию (YouTube) — проверь перед открытием.\n\n"
    "<b>Доступ</b>\n"
    "Первые дни — бесплатный триал. Дальше — подписка («💳 Подписка»).\n"
    "Вопросы — «✍️ Поддержка»."
)


@router.callback_query(F.data == "guide")
async def show_guide(callback: CallbackQuery) -> None:
    await callback.message.answer(_GUIDE)
    await callback.answer()


@router.callback_query(F.data == "subscription")
async def subscription_menu(callback: CallbackQuery) -> None:
    await ensure_user(callback.from_user.id)
    settings = get_settings()
    if callback.from_user.id in settings.admin_id_set:
        status = "♾ Безлимитный доступ (админ)"
    else:
        async with get_session() as session:
            user = await session.get(User, callback.from_user.id)
        status = status_text(user) if user else "Доступ не найден."
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=f"⭐ Оплатить {settings.subscription_stars} — {settings.subscription_days} дн.",
                callback_data="buy_sub",
            )
        ]]
    )
    await callback.message.answer(
        f"💳 <b>Подписка</b>\n\n{status}\n\n"
        f"Оплата через Telegram Stars — {settings.subscription_stars} ⭐ за "
        f"{settings.subscription_days} дней доступа.",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data == "buy_sub")
async def buy_subscription(callback: CallbackQuery, bot: Bot) -> None:
    settings = get_settings()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Подписка PostiqBot",
        description=f"Доступ к авто-репостингу на {settings.subscription_days} дней.",
        payload="postiq_subscription",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Подписка", amount=settings.subscription_stars)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message) -> None:
    settings = get_settings()
    until = await grant_subscription(message.from_user.id, settings.subscription_days)
    await message.answer(
        f"✅ Оплата прошла! Подписка активна до <b>{until:%d.%m.%Y}</b>. Спасибо! 🙌"
    )


class SupportFlow(StatesGroup):
    waiting_message = State()


@router.callback_query(F.data == "support")
async def support_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SupportFlow.waiting_message)
    await callback.message.answer(
        "✍️ Напиши своё сообщение/вопрос одним сообщением — я передам в поддержку."
    )
    await callback.answer()


@router.message(SupportFlow.waiting_message)
async def support_forward(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    if not message.text:
        await message.answer("Пришли текстом, пожалуйста.")
        return
    uname = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else f"id {message.from_user.id}"
    )
    sent = False
    for admin_id in get_settings().admin_id_set:
        try:
            await bot.send_message(
                admin_id,
                f"✍️ <b>Поддержка</b> от {uname} (id <code>{message.from_user.id}</code>):\n\n"
                f"{message.text}",
            )
            sent = True
        except Exception:  # noqa: BLE001
            logger.warning("Не смог доставить сообщение поддержки админу %s", admin_id)
    await message.answer(
        "✅ Отправлено в поддержку — ответим как сможем."
        if sent
        else "⚠️ Поддержка временно недоступна, попробуй позже."
    )


@router.message(F.reply_to_message.text.contains("Поддержка от"))
async def admin_reply(message: Message, bot: Bot) -> None:
    """Админ отвечает Reply на пересланное сообщение поддержки → доставляем юзеру."""
    if message.from_user.id not in get_settings().admin_id_set:
        return
    if not message.text:
        return
    m = re.search(r"id\s+(\d+)", message.reply_to_message.text)
    if not m:
        await message.reply("Не нашёл id пользователя в исходном сообщении.")
        return
    user_id = int(m.group(1))
    try:
        await bot.send_message(user_id, f"💬 <b>Ответ поддержки:</b>\n\n{message.text}")
        await message.reply("✅ Доставлено пользователю.")
    except Exception:  # noqa: BLE001
        await message.reply("⚠️ Не удалось доставить (юзер не писал боту / заблокировал).")
