"""Единое меню на inline-кнопках — одно сообщение, которое редактируется «на месте»."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from bot.config import get_settings
from bot.db.models import Connection, PublishAccount, User
from bot.db.session import get_session
from bot.handlers.start import ensure_user
from bot.i18n import label, set_user_lang, t, user_lang
from bot.services.subscription import status_text
from bot.ui import show_screen

router = Router(name="menu")


def _tr(ru: str, en: str, lang: str) -> str:
    return en if lang == "en" else ru


def _btn(ru: str, en: str, lang: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=_tr(ru, en, lang), callback_data=data)


def _back(screen: str, lang: str) -> list[InlineKeyboardButton]:
    return [_btn("⬅️ Назад", "⬅️ Back", lang, f"nav:{screen}")]


async def _status_line(user_id: int, lang: str) -> str:
    settings = get_settings()
    if user_id in settings.admin_id_set:
        return t("status_admin", lang)
    async with get_session() as session:
        user = await session.get(User, user_id)
    return status_text(user, lang) if user else "—"


async def _profile_caption(user_id: int, lang: str) -> str:
    async with get_session() as session:
        accounts = await session.scalar(
            select(func.count()).select_from(PublishAccount).where(
                PublishAccount.user_id == user_id
            )
        )
        connections = await session.scalar(
            select(func.count()).select_from(Connection).where(
                Connection.user_id == user_id
            )
        )
        invited = await session.scalar(
            select(func.count()).select_from(User).where(User.referred_by == user_id)
        )
    status = await _status_line(user_id, lang)
    return t("profile_body", lang, status=status, accounts=accounts or 0,
             connections=connections or 0, invited=invited or 0)


async def _referral_caption(user_id: int, lang: str, bot: Bot) -> str:
    settings = get_settings()
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user_id}"
    async with get_session() as session:
        invited = await session.scalar(
            select(func.count()).select_from(User).where(User.referred_by == user_id)
        )
        paid = await session.scalar(
            select(func.count()).select_from(User).where(
                User.referred_by == user_id, User.referral_rewarded.is_(True)
            )
        )
    return t("referral", lang, bonus=settings.referral_bonus_days, link=link,
             invited=invited or 0, paid=paid or 0)


def _plan_card(plan: str, lang: str) -> str:
    """Описание одного плана для экрана выбора периода."""
    from bot.config import fmt_limit

    s = get_settings()
    p = s.plans[plan]
    accs, vids = fmt_limit(p["accounts"]), fmt_limit(p["videos"])
    return t("plan_card", lang, plan=s.plan_label(plan), accounts=accs, videos=vids,
             m_rub=p["month"]["rub"], m_star=p["month"]["stars"],
             f_rub=p["forever"]["rub"], f_star=p["forever"]["stars"])


async def _build(screen: str, user_id: int, lang: str, bot: Bot) -> tuple[str, str, InlineKeyboardMarkup]:
    settings = get_settings()

    if screen == "root":
        rows = [
            [_btn("➕ Подключения", "➕ Connections", lang, "nav:connections"),
             _btn("👤 Профиль", "👤 Profile", lang, "nav:profile")],
            [_btn("💎 Тарифы", "💎 Plans", lang, "nav:tariffs"),
             _btn("🛠 Поддержка", "🛠 Support", lang, "nav:support")],
            [_btn("⚙️ Ещё", "⚙️ More", lang, "nav:more")],
        ]
        return "start", t("menu_root", lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "connections":
        rows = [
            [_btn("📋 Мои подключения", "📋 My connections", lang, "nav:mylist")],
            [_btn("➕ Новое подключение", "➕ New connection", lang, "nav:newconn")],
            _back("root", lang),
        ]
        return "connections", t("menu_connections", lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "newconn":
        rows = [
            [_btn("🔗 Подключить аккаунт", "🔗 Connect account", lang, "nav:connect")],
            [_btn("➕ Добавить источник", "➕ Add source", lang, "nav:addsrc")],
            _back("connections", lang),
        ]
        return "connections", t("menu_new_conn", lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "connect":
        rows = [
            [InlineKeyboardButton(text=label("youtube", lang), callback_data="connect_youtube")],
            [InlineKeyboardButton(text=label("tiktok", lang), callback_data="connect_tiktok")],
            _back("newconn", lang),
        ]
        return "connect", label("choose_platform", lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "profile":
        rows = [
            [_btn("👥 Рефералка", "👥 Referrals", lang, "nav:referral")],
            _back("root", lang),
        ]
        return "profile", await _profile_caption(user_id, lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "referral":
        rows = [_back("profile", lang)]
        return "referral", await _referral_caption(user_id, lang, bot), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "tariffs":
        rows = [
            [_btn("💎 Купить тариф", "💎 Buy a plan", lang, "nav:buy")],
            [_btn("⭐ Моя подписка", "⭐ My subscription", lang, "nav:mysub")],
            _back("root", lang),
        ]
        return "tariffs", t("menu_tariffs", lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "buy":
        rows = [
            [InlineKeyboardButton(
                text=f"{settings.plan_label(pl)} — {settings.plans[pl]['month']['rub']} ₽/мес",
                callback_data=f"nav:plan_{pl}",
            )]
            for pl in settings.plans
        ]
        rows.append(_back("tariffs", lang))
        return "tariffs", t("buy_caption", lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen.startswith("plan_"):
        pl = screen[len("plan_"):]
        if pl not in settings.plans:
            pl = "starter"
        rows = [
            [InlineKeyboardButton(
                text=t("btn_buy_month", lang, rub=settings.plans[pl]["month"]["rub"]),
                callback_data=f"buy:{pl}:month:rub")],
            [InlineKeyboardButton(
                text=t("btn_buy_month_star", lang, stars=settings.plans[pl]["month"]["stars"]),
                callback_data=f"buy:{pl}:month:stars")],
            [InlineKeyboardButton(
                text=t("btn_buy_forever", lang, rub=settings.plans[pl]["forever"]["rub"]),
                callback_data=f"buy:{pl}:forever:rub")],
            [InlineKeyboardButton(
                text=t("btn_buy_forever_star", lang, stars=settings.plans[pl]["forever"]["stars"]),
                callback_data=f"buy:{pl}:forever:stars")],
            _back("buy", lang),
        ]
        return "tariffs", _plan_card(pl, lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "mysub":
        status = await _status_line(user_id, lang)
        rows = [
            [_btn("💎 Купить тариф", "💎 Buy a plan", lang, "nav:buy")],
            _back("tariffs", lang),
        ]
        return "tariffs", t("my_sub_body", lang, status=status), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "more":
        rows = [
            [_btn("📖 Как пользоваться", "📖 How to use", lang, "nav:guide")],
            [_btn("🌐 Сменить язык", "🌐 Change language", lang, "nav:lang")],
            [_btn("📄 Документы", "📄 Documents", lang, "nav:documents")],
            _back("root", lang),
        ]
        return "more", t("menu_more", lang), InlineKeyboardMarkup(inline_keyboard=rows)

    if screen == "guide":
        return "guide", t("guide", lang), InlineKeyboardMarkup(inline_keyboard=[_back("more", lang)])

    if screen == "documents":
        contact = f" — {settings.support_contact}" if settings.support_contact else ""
        caption = t("documents_title", lang) + t("support_line", lang, contact=contact)
        rows = [
            [InlineKeyboardButton(text=t("btn_privacy", lang), url=settings.privacy_url)],
            [InlineKeyboardButton(text=t("btn_terms", lang), url=settings.terms_url)],
            _back("more", lang),
        ]
        return "documents", caption, InlineKeyboardMarkup(inline_keyboard=rows)

    return await _build("root", user_id, lang, bot)


async def open_menu(message: Message, user_id: int, screen: str = "root",
                    *, edit: bool = False, bot: Bot | None = None) -> None:
    """Показать/перерисовать меню на экране screen."""
    await ensure_user(user_id)
    lang = await user_lang(user_id)
    icon, caption, kb = await _build(screen, user_id, lang, bot or message.bot)
    await show_screen(message, icon, caption, kb, edit=edit, lang=lang)


async def _enter_addsrc(message: Message, state: FSMContext, user_id: int, lang: str) -> None:
    from bot.handlers.sources import SourceFlow, _user_accounts

    accounts = await _user_accounts(user_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back("newconn", lang)])
    if not accounts:
        await show_screen(message, "source", t("source_need_account", lang), kb, edit=True, lang=lang)
        return
    await state.set_state(SourceFlow.waiting_link)
    await show_screen(message, "source", t("source_prompt", lang), kb, edit=True, lang=lang)


async def _enter_support(message: Message, state: FSMContext, lang: str) -> None:
    from bot.support_bot import support_username

    uname = support_username()
    if uname:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("support_open_btn", lang), url=f"https://t.me/{uname}")],
            _back("root", lang),
        ])
        await show_screen(message, "support", t("support_open", lang), kb, edit=True, lang=lang)
        return
    from bot.handlers.extras import SupportFlow

    await state.set_state(SupportFlow.waiting_message)
    kb = InlineKeyboardMarkup(inline_keyboard=[_back("root", lang)])
    await show_screen(message, "support", t("support_prompt", lang), kb, edit=True, lang=lang)


async def _show_mylist(message: Message, user_id: int, lang: str) -> None:
    from bot.handlers.connections import _list_markup, _load_connections

    connections = await _load_connections(user_id)
    if not connections:
        kb = InlineKeyboardMarkup(inline_keyboard=[_back("connections", lang)])
        await show_screen(message, "connections", t("mylist_empty", lang), kb, edit=True, lang=lang)
        return
    rows = list(_list_markup(connections).inline_keyboard)
    rows.append(_back("connections", lang))
    await show_screen(message, "connections", t("mylist_title", lang),
                      InlineKeyboardMarkup(inline_keyboard=rows), edit=True, lang=lang)


@router.callback_query(F.data.startswith("nav:"))
async def on_nav(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    screen = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    message = callback.message
    lang = await user_lang(user_id)

    if screen not in ("addsrc", "support"):
        await state.set_state(None)

    if screen == "lang":
        lang = "en" if lang == "ru" else "ru"
        await set_user_lang(user_id, lang)
        screen = "more"
    elif screen == "addsrc":
        await _enter_addsrc(message, state, user_id, lang)
        await callback.answer()
        return
    elif screen == "support":
        await _enter_support(message, state, lang)
        await callback.answer()
        return
    elif screen == "mylist":
        await _show_mylist(message, user_id, lang)
        await callback.answer()
        return

    icon, caption, kb = await _build(screen, user_id, lang, bot)
    await show_screen(message, icon, caption, kb, edit=True, lang=lang)
    await callback.answer()
