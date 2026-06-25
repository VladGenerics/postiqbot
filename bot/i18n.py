"""Простая локализация (ru/en): метки кнопок, строки сообщений, язык юзера."""
from __future__ import annotations

from bot.db.models import User
from bot.db.session import get_session

DEFAULT_LANG = "ru"
LANGS = ("ru", "en")

LABELS: dict[str, dict[str, str]] = {
    "youtube": {"ru": "🔗 Подключить YouTube", "en": "🔗 Connect YouTube"},
    "tiktok": {"ru": "🎵 Подключить TikTok", "en": "🎵 Connect TikTok"},
    "connect": {"ru": "🔗 Подключить аккаунт", "en": "🔗 Connect account"},
    "source": {"ru": "📡 Добавить источник", "en": "📡 Add source"},
    "connections": {"ru": "📋 Мои подключения", "en": "📋 My connections"},
    "tariff": {"ru": "💳 Тарифы", "en": "💳 Plans"},
    "guide": {"ru": "📖 Как пользоваться", "en": "📖 How to use"},
    "referral": {"ru": "🎁 Пригласить друга", "en": "🎁 Invite a friend"},
    "support": {"ru": "✍️ Поддержка", "en": "✍️ Support"},
    "profile": {"ru": "👤 Профиль", "en": "👤 Profile"},
    "documents": {"ru": "📄 Документы", "en": "📄 Documents"},
    "choose_platform": {
        "ru": "Какой аккаунт подключить?",
        "en": "Which account to connect?",
    },
    "lang": {"ru": "🌐 Switch to English", "en": "🌐 На русский"},
}

