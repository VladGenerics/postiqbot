"""Промокоды: создание админом (/promo) и применение пользователем в карточке тарифа."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import get_settings
from bot.db.models import PromoCode, User
from bot.db.session import get_session
from bot.i18n import t, user_lang
from bot.services import promo as promo_svc
from bot.ui import ask, cleanup_ask, edit_anchor

router = Router(name="promo")


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_id_set


_USAGE = (
    "🎟 <b>Промокоды</b>\n\n"
    "<b>/promo new</b> &lt;%&gt; [тариф|all] [uses=N] [days=N] [КОД]\n"
    "  <code>/promo new 30</code> — −30% на все тарифы, без лимита, код сгенерируется\n"
    "  <code>/promo new 50 pro uses=100 days=7 CREATOR50</code>\n"
    "<b>/promo off</b> &lt;КОД&gt; / <b>/promo on</b> &lt;КОД&gt; — выключить / включить\n"
    "<b>/promo del</b> &lt;КОД&gt; — удалить\n"
    "<b>/promo</b> — список кодов\n\n"
    f"<i>Скидка в процентах, от {promo_svc.MIN_PERCENT} до {promo_svc.MAX_PERCENT}. "
    "Действует и на ₽, и на Stars. Один клиент может использовать код один раз; "
    "uses=0 — без общего лимита, без days — код бессрочный.</i>"
)

_ERRORS = {
    "no_percent": "Не понял размер скидки. Пример: <code>/promo new 30</code>",
    "bad_percent": (
        f"Скидка — от {promo_svc.MIN_PERCENT}% до {promo_svc.MAX_PERCENT}%. "
        "Для «бесплатно» есть <code>/grant</code>."
    ),
    "bad_code": "Код: латиница, цифры, «-» и «_», от 2 до 32 символов.",
    "bad_uses": "<code>uses=N</code> — целое число (0 = без лимита).",
    "bad_days": "<code>days=N</code> — целое число дней больше нуля.",
    "bad_token": "Лишний аргумент. Формат: <code>/promo new &lt;%&gt; [тариф|all] [uses=N] [days=N] [КОД]</code>",
}


def _scope(plan: str | None) -> str:
    s = get_settings()
    return s.plan_label(plan) if plan in s.plans else "все тарифы"


def _line(promo: PromoCode) -> str:
    uses = f"{promo.used_count}/{promo.max_uses}" if promo.max_uses else f"{promo.used_count}/∞"
    until = f" · до {promo.expires_at:%d.%m.%Y}" if promo.expires_at else ""
    flag = "🟢" if promo.is_active else "🔴"
    return (
        f"{flag} <code>{promo.code}</code> — −{promo.percent}% · "
        f"{_scope(promo.plan)} · использован {uses}{until}"
    )


async def _show_list(message: Message) -> None:
    async with get_session() as session:
        codes = await promo_svc.all_codes(session)
    head = "🎟 <b>Промокоды</b>\n\n" + (
        "\n".join(_line(p) for p in codes) if codes else "Пока ни одного."
    )
    await message.answer(f"{head}\n\n{_USAGE}")


async def _create(message: Message, args: list[str]) -> None:
    data, error = promo_svc.parse_new(args, get_settings().plans)
    if data is None:
        await message.answer(f"⚠️ {_ERRORS.get(error or '', 'Не понял аргументы.')}")
        return
    async with get_session() as session:
        user_given = any(promo_svc.normalize_code(a) == data.code for a in args)
        for _ in range(5):
            if await promo_svc.get(session, data.code) is None:
                break
            if user_given:
                await message.answer(f"⚠️ Код <code>{data.code}</code> уже существует.")
                return
            data.code = promo_svc.generate_code(data.percent)
        else:
            await message.answer("⚠️ Не удалось подобрать свободный код — попробуй ещё раз.")
            return
        promo = await promo_svc.create(session, data, message.from_user.id)
        line = _line(promo)
    await message.answer(f"✅ Промокод создан:\n{line}")


async def _switch(message: Message, code: str, active: bool) -> None:
    async with get_session() as session:
        promo = await promo_svc.get(session, code)
        if promo is None:
            await message.answer("⚠️ Код не найден.")
            return
        promo.is_active = active
        line = _line(promo)
    await message.answer(f"{'🟢 Включён' if active else '🔴 Выключен'}:\n{line}")


async def _delete(message: Message, code: str) -> None:
    """Удаление стирает и историю списаний (FK ON DELETE CASCADE): клиенты, успевшие использовать код."""
    async with get_session() as session:
        promo = await promo_svc.get(session, code)
        if promo is None:
            await message.answer("⚠️ Код не найден.")
            return
        name, used = promo.code, promo.used_count
        await session.delete(promo)
    await message.answer(f"🗑 Код <code>{name}</code> удалён (было списаний: {used}).")


@router.message(Command("promo"))
async def cmd_promo(message: Message, command: CommandObject) -> None:
    """/promo — список и справка; /promo new|on|off|del — управление кодами."""
    if not _is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if not parts:
        await _show_list(message)
        return
    sub = parts[0].lower()
    if sub in ("new", "add", "создать"):
        await _create(message, parts[1:])
    elif sub in ("on", "вкл"):
        await _switch(message, " ".join(parts[1:]), True)
    elif sub in ("off", "выкл"):
        await _switch(message, " ".join(parts[1:]), False)
    elif sub in ("del", "delete", "rm", "удалить"):
        await _delete(message, " ".join(parts[1:]))
    elif promo_svc.parse_percent(sub) is not None:
        await _create(message, parts)
    else:
        await message.answer(_USAGE)


class PromoFlow(StatesGroup):
    waiting_code = State()


def _plan_arg(data: str) -> str:
    """promo:<action>:<plan> → план (с проверкой: callback_data приходит извне)."""
    parts = data.split(":")
    plan = parts[2] if len(parts) > 2 else ""
    return plan if plan in get_settings().plans else next(iter(get_settings().plans))


def _retry_kb(plan: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_promo", lang), callback_data=f"promo:ask:{plan}")],
        [InlineKeyboardButton(text=t("btn_promo_back", lang), callback_data=f"nav:plan_{plan}")],
    ])


async def _plan_screen(user_id: int, lang: str, plan: str, bot: Bot):
    """Карточка тарифа (подпись + кнопки) — уже с учётом применённой скидки."""
    from bot.handlers.menu import _build

    _icon, caption, kb = await _build(f"plan_{plan}", user_id, lang, bot)
    return caption, kb


@router.callback_query(F.data.startswith("promo:ask:"))
async def cb_promo_ask(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await user_lang(callback.from_user.id)
    await state.set_state(PromoFlow.waiting_code)
    await state.update_data(promo_plan=_plan_arg(callback.data))
    await ask(callback.message, state, t("promo_prompt", lang), lang)
    await callback.answer()


@router.callback_query(F.data.startswith("promo:clear:"))
async def cb_promo_clear(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    lang = await user_lang(callback.from_user.id)
    async with get_session() as session:
        user = await session.get(User, callback.from_user.id)
        if user is not None:
            user.promo_code = None
    await state.set_state(None)
    from bot.handlers.menu import open_menu

    await open_menu(callback.message, callback.from_user.id,
                    f"plan_{_plan_arg(callback.data)}", edit=True, bot=bot)
    await callback.answer(t("promo_cleared", lang))


@router.message(PromoFlow.waiting_code)
async def promo_got_code(message: Message, state: FSMContext, bot: Bot) -> None:
    user_id = message.from_user.id
    lang = await user_lang(user_id)
    code = promo_svc.normalize_code(message.text or "")
    data = await state.get_data()
    plan = data.get("promo_plan")
    plan = plan if plan in get_settings().plans else next(iter(get_settings().plans))

    if not promo_svc.is_valid_code(code):
        await message.answer(t("promo_bad_not_found", lang))
        return

    await cleanup_ask(message, state)
    percent = 0
    async with get_session() as session:
        promo, reason = await promo_svc.check(session, code, user_id, plan)
        if promo is not None and reason is None:
            percent = promo.percent
            user = await session.get(User, user_id)
            if user is not None:
                user.promo_code = promo.code
    if promo is None or reason is not None:
        await state.clear()
        await message.answer(
            t(f"promo_bad_{reason or promo_svc.NOT_FOUND}", lang),
            reply_markup=_retry_kb(plan, lang),
        )
        return

    caption, kb = await _plan_screen(user_id, lang, plan, bot)
    if not await edit_anchor(message, state, caption, kb):
        await message.answer(caption, reply_markup=kb)
    await state.clear()
    await message.answer(t("promo_applied", lang, code=promo.code, percent=percent))