T: dict[str, dict[str, str]] = {
    "welcome": {
        "ru": (
            "👋 Привет! Я <b>PostiqBot</b>.\n\n"
            "Я слежу за каналами-источниками и автоматически перезаливаю новые "
            "видео (включая Shorts) на твои YouTube/TikTok по расписанию.\n\n"
            "Пользуйся кнопками меню внизу 👇\n"
            "Начни с подключения своего канала, потом добавь источник."
        ),
        "en": (
            "👋 Hi! I'm <b>PostiqBot</b>.\n\n"
            "I watch source channels and automatically repost new videos "
            "(including Shorts) to your YouTube/TikTok on schedule.\n\n"
            "Use the menu buttons below 👇\n"
            "Start by connecting your channel, then add a source."
        ),
    },
    "lang_switched": {
        "ru": "🌐 Язык переключён на русский.",
        "en": "🌐 Language switched to English.",
    },
    "limit_accounts": {
        "ru": (
            "⚠️ На твоём тарифе можно подключить до <b>{limit}</b> аккаунтов. "
            "Удали лишний или оформи тариф побольше («💳 Тарифы»)."
        ),
        "en": (
            "⚠️ Your plan allows up to <b>{limit}</b> accounts. "
            "Remove one or upgrade your plan («💳 Plans»)."
        ),
    },
    "tariffs_caption": {
        "ru": "💳 <b>Тарифы</b>\n\n{status}\n{prices}\n\nВыбери тариф ниже 👇",
        "en": "💳 <b>Plans</b>\n\n{status}\n{prices}\n\nPick a plan below 👇",
    },
    "pay_choose": {
        "ru": "💳 Тариф на <b>{days} дней</b>. Выбери способ оплаты:",
        "en": "💳 <b>{days}-day</b> plan. Choose a payment method:",
    },
    "btn_pay_stars": {"ru": "⭐ Telegram Stars ({stars})", "en": "⭐ Telegram Stars ({stars})"},
    "btn_pay_rub": {"ru": "₽ СБП / карта ({rub} ₽)", "en": "₽ Card / SBP ({rub} ₽)"},
    "rub_soon": {
        "ru": "₽ Оплата через СБП/карту скоро подключится. Пока можно оплатить через Telegram Stars (⭐) или написать в «✍️ Поддержка».",
        "en": "₽ Card/SBP payment is coming soon. For now use Telegram Stars (⭐) or contact «✍️ Support».",
    },
    "status_admin": {"ru": "♾ Безлимитный доступ (админ)", "en": "♾ Unlimited access (admin)"},
    "profile_body": {
        "ru": (
            "👤 <b>Профиль</b>\n\n{status}\n\n"
            "🔗 Подключено аккаунтов: <b>{accounts}</b>\n"
            "📋 Активных связок: <b>{connections}</b>\n"
            "🎁 Приглашено друзей: <b>{invited}</b>\n\n"
            "Продлить или сменить тариф — «💳 Тарифы»."
        ),
        "en": (
            "👤 <b>Profile</b>\n\n{status}\n\n"
            "🔗 Connected accounts: <b>{accounts}</b>\n"
            "📋 Active connections: <b>{connections}</b>\n"
            "🎁 Friends invited: <b>{invited}</b>\n\n"
            "Renew or change your plan — «💳 Plans»."
        ),
    },
    "documents_title": {
        "ru": "📄 <b>Документы и поддержка</b>\n\nОзнакомься с условиями сервиса:",
        "en": "📄 <b>Documents & support</b>\n\nPlease review the service terms:",
    },
    "btn_privacy": {"ru": "🔐 Политика конфиденциальности", "en": "🔐 Privacy Policy"},
    "btn_terms": {"ru": "📄 Пользовательское соглашение", "en": "📄 Terms of Service"},
    "support_line": {
        "ru": "\n\n✍️ Поддержка: кнопка «Поддержка» в меню{contact}",
        "en": "\n\n✍️ Support: the «Support» button in the menu{contact}",
    },
    "support_prompt": {
        "ru": "✍️ Напиши своё сообщение/вопрос одним сообщением — я передам в поддержку.",
        "en": "✍️ Send your message/question in one message — I'll forward it to support.",
    },
    "support_sent": {
        "ru": "✅ Отправлено в поддержку — ответим как сможем.",
        "en": "✅ Sent to support — we'll reply as soon as we can.",
    },
    "support_unavailable": {
        "ru": "⚠️ Поддержка временно недоступна, попробуй позже.",
        "en": "⚠️ Support is temporarily unavailable, try later.",
    },
    "source_need_account": {
        "ru": "Сначала подключи свой канал («🔗 Подключить YouTube» или «🎵 Подключить TikTok»).",
        "en": "First connect your channel («🔗 Connect YouTube» or «🎵 Connect TikTok»).",
    },
    "source_prompt": {
        "ru": (
            "Пришли ссылку на канал-источник:\n"
            "• YouTube — <code>@handle</code> или ссылку\n"
            "• TikTok — ссылку на профиль (<code>https://www.tiktok.com/@user</code>)"
        ),
        "en": (
            "Send a link to the source channel:\n"
            "• YouTube — <code>@handle</code> or a link\n"
            "• TikTok — profile link (<code>https://www.tiktok.com/@user</code>)"
        ),
    },
    "oauth_youtube": {
        "ru": (
            "Нажми кнопку ниже и разреши доступ к своему YouTube-каналу.\n"
            "После подтверждения я пришлю сообщение, что канал подключён.\n\n"
            "<i>Ссылка действует 10 минут.</i>"
        ),
        "en": (
            "Tap the button below and grant access to your YouTube channel.\n"
            "After you confirm, I'll message you that the channel is connected.\n\n"
            "<i>The link is valid for 10 minutes.</i>"
        ),
    },
    "oauth_tiktok": {
        "ru": (
            "Нажми кнопку ниже и разреши доступ к своему TikTok-аккаунту.\n"
            "После подтверждения я пришлю сообщение, что аккаунт подключён.\n\n"
            "<i>Ссылка действует 10 минут.</i>"
        ),
        "en": (
            "Tap the button below and grant access to your TikTok account.\n"
            "After you confirm, I'll message you that the account is connected.\n\n"
            "<i>The link is valid for 10 minutes.</i>"
        ),
    },
    "btn_login_google": {"ru": "🔓 Войти через Google", "en": "🔓 Sign in with Google"},
    "btn_login_tiktok": {"ru": "🔓 Войти через TikTok", "en": "🔓 Sign in with TikTok"},
    "guide": {
        "ru": (
            "📖 <b>Как пользоваться PostiqBot</b>\n\n"
            "Бот автоматически забирает новые видео с канала-источника и публикует их "
            "на твой канал (YouTube или TikTok) по расписанию.\n\n"
            "<b>1. Подключи свой канал</b>\n"
            "«🔗 Подключить YouTube» или «🎵 Подключить TikTok» — вход через официальный OAuth.\n\n"
            "<b>2. Добавь источник</b>\n"
            "«📡 Добавить источник» → пришли ссылку на канал (YouTube @handle или ссылку TikTok).\n\n"
            "<b>3. Настрой связку</b>\n"
            "«📋 Мои подключения» → расписание, оверлей (картинка/GIF), доступ, пауза.\n\n"
            "<b>Важно</b>\n"
            "• Публикуются только <b>новые</b> видео.\n"
            "• TikTok-публикация приходит в черновики — публикуешь сам.\n"
            "• Доступ: триал, затем подписка («💳 Тарифы»). Вопросы — «✍️ Поддержка»."
        ),
        "en": (
            "📖 <b>How to use PostiqBot</b>\n\n"
            "The bot automatically takes new videos from a source channel and publishes "
            "them to your channel (YouTube or TikTok) on schedule.\n\n"
            "<b>1. Connect your channel</b>\n"
            "«🔗 Connect YouTube» or «🎵 Connect TikTok» — official OAuth sign-in.\n\n"
            "<b>2. Add a source</b>\n"
            "«📡 Add source» → send a channel link (YouTube @handle or a TikTok link).\n\n"
            "<b>3. Configure the link</b>\n"
            "«📋 My connections» → schedule, overlay (image/GIF), visibility, pause.\n\n"
            "<b>Important</b>\n"
            "• Only <b>new</b> videos are published.\n"
            "• TikTok posts land in drafts — you publish them yourself.\n"
            "• Access: trial, then subscription («💳 Plans»). Questions — «✍️ Support»."
        ),
    },
    "referral": {
        "ru": (
            "🎁 <b>Реферальная программа</b>\n\n"
            "Приглашай друзей! Когда приглашённый оформит подписку — тебе "
            "<b>+{bonus} дней</b> доступа.\n\n"
            "Твоя ссылка:\n{link}\n\n"
            "👥 Приглашено: <b>{invited}</b>\n💳 Оплатили (бонус начислен): <b>{paid}</b>"
        ),
        "en": (
            "🎁 <b>Referral program</b>\n\n"
            "Invite friends! When an invited user buys a subscription, you get "
            "<b>+{bonus} days</b> of access.\n\n"
            "Your link:\n{link}\n\n"
            "👥 Invited: <b>{invited}</b>\n💳 Paid (bonus granted): <b>{paid}</b>"
        ),
    },
}


def t(key: str, lang: str, **fmt) -> str:
    text = T.get(key, {}).get(lang) or T.get(key, {}).get(DEFAULT_LANG, key)
    return text.format(**fmt) if fmt else text


def label(action: str, lang: str) -> str:
    return LABELS[action].get(lang, LABELS[action][DEFAULT_LANG])


def labels(action: str) -> set[str]:
    """Все варианты метки (для матчинга нажатия независимо от языка)."""
    return set(LABELS[action].values())


async def user_lang(telegram_id: int) -> str:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
    return user.lang if user and user.lang in LANGS else DEFAULT_LANG


async def set_user_lang(telegram_id: int, lang: str) -> None:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.lang = lang
