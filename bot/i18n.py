"""Простая локализация (ru/en): метки кнопок, строки сообщений, язык юзера."""
from __future__ import annotations

from bot.db.models import User
from bot.db.session import get_session

DEFAULT_LANG = "ru"
LANGS = ("ru", "en")

LABELS: dict[str, dict[str, str]] = {
    "youtube": {"ru": "▶️ Подключить YouTube", "en": "▶️ Connect YouTube"},
    "tiktok": {"ru": "🎵 Подключить TikTok", "en": "🎵 Connect TikTok"},
    "connect": {"ru": "🔗 Подключить аккаунт", "en": "🔗 Connect account"},
    "source": {"ru": "📡 Добавить источник", "en": "📡 Add source"},
    "connections": {"ru": "📋 Мои подключения", "en": "📋 My connections"},
    "tariff": {"ru": "💎 Тарифы", "en": "💎 Plans"},
    "guide": {"ru": "📖 Как пользоваться", "en": "📖 How to use"},
    "referral": {"ru": "🎁 Пригласить друга", "en": "🎁 Invite a friend"},
    "support": {"ru": "💬 Поддержка", "en": "💬 Support"},
    "profile": {"ru": "👤 Профиль", "en": "👤 Profile"},
    "documents": {"ru": "📄 Документы", "en": "📄 Documents"},
    "more": {"ru": "⚙️ Ещё", "en": "⚙️ More"},
    "choose_platform": {
        "ru": "Какой аккаунт подключить?",
        "en": "Which account to connect?",
    },
    "lang": {"ru": "🌐 Switch to English", "en": "🌐 На русский"},
}

LEGACY_LABELS: dict[str, tuple[str, ...]] = {
    "connect": ("⊕ Подключить аккаунт", "⊕ Connect account"),
    "source": ("⊕ Добавить источник", "⊕ Add source"),
    "connections": ("☰ Мои подключения", "☰ My connections"),
    "profile": ("◉ Профиль", "◉ Profile"),
    "tariff": ("💳 Тарифы", "💳 Plans", "◈ Тарифы", "◈ Plans"),
    "more": ("ℹ️ Ещё", "ℹ️ More", "⋯ Ещё", "⋯ More"),
}

T: dict[str, dict[str, str]] = {
    "welcome": {
        "ru": (
            "👋 Привет! Я <b>PosttiqBot</b>.\n\n"
            "Я слежу за каналами-источниками и автоматически перезаливаю новые "
            "видео (включая Shorts) на твои YouTube/TikTok по расписанию.\n\n"
            "Пользуйся кнопками меню внизу 👇\n"
            "Начни с подключения своего канала, потом добавь источник."
        ),
        "en": (
            "👋 Hi! I'm <b>PosttiqBot</b>.\n\n"
            "I watch source channels and automatically repost new videos "
            "(including Shorts) to your YouTube/TikTok on schedule.\n\n"
            "Use the menu buttons below 👇\n"
            "Start by connecting your channel, then add a source."
        ),
    },
    "more_title": {"ru": "⚙️ <b>Дополнительно</b>", "en": "⚙️ <b>More</b>"},
    "menu_root": {
        "ru": "🏠 <b>Главное меню</b>\n\nВыбери раздел 👇",
        "en": "🏠 <b>Main menu</b>\n\nChoose a section 👇",
    },
    "menu_connections": {
        "ru": "➕ <b>Подключения</b>\n\nВыбери действие 👇",
        "en": "➕ <b>Connections</b>\n\nChoose an action 👇",
    },
    "menu_new_conn": {
        "ru": "➕ <b>Новое подключение</b>\n\nЧто добавить?",
        "en": "➕ <b>New connection</b>\n\nWhat to add?",
    },
    "menu_tariffs": {
        "ru": "💎 <b>Тарифы</b>\n\nВыбери 👇",
        "en": "💎 <b>Plans</b>\n\nChoose 👇",
    },
    "menu_more": {
        "ru": "⚙️ <b>Ещё</b>\n\nВыбери раздел 👇",
        "en": "⚙️ <b>More</b>\n\nChoose a section 👇",
    },
    "buy_caption": {
        "ru": "💎 <b>Тарифы</b>\n\nВыбери план 👇",
        "en": "💎 <b>Plans</b>\n\nChoose a plan 👇",
    },
    "plan_card": {
        "ru": (
            "{plan}\n\n"
            "📦 Каналов: <b>{accounts}</b>\n"
            "🎬 <b>{videos}</b> видео/день на связку\n\n"
            "📅 Месяц: <b>{m_rub} ₽</b> / {m_star} ⭐\n"
            "♾️ Навсегда: <b>{f_rub} ₽</b> / {f_star} ⭐\n\n"
            "Выбери способ оплаты 👇"
        ),
        "en": (
            "{plan}\n\n"
            "📦 Channels: <b>{accounts}</b>\n"
            "🎬 <b>{videos}</b> videos/day per connection\n\n"
            "📅 Month: <b>{m_rub} ₽</b> / {m_star} ⭐\n"
            "♾️ Forever: <b>{f_rub} ₽</b> / {f_star} ⭐\n\n"
            "Choose a payment option 👇"
        ),
    },
    "btn_buy_month": {"ru": "📅 Месяц — {rub} ₽", "en": "📅 Month — {rub} ₽"},
    "per_month_short": {"ru": "₽/мес", "en": "₽/mo"},
    "btn_buy_month_star": {"ru": "📅 Месяц — {stars} ⭐", "en": "📅 Month — {stars} ⭐"},
    "btn_buy_forever": {"ru": "♾️ Навсегда — {rub} ₽", "en": "♾️ Forever — {rub} ₽"},
    "btn_buy_forever_star": {"ru": "♾️ Навсегда — {stars} ⭐", "en": "♾️ Forever — {stars} ⭐"},
    "inv_period_month": {"ru": "на месяц", "en": "for a month"},
    "my_sub_body": {
        "ru": "⭐ <b>Моя подписка</b>\n\n{status}",
        "en": "⭐ <b>My subscription</b>\n\n{status}",
    },
    "mylist_title": {
        "ru": "📋 <b>Мои подключения</b>\nВыбери связку, чтобы настроить:",
        "en": "📋 <b>My connections</b>\nTap a link to configure:",
    },
    "mylist_empty": {
        "ru": "📋 <b>Мои подключения</b>\n\nСвязок пока нет. Нажми «➕ Новое подключение».",
        "en": "📋 <b>My connections</b>\n\nNo connections yet. Tap «➕ New connection».",
    },
    "lang_switched": {
        "ru": "🌐 Язык переключён на русский.",
        "en": "🌐 Language switched to English.",
    },
    "limit_accounts": {
        "ru": (
            "⚠️ На твоём тарифе можно подключить до <b>{limit}</b> аккаунтов. "
            "Удали лишний или оформи тариф побольше («💎 Тарифы»)."
        ),
        "en": (
            "⚠️ Your plan allows up to <b>{limit}</b> accounts. "
            "Remove one or upgrade your plan («💎 Plans»)."
        ),
    },
    "tariffs_caption": {
        "ru": "💎 <b>Тарифы</b>\n\n{status}\n{prices}\n\nВыбери тариф ниже 👇",
        "en": "💎 <b>Plans</b>\n\n{status}\n{prices}\n\nPick a plan below 👇",
    },
    "pay_choose": {
        "ru": "💳 Тариф <b>{plan}</b>. Выбери способ оплаты:",
        "en": "💳 <b>{plan}</b> plan. Choose a payment method:",
    },
    "btn_pay_stars": {"ru": "⭐ Telegram Stars ({stars})", "en": "⭐ Telegram Stars ({stars})"},
    "btn_pay_rub": {"ru": "💳 СБП / карта ({price})", "en": "💳 Card / SBP ({price})"},
    "price_line": {
        "ru": "• {plan} — <b>{price}</b> ({accounts} акк, {videos} видео/день)",
        "en": "• {plan} — <b>{price}</b> ({accounts} accounts, {videos} videos/day)",
    },
    "rub_soon": {
        "ru": "₽ Оплата через СБП/карту скоро подключится. Пока можно оплатить через Telegram Stars (⭐) или написать в «💬 Поддержка».",
        "en": "₽ Card/SBP payment is coming soon. For now use Telegram Stars (⭐) or contact «💬 Support».",
    },
    "pay_link": {
        "ru": "💳 Счёт на <b>{amount} ₽</b> ({plan}) создан.\nОплати по кнопке ниже — доступ активируется автоматически после оплаты.",
        "en": "💳 Invoice for <b>{amount} ₽</b> ({plan}) created.\nPay via the button below — access activates automatically after payment.",
    },
    "btn_pay_now": {"ru": "💳 Оплатить {amount} ₽", "en": "💳 Pay {amount} ₽"},
    "pay_error": {
        "ru": "⚠️ Не удалось создать счёт. Попробуй позже или напиши в «💬 Поддержка».",
        "en": "⚠️ Couldn't create the invoice. Try later or contact «💬 Support».",
    },
    "status_admin": {"ru": "♾ Безлимитный доступ (админ)", "en": "♾ Unlimited access (admin)"},
    "expiry_soon": {
        "ru": (
            "⏳ Твой доступ заканчивается <b>{date}</b>.\n"
            "Продли подписку, чтобы бот не переставал публиковать — нажми «💎 Тарифы»."
        ),
        "en": (
            "⏳ Your access ends on <b>{date}</b>.\n"
            "Renew to keep the bot publishing — tap «💎 Plans»."
        ),
    },
    "publish_failed_auth": {
        "ru": (
            "❌ Не удалось опубликовать «{title}»: возможно, отозван доступ к каналу.\n"
            "Переподключи аккаунт: «➕ Новое подключение» → «🔓 Войти через …»."
        ),
        "en": (
            "❌ Couldn't publish «{title}»: channel access may have been revoked.\n"
            "Reconnect the account: «➕ New connection» → «🔓 Sign in with …»."
        ),
    },
    "publish_failed": {
        "ru": "❌ Не удалось опубликовать «{title}». Попробуем позже.",
        "en": "❌ Couldn't publish «{title}». We'll retry later.",
    },
    "download_failed": {
        "ru": "❌ Не удалось скачать «{title}».\n<i>{reason}</i>",
        "en": "❌ Couldn't download «{title}».\n<i>{reason}</i>",
    },
    "download_failed_age": {
        "ru": (
            "❌ Видео «{title}» с возрастным ограничением (18+) — YouTube требует "
            "вход, и бот не может его скачать. Выбери другой источник."
        ),
        "en": (
            "❌ «{title}» is age-restricted (18+) — YouTube requires sign-in, so the "
            "bot can't download it. Please pick another source."
        ),
    },
    "profile_body": {
        "ru": (
            "👤 <b>Профиль</b>\n\n{status}\n\n"
            "🔗 Подключено аккаунтов: <b>{accounts}</b>\n"
            "📋 Активных связок: <b>{connections}</b>\n"
            "🎁 Приглашено друзей: <b>{invited}</b>\n\n"
            "Продлить или сменить тариф — «💎 Тарифы»."
        ),
        "en": (
            "👤 <b>Profile</b>\n\n{status}\n\n"
            "🔗 Connected accounts: <b>{accounts}</b>\n"
            "📋 Active connections: <b>{connections}</b>\n"
            "🎁 Friends invited: <b>{invited}</b>\n\n"
            "Renew or change your plan — «💎 Plans»."
        ),
    },
    "documents_title": {
        "ru": "📄 <b>Документы и поддержка</b>\n\nОзнакомься с условиями сервиса:",
        "en": "📄 <b>Documents & support</b>\n\nPlease review the service terms:",
    },
    "btn_privacy": {"ru": "🔐 Политика конфиденциальности", "en": "🔐 Privacy Policy"},
    "btn_terms": {"ru": "📄 Пользовательское соглашение", "en": "📄 Terms of Service"},
    "policy_line": {
        "ru": "🔐 Политика конфиденциальности:\n{url}",
        "en": "🔐 Privacy Policy:\n{url}",
    },
    "terms_line": {
        "ru": "📄 Пользовательское соглашение:\n{url}",
        "en": "📄 Terms of Service:\n{url}",
    },
    "support_line": {
        "ru": "\n\n💬 Поддержка: кнопка «Поддержка» в меню{contact}",
        "en": "\n\n💬 Support: the «Support» button in the menu{contact}",
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
        "ru": "Сначала подключи свой канал («🔓 Войти через YouTube» или «🔓 Войти через TikTok»).",
        "en": "First connect your channel («🔓 Sign in with YouTube» or «🔓 Sign in with TikTok»).",
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
    "btn_signin_youtube": {"ru": "🔓 Войти через YouTube", "en": "🔓 Sign in with YouTube"},
    "btn_signin_tiktok": {"ru": "🔓 Войти через TikTok", "en": "🔓 Sign in with TikTok"},
    "acc_connected_youtube": {
        "ru": (
            "✅ Канал <b>{title}</b> подключён!\n"
            "Теперь добавь источник, за которым следить."
        ),
        "en": (
            "✅ Channel <b>{title}</b> connected!\n"
            "Now add a source channel to watch."
        ),
    },
    "acc_connected_tiktok": {
        "ru": (
            "✅ TikTok <b>{title}</b> подключён!\n"
            "Теперь можно выбрать его как канал публикации при создании связки."
        ),
        "en": (
            "✅ TikTok <b>{title}</b> connected!\n"
            "You can now pick it as the publishing channel for a connection."
        ),
    },
    "guide": {
        "ru": (
            "📖 <b>Как пользоваться PosttiqBot</b>\n\n"
            "Бот автоматически забирает новые видео с канала-источника и публикует их "
            "на твой канал (YouTube или TikTok) по расписанию.\n\n"
            "<b>1. Подключи свой канал</b>\n"
            "«➕ Подключения» → «➕ Новое подключение» → «🔓 Войти через YouTube» "
            "или «🔓 Войти через TikTok» (вход через официальный OAuth).\n\n"
            "<b>2. Добавь источник</b>\n"
            "«➕ Новое подключение» → «📡 Добавить источник» → пришли ссылку на канал "
            "(YouTube @handle/ссылку или ссылку на профиль TikTok).\n\n"
            "<b>3. Настрой связку</b>\n"
            "«📋 Мои подключения» → выбери связку: расписание (сразу/интервал/по времени), "
            "оверлей (картинка/GIF), доступ, пауза.\n"
            "📥 <b>Залить архив</b> — поставить в очередь <b>прошлые</b> видео источника "
            "(старые → новые). Выходят по 4/день на связку.\n\n"
            "<b>Важно</b>\n"
            "• Публикуются только <b>новые</b> видео (одно видео не репостится дважды).\n"
            "• TikTok: перед выходом бот присылает карточку — жмёшь «✅ Опубликовать», "
            "и видео уходит в ленту. В связке можно включить автопубликацию без вопросов.\n"
            "• Доступ: триал, затем подписка («💎 Тарифы»). Вопросы — «💬 Поддержка»."
        ),
        "en": (
            "📖 <b>How to use PosttiqBot</b>\n\n"
            "The bot automatically takes new videos from a source channel and publishes "
            "them to your channel (YouTube or TikTok) on schedule.\n\n"
            "<b>1. Connect your channel</b>\n"
            "«➕ Connections» → «➕ New connection» → «🔓 Sign in with YouTube» "
            "or «🔓 Sign in with TikTok» (official OAuth sign-in).\n\n"
            "<b>2. Add a source</b>\n"
            "«➕ New connection» → «📡 Add source» → send a channel link "
            "(YouTube @handle/link or a TikTok profile link).\n\n"
            "<b>3. Configure the link</b>\n"
            "«📋 My connections» → pick a link: schedule (immediate/interval/times), "
            "overlay (image/GIF), visibility, pause.\n"
            "📥 <b>Backfill</b> — queue the source's <b>past</b> videos "
            "(oldest → newest). They publish at 4/day per connection.\n\n"
            "<b>Important</b>\n"
            "• Only <b>new</b> videos are published (a video isn't reposted twice).\n"
            "• TikTok: the bot sends a confirmation card first — tap «✅ Post it» and the "
            "video goes to your feed. A connection can be switched to auto-posting.\n"
            "• Access: trial, then subscription («💎 Plans»). Questions — «💬 Support»."
        ),
    },
    "referral": {
        "ru": (
            "🎁 <b>Реферальная программа</b>\n\n"
            "Приглашай друзей! Когда приглашённый оформит первую подписку, тебе "
            "начислим бесплатный доступ на <b>{bonus} дн.</b> по тарифу "
            "<b>{plan}</b>.\n\n"
            "Твоя ссылка:\n{link}\n\n"
            "👥 Приглашено: <b>{invited}</b>\n💳 Оплатили (бонус начислен): <b>{paid}</b>"
        ),
        "en": (
            "🎁 <b>Referral program</b>\n\n"
            "Invite friends! When an invited user buys their first subscription, you "
            "get <b>{bonus} days</b> of free access on the <b>{plan}</b> plan.\n\n"
            "Your link:\n{link}\n\n"
            "👥 Invited: <b>{invited}</b>\n💳 Paid (bonus granted): <b>{paid}</b>"
        ),
    },
    "c_active": {"ru": "🟢 активна", "en": "🟢 active"},
    "c_paused": {"ru": "⏸ на паузе", "en": "⏸ paused"},
    "c_sched_interval": {"ru": "⏱ каждые {n} мин", "en": "⏱ every {n} min"},
    "c_sched_times": {"ru": "🕐 в {times} ({tz})", "en": "🕐 at {times} ({tz})"},
    "c_sched_now": {"ru": "⚡ сразу", "en": "⚡ immediately"},
    "c_ovl_on": {"ru": "вкл ({pos}, {scale}%)", "en": "on ({pos}, {scale}%)"},
    "c_ovl_off": {"ru": "выкл", "en": "off"},
    "c_ovl_blocked": {"ru": "недоступно для TikTok", "en": "unavailable for TikTok"},
    "c_ovl_blocked_alert": {
        "ru": "Для публикации в ленту TikTok оверлей недоступен: правила TikTok "
              "запрещают накладывать логотипы и водяные знаки на видео.",
        "en": "Overlay is unavailable when posting to a TikTok feed: TikTok rules "
              "prohibit superimposing logos or watermarks on the video.",
    },
    "c_priv_private": {"ru": "🔒 приватное", "en": "🔒 private"},
    "c_priv_unlisted": {"ru": "🔗 по ссылке", "en": "🔗 unlisted"},
    "c_priv_public": {"ru": "🌍 публичное", "en": "🌍 public"},
    "c_card": {
        "ru": (
            "<b>{name}</b>\n\n"
            "📡 Источник: <b>{src}</b>\n"
            "📤 Публикую на: <b>{dst}</b>\n"
            "📁 Папка: {folder}\n"
            "👁 Доступ публикаций: {priv}\n"
            "⏰ Расписание: {sched}\n"
            "🖼 Оверлей: {ovl}\n"
            "⚙️ Статус: {status}"
        ),
        "en": (
            "<b>{name}</b>\n\n"
            "📡 Source: <b>{src}</b>\n"
            "📤 Publishing to: <b>{dst}</b>\n"
            "📁 Folder: {folder}\n"
            "👁 Visibility: {priv}\n"
            "⏰ Schedule: {sched}\n"
            "🖼 Overlay: {ovl}\n"
            "⚙️ Status: {status}"
        ),
    },
    "c_btn_pause": {"ru": "⏸ Поставить на паузу", "en": "⏸ Pause"},
    "c_btn_resume": {"ru": "▶️ Возобновить", "en": "▶️ Resume"},
    "c_btn_visibility": {"ru": "👁 Доступ: {priv}", "en": "👁 Visibility: {priv}"},
    "c_btn_schedule": {"ru": "⏰ Расписание: {sched}", "en": "⏰ Schedule: {sched}"},
    "c_btn_overlay": {"ru": "🖼 Оверлей: {ovl}", "en": "🖼 Overlay: {ovl}"},
    "c_btn_tiktok": {"ru": "🎵 TikTok: {mode}", "en": "🎵 TikTok: {mode}"},
    "c_tt_auto": {"ru": "автопубликация", "en": "auto-posting"},
    "c_tt_card": {"ru": "с подтверждением", "en": "confirm each"},
    "c_btn_delete": {"ru": "🗑 Удалить", "en": "🗑 Delete"},
    "c_btn_to_list": {"ru": "⬅️ К списку", "en": "⬅️ Back to list"},
    "c_btn_back": {"ru": "⬅️ Назад", "en": "⬅️ Back"},
    "c_btn_cancel": {"ru": "❌ Отмена", "en": "❌ Cancel"},
    "ask_cancelled": {"ru": "Отменено", "en": "Cancelled"},
    "c_btn_del_yes": {"ru": "🗑 Да, удалить", "en": "🗑 Yes, delete"},
    "c_not_found": {"ru": "Связка не найдена", "en": "Connection not found"},
    "c_not_found_dot": {"ru": "Связка не найдена.", "en": "Connection not found."},
    "c_resumed": {"ru": "Возобновлено", "en": "Resumed"},
    "c_paused_toast": {"ru": "Поставлено на паузу", "en": "Paused"},
    "c_del_confirm": {
        "ru": (
            "Удалить эту связку? Новые видео из источника публиковаться не будут.\n"
            "<i>Уже опубликованные видео останутся на твоём канале.</i>"
        ),
        "en": (
            "Delete this connection? New videos from the source won't be published.\n"
            "<i>Already published videos stay on your channel.</i>"
        ),
    },
    "c_deleted": {"ru": "🗑 Связка удалена.", "en": "🗑 Connection deleted."},
    "c_deleted_toast": {"ru": "Удалено", "en": "Deleted"},
    "c_sched_menu": {
        "ru": (
            "⏰ <b>Расписание публикаций</b>\n\n"
            "• <b>Сразу</b> — публиковать как только видео скачано\n"
            "• <b>Интервал</b> — не чаще раза в N минут (растягивает очередь)\n"
            "• <b>По времени</b> — в заданные часы дня"
        ),
        "en": (
            "⏰ <b>Publishing schedule</b>\n\n"
            "• <b>Immediately</b> — publish as soon as the video is downloaded\n"
            "• <b>Interval</b> — no more than once every N minutes (spreads the queue)\n"
            "• <b>Times</b> — at set hours of the day"
        ),
    },
    "c_sched_btn_now": {"ru": "⚡ Сразу", "en": "⚡ Immediately"},
    "c_sched_btn_int": {"ru": "⏱ Интервал", "en": "⏱ Interval"},
    "c_sched_btn_times": {"ru": "🕐 По времени", "en": "🕐 Times"},
    "c_sched_now_toast": {"ru": "Публикую сразу", "en": "Publishing immediately"},
    "c_int_prompt": {
        "ru": "Пришли интервал между публикациями в <b>минутах</b> (например <code>120</code> = раз в 2 часа).",
        "en": "Send the interval between posts in <b>minutes</b> (e.g. <code>120</code> = once every 2 hours).",
    },
    "c_int_bad": {
        "ru": "Нужно положительное число минут. Попробуй ещё раз.",
        "en": "Need a positive number of minutes. Try again.",
    },
    "c_times_prompt": {
        "ru": (
            "Пришли времена публикаций через запятую в формате ЧЧ:ММ.\n"
            "Можно добавить таймзону.\n\n"
            "Примеры:\n<code>10:00, 15:00, 19:30</code>\n"
            "<code>09:00, 21:00 Europe/Moscow</code>"
        ),
        "en": (
            "Send posting times separated by commas in HH:MM format.\n"
            "You can add a timezone.\n\n"
            "Examples:\n<code>10:00, 15:00, 19:30</code>\n"
            "<code>09:00, 21:00 Europe/Moscow</code>"
        ),
    },
    "c_times_bad": {
        "ru": "Не нашёл корректных времён. Формат: <code>10:00, 15:00</code>",
        "en": "No valid times found. Format: <code>10:00, 15:00</code>",
    },
    "c_ovl_text": {
        "ru": (
            "🖼 <b>Оверлей</b> — картинка/GIF поверх видео.\n\n"
            "Выбери <b>позицию</b> (сетка) и <b>размер</b> (% ширины).\n"
            "Текущая позиция отмечена точкой."
        ),
        "en": (
            "🖼 <b>Overlay</b> — an image/GIF on top of the video.\n\n"
            "Pick a <b>position</b> (grid) and <b>size</b> (% of width).\n"
            "The current position is marked with a dot."
        ),
    },
    "c_ovl_hint": {
        "ru": (
            "⚠️ <b>Если у фото прозрачный фон</b> (PNG без фона) — отправь его "
            "<b>как ДОКУМЕНТ/Файл</b>, а не как обычное фото!\n\n"
            "Как отправить файлом:\n"
            "📎 Скрепка → <b>Файл</b> → выбери своё PNG → отправить.\n\n"
            "Если отправить как «Фото», Telegram сожмёт его в JPEG и "
            "<b>прозрачность пропадёт</b> — фон станет белым."
        ),
        "en": (
            "⚠️ <b>If your image has a transparent background</b> (PNG) — send it "
            "<b>as a DOCUMENT/File</b>, not as a regular photo!\n\n"
            "How to send as a file:\n"
            "📎 Attach → <b>File</b> → choose your PNG → send.\n\n"
            "If sent as a “Photo”, Telegram compresses it to JPEG and "
            "<b>transparency is lost</b> — the background turns white."
        ),
    },
    "c_ovl_btn_replace": {"ru": "🔁 Заменить", "en": "🔁 Replace"},
    "c_ovl_btn_remove": {"ru": "🗑 Убрать", "en": "🗑 Remove"},
    "c_ovl_prompt": {
        "ru": "Пришли <b>картинку</b>, <b>GIF</b> или стикер — наложу её на каждое видео этой связки.\n\n",
        "en": "Send an <b>image</b>, <b>GIF</b> or sticker — I'll overlay it on every video of this connection.\n\n",
    },
    "c_ovl_prompt_replace": {
        "ru": "Пришли новую картинку/GIF для оверлея.\n\n",
        "en": "Send a new image/GIF for the overlay.\n\n",
    },
    "c_ovl_not_image": {
        "ru": "Это не картинка. Пришли фото, GIF, документ-изображение или стикер.",
        "en": "That's not an image. Send a photo, GIF, image document or sticker.",
    },
    "c_ovl_saved": {
        "ru": "✅ Картинка сохранена. Вот как ляжет — настрой позицию и размер:",
        "en": "✅ Image saved. Here's how it looks — adjust the position and size:",
    },
    "c_ovl_pos_toast": {"ru": "Позиция обновлена", "en": "Position updated"},
    "c_ovl_scale_toast": {"ru": "Размер обновлён", "en": "Size updated"},
    "c_ovl_removed_toast": {"ru": "Оверлей убран", "en": "Overlay removed"},
    "c_not_found_short": {"ru": "Не найдено", "en": "Not found"},
    "c_btn_backfill": {"ru": "📥 Залить архив", "en": "📥 Backfill"},
    "c_default_name": {"ru": "Связка #{id}", "en": "Connection #{id}"},
    "c_btn_rename": {"ru": "✏️ Переименовать", "en": "✏️ Rename"},
    "c_ren_prompt": {
        "ru": "Пришли новое название связки (до 64 символов).",
        "en": "Send a new name for the connection (up to 64 characters).",
    },
    "c_ren_too_long": {
        "ru": "Слишком длинно — максимум 64 символа. Попробуй короче.",
        "en": "Too long — 64 characters max. Try a shorter one.",
    },
    "c_renamed_toast": {"ru": "Название сохранено", "en": "Name saved"},
    "f_btn_folder": {"ru": "📁 Папка: {folder}", "en": "📁 Folder: {folder}"},
    "f_none": {"ru": "без папки", "en": "no folder"},
    "f_title": {
        "ru": "📁 <b>{name}</b>\n\nСвязки в папке:",
        "en": "📁 <b>{name}</b>\n\nConnections in this folder:",
    },
    "f_empty": {
        "ru": (
            "📁 <b>{name}</b>\n\nПапка пуста. Открой связку и нажми "
            "«📁 Папка», чтобы переместить её сюда."
        ),
        "en": (
            "📁 <b>{name}</b>\n\nThis folder is empty. Open a connection and tap "
            "«📁 Folder» to move it here."
        ),
    },
    "f_btn_new": {"ru": "➕ Новая папка", "en": "➕ New folder"},
    "f_new_prompt": {
        "ru": "Пришли название папки (до 64 символов).",
        "en": "Send a folder name (up to 64 characters).",
    },
    "f_created": {"ru": "✅ Папка «{name}» создана.", "en": "✅ Folder «{name}» created."},
    "f_btn_rename": {"ru": "✏️ Переименовать папку", "en": "✏️ Rename folder"},
    "f_ren_prompt": {
        "ru": "Пришли новое название папки (до 64 символов).",
        "en": "Send a new folder name (up to 64 characters).",
    },
    "f_btn_delete": {"ru": "🗑 Удалить папку", "en": "🗑 Delete folder"},
    "f_del_confirm": {
        "ru": (
            "Удалить папку «{name}»?\n"
            "<i>Связки не удалятся — они вернутся в общий список.</i>"
        ),
        "en": (
            "Delete folder «{name}»?\n"
            "<i>Connections won't be deleted — they'll return to the main list.</i>"
        ),
    },
    "f_deleted": {"ru": "🗑 Папка удалена.", "en": "🗑 Folder deleted."},
    "f_deleted_toast": {"ru": "Папка удалена", "en": "Folder deleted"},
    "f_not_found": {"ru": "Папка не найдена", "en": "Folder not found"},
    "mv_title": {
        "ru": "📁 Куда переместить связку?",
        "en": "📁 Where to move the connection?",
    },
    "mv_no_folder": {"ru": "📂 Без папки", "en": "📂 No folder"},
    "mv_moved_toast": {"ru": "Перемещено", "en": "Moved"},
    "gate_prompt": {
        "ru": (
            "👋 Привет! Чтобы получить <b>7 дней бесплатного доступа</b> к PosttiqBot, "
            "подпишись на наш канал 👇"
        ),
        "en": (
            "👋 Hi! To get <b>7 days of free access</b> to PosttiqBot, "
            "subscribe to our channel 👇"
        ),
    },
    "gate_btn_join": {"ru": "📢 Перейти в канал", "en": "📢 Go to channel"},
    "gate_btn_check": {"ru": "✅ Я подписался — проверить", "en": "✅ I subscribed — check"},
    "gate_ok": {
        "ru": "✅ Подписка подтверждена! Тебе начислено <b>7 дней</b> бесплатного доступа. Добро пожаловать! 🎉",
        "en": "✅ Subscription confirmed! You've been granted <b>7 days</b> of free access. Welcome! 🎉",
    },
    "gate_fail": {
        "ru": "❌ Ты ещё не подписан на канал. Подпишись и нажми «Проверить» снова.",
        "en": "❌ You haven't subscribed yet. Subscribe and tap «Check» again.",
    },
    "gate_toast": {
        "ru": "Сначала подпишись на канал 👇",
        "en": "Subscribe to the channel first 👇",
    },
    "private_notice": {
        "ru": (
            "🚀 <b>PosttiqBot скоро откроется!</b>\n\n"
            "Подпишись на канал, чтобы на старте забрать бесплатный доступ."
        ),
        "en": (
            "🚀 <b>PosttiqBot is opening soon!</b>\n\n"
            "Subscribe to our channel to grab free access at launch."
        ),
    },
    "bf_choose": {
        "ru": (
            "📥 <b>Залить архив источника</b>\n"
            "Сколько последних видео поставить в очередь (старые → новые)?\n"
            "<i>В очередь можно сколько угодно — публикуется до 4/день на аккаунт.</i>"
        ),
        "en": (
            "📥 <b>Backfill the source archive</b>\n"
            "How many recent videos to queue (oldest → newest)?\n"
            "<i>Queue as many as you want — it publishes up to 4/day per account.</i>"
        ),
    },
    "bf_all": {"ru": "Всё", "en": "All"},
    "bf_choose_conn": {
        "ru": (
            "📥 <b>Залить архив</b>\n"
            "Поставит в очередь <b>прошлые</b> видео источника (старые → новые) — "
            "они будут публиковаться на твой канал по 4/день на связку.\n\n"
            "Выбери связку:"
        ),
        "en": (
            "📥 <b>Backfill</b>\n"
            "Queues the source's <b>past</b> videos (oldest → newest) — they'll "
            "publish to your channel at 4/day per connection.\n\n"
            "Pick a connection:"
        ),
    },
    "bf_working": {"ru": "⏳ Собираю архив…", "en": "⏳ Fetching the archive…"},
    "bf_done": {
        "ru": "✅ В очередь поставлено <b>{created}</b> видео из «{title}» (старые → новые).",
        "en": "✅ Queued <b>{created}</b> videos from «{title}» (oldest → newest).",
    },
    "bf_empty": {
        "ru": "⚠️ Архив пуст или источник недоступен (для TikTok могут понадобиться cookies).",
        "en": "⚠️ Archive is empty or the source is unavailable (TikTok may need cookies).",
    },
    "bf_none": {
        "ru": "ℹ️ Новых видео не добавлено — всё уже в очереди или опубликовано.",
        "en": "ℹ️ Nothing new added — everything is already queued or published.",
    },
    "bf_toast": {"ru": "Готово", "en": "Done"},
    "src_bad_link": {
        "ru": (
            "❌ Не получилось распознать канал. Проверь ссылку и пришли ещё раз.\n"
            "Для TikTok пришли полную ссылку на профиль (https://www.tiktok.com/@...)."
        ),
        "en": (
            "❌ Couldn't recognize the channel. Check the link and send it again.\n"
            "For TikTok, send the full profile link (https://www.tiktok.com/@...)."
        ),
    },
    "src_choose_dest": {
        "ru": "Источник <b>{title}</b> распознан.\nНа какой свой канал публиковать?",
        "en": "Source <b>{title}</b> recognized.\nWhich of your channels should I publish to?",
    },
    "src_connected": {
        "ru": (
            "✅ Источник <b>{title}</b> подключён.\n"
            "Как только там появится новое видео — я заберу его и опубликую к тебе."
        ),
        "en": (
            "✅ Source <b>{title}</b> connected.\n"
            "As soon as a new video appears there, I'll grab it and publish it for you."
        ),
    },
    "src_exists": {
        "ru": "ℹ️ Такая связка уже существует.",
        "en": "ℹ️ This connection already exists.",
    },
    "src_default_title": {"ru": "канал", "en": "channel"},
    "acc_no_project": {
        "ru": (
            "⚠️ Нет доступных Google-проектов в пуле. "
            "Админу нужно добавить проект командой /addproject."
        ),
        "en": (
            "⚠️ No available Google projects in the pool. "
            "The admin needs to add one via /addproject."
        ),
    },
    "acc_tiktok_off": {
        "ru": "⚠️ TikTok пока не настроен на сервере.",
        "en": "⚠️ TikTok isn't configured on the server yet.",
    },
    "bad_tariff": {"ru": "Неверный тариф", "en": "Invalid plan"},
    "support_send_text": {"ru": "Пришли текстом, пожалуйста.", "en": "Please send it as text."},
    "paid_forever": {"ru": "активна <b>навсегда</b> ♾️", "en": "active <b>forever</b> ♾️"},
    "paid_until": {"ru": "активна до <b>{date}</b>", "en": "active until <b>{date}</b>"},
    "paid_ok": {
        "ru": "✅ Оплата прошла! Подписка {active}. Спасибо! 🙌",
        "en": "✅ Payment succeeded! Subscription {active}. Thank you! 🙌",
    },
    "pay_received": {
        "ru": "✅ Оплата получена! Подписка активна до <b>{date}</b>. Спасибо! 🙌",
        "en": "✅ Payment received! Subscription active until <b>{date}</b>. Thank you! 🙌",
    },
    "ref_reward": {
        "ru": (
            "🎁 Твой приглашённый оформил подписку — тебе начислен бесплатный "
            "доступ на <b>{days} дн.</b> по тарифу <b>{plan}</b>!\n"
            "Доступ активен до <b>{date}</b>."
        ),
        "en": (
            "🎁 Your referral bought a subscription — you get <b>{days} days</b> of "
            "free access on the <b>{plan}</b> plan!\n"
            "Access is active until <b>{date}</b>."
        ),
    },
    "pub_yt_ok": {
        "ru": (
            "✅ Видео опубликовано: https://youtu.be/{id}\n"
            "<i>{title}</i> (доступ: {privacy})"
        ),
        "en": (
            "✅ Video published: https://youtu.be/{id}\n"
            "<i>{title}</i> (visibility: {privacy})"
        ),
    },
    "pub_tt_ok": {
        "ru": (
            "✅ Видео отправлено в черновики TikTok: <i>{title}</i>\n"
            "Открой приложение TikTok → Профиль → Черновики → опубликуй."
        ),
        "en": (
            "✅ Video sent to TikTok drafts: <i>{title}</i>\n"
            "Open TikTok → Profile → Drafts → publish it."
        ),
    },
    "pub_tt_live": {
        "ru": (
            "✅ Видео опубликовано в TikTok: <i>{title}</i>\n"
            "Оно появится в профиле через минуту — TikTok ещё обрабатывает файл."
        ),
        "en": (
            "✅ Video published to TikTok: <i>{title}</i>\n"
            "It shows up on your profile in a minute — TikTok is still processing it."
        ),
    },
    "pub_tt_unaudited": {
        "ru": (
            "⚠️ TikTok пока не даёт публиковать в ленту: приложение бота ещё не "
            "прошло аудит TikTok, и разрешены только приватные публикации.\n"
            "Чтобы видео не потерялось, оно залито в черновики: "
            "<i>{title}</i>\nОткрой приложение TikTok → Профиль → Черновики → "
            "опубликуй. Как только аудит пройдёт, публикация снова пойдёт сама."
        ),
        "en": (
            "⚠️ TikTok won't post to your feed yet: the bot's app hasn't passed the "
            "TikTok audit, so only private posts are allowed.\n"
            "So the video isn't lost, it went to your drafts: <i>{title}</i>\n"
            "Open TikTok → Profile → Drafts → publish it. Once the audit is "
            "approved, posting resumes on its own."
        ),
    },
    "pub_fail": {
        "ru": "❌ Не удалось опубликовать «{title}»: {error}",
        "en": "❌ Couldn't publish «{title}»: {error}",
    },
    "pub_tt_too_many": {
        "ru": (
            "⚠️ TikTok не принял «{title}»: слишком много неопубликованных черновиков.\n"
            "Открой TikTok → Профиль → Черновики, опубликуй или удали старые, "
            "потом можно повторить."
        ),
        "en": (
            "⚠️ TikTok rejected «{title}»: too many unpublished drafts.\n"
            "Open TikTok → Profile → Drafts, publish or delete old ones, then retry."
        ),
    },
    "pub_tt_rate_limit": {
        "ru": (
            "⚠️ TikTok не принял «{title}»: исчерпан суточный лимит публикаций "
            "для аккаунта.\nПопробуй ещё раз через несколько часов."
        ),
        "en": (
            "⚠️ TikTok rejected «{title}»: the account hit its daily posting limit.\n"
            "Try again in a few hours."
        ),
    },
    "pub_tt_retry": {
        "ru": (
            "⏳ TikTok сейчас не принимает «{title}» — сработал лимит аккаунта.\n"
            "Видео сохранено, попробую опубликовать снова через {hours} ч."
        ),
        "en": (
            "⏳ TikTok won't take «{title}» right now — the account hit a limit.\n"
            "The video is saved, I'll try publishing again in {hours}h."
        ),
    },
    "pub_tt_privacy_gone": {
        "ru": (
            "⚠️ Не удалось опубликовать «{title}»: выбранная приватность больше "
            "недоступна аккаунту (например, профиль стал приватным).\n"
            "Открой настройки TikTok у связки и выбери, кто увидит видео."
        ),
        "en": (
            "⚠️ Couldn't publish «{title}»: the chosen visibility is no longer "
            "available for the account (e.g. the profile went private).\n"
            "Open the connection's TikTok settings and pick who can see videos."
        ),
    },
    "ttc_header": {
        "ru": "🎵 <b>Новое видео готово к публикации в TikTok</b>",
        "en": "🎵 <b>New video ready to post on TikTok</b>",
    },
    "ttc_account": {
        "ru": "👤 Аккаунт: <b>{nickname}</b>",
        "en": "👤 Account: <b>{nickname}</b>",
    },
    "ttc_privacy_ask": {
        "ru": "👁 <b>Кто увидит видео — выбери ниже</b> (обязательно)",
        "en": "👁 <b>Who can see it — choose below</b> (required)",
    },
    "ttc_privacy_is": {
        "ru": "👁 Кто увидит: <b>{value}</b>",
        "en": "👁 Visibility: <b>{value}</b>",
    },
    "ttc_prv_public": {"ru": "Все (Public)", "en": "Everyone (Public)"},
    "ttc_prv_followers": {"ru": "Подписчики", "en": "Followers"},
    "ttc_prv_friends": {"ru": "Друзья", "en": "Friends"},
    "ttc_prv_private": {"ru": "Только я", "en": "Only me"},
    "ttc_tog_comment": {"ru": "Комментарии", "en": "Comments"},
    "ttc_tog_duet": {"ru": "Дуэты", "en": "Duet"},
    "ttc_tog_stitch": {"ru": "Стичи", "en": "Stitch"},
    "ttc_tog_blocked": {
        "ru": "Эта настройка отключена в самом аккаунте TikTok — изменить нельзя.",
        "en": "This setting is turned off in your TikTok account — can't change it here.",
    },
    "ttc_brand_organic": {
        "ru": "Продвигаю свой бренд",
        "en": "Promoting my own brand",
    },
    "ttc_brand_content": {
        "ru": "Реклама другого бренда",
        "en": "Paid partnership",
    },
    "ttc_brand_not_private": {
        "ru": "Рекламу нельзя публиковать как «Только я» — смени приватность.",
        "en": "Branded content can't be private — change the visibility first.",
    },
    "ttc_music_notice": {
        "ru": (
            "Публикуя, ты соглашаешься с "
            "<a href=\"https://www.tiktok.com/legal/page/global/music-usage-confirmation/en\">"
            "Music Usage Confirmation</a> TikTok."
        ),
        "en": (
            "By posting, you agree to TikTok's "
            "<a href=\"https://www.tiktok.com/legal/page/global/music-usage-confirmation/en\">"
            "Music Usage Confirmation</a>."
        ),
    },
    "ttc_music_notice_brand": {
        "ru": (
            "Публикуя, ты соглашаешься с "
            "<a href=\"https://www.tiktok.com/legal/page/global/bc-policy/en\">"
            "Branded Content Policy</a> и "
            "<a href=\"https://www.tiktok.com/legal/page/global/music-usage-confirmation/en\">"
            "Music Usage Confirmation</a> TikTok."
        ),
        "en": (
            "By posting, you agree to TikTok's "
            "<a href=\"https://www.tiktok.com/legal/page/global/bc-policy/en\">"
            "Branded Content Policy</a> and "
            "<a href=\"https://www.tiktok.com/legal/page/global/music-usage-confirmation/en\">"
            "Music Usage Confirmation</a>."
        ),
    },
    "ttc_btn_title": {"ru": "✏️ Изменить подпись", "en": "✏️ Edit caption"},
    "ttc_btn_go": {"ru": "✅ Опубликовать", "en": "✅ Post it"},
    "ttc_btn_no": {"ru": "❌ Отменить", "en": "❌ Cancel"},
    "ttc_btn_auto": {
        "ru": "⚡ Больше не спрашивать — настроить автопубликацию",
        "en": "⚡ Stop asking — set up auto-posting",
    },
    "ttc_ask_title": {
        "ru": "Пришли новую подпись к видео (до 150 символов).",
        "en": "Send the new caption for the video (up to 150 characters).",
    },
    "ttc_title_saved": {
        "ru": "✅ Подпись обновлена: <i>{title}</i>",
        "en": "✅ Caption updated: <i>{title}</i>",
    },
    "ttc_need_privacy": {
        "ru": "Сначала выбери, кто увидит видео.",
        "en": "Choose who can see the video first.",
    },
    "ttc_confirmed": {
        "ru": (
            "✅ Принято: <i>{title}</i>\n"
            "Видео выйдет в TikTok по расписанию связки."
        ),
        "en": (
            "✅ Confirmed: <i>{title}</i>\n"
            "The video will go live on TikTok per your connection schedule."
        ),
    },
    "ttc_cancelled": {
        "ru": "❌ Публикация отменена: <i>{title}</i>. Файл удалён.",
        "en": "❌ Post cancelled: <i>{title}</i>. File removed.",
    },
    "ttc_expired": {
        "ru": (
            "⏳ Публикация отменена: <i>{title}</i>\n"
            "Подтверждение не пришло за {hours} ч, видео удалено с сервера."
        ),
        "en": (
            "⏳ Post cancelled: <i>{title}</i>\n"
            "No confirmation within {hours}h, the video was removed from the server."
        ),
    },
    "ttc_too_long": {
        "ru": (
            "⚠️ «{title}» не подходит для TikTok: длительность {duration} с, "
            "а лимит аккаунта — {limit} с."
        ),
        "en": (
            "⚠️ «{title}» doesn't fit TikTok: it's {duration}s long, "
            "the account limit is {limit}s."
        ),
    },
    "ttc_gone": {
        "ru": "Видео больше не найдено.",
        "en": "This video no longer exists.",
    },
    "ttc_stale": {
        "ru": "Эта карточка уже неактуальна — публикация обработана или отменена.",
        "en": "This card is out of date — the post was already handled or cancelled.",
    },
    "ttc_err_creator": {
        "ru": "TikTok не отвечает. Попробуй нажать ещё раз через минуту.",
        "en": "TikTok isn't responding. Try tapping again in a minute.",
    },
    "tts_header": {
        "ru": "🎵 <b>Автопубликация в TikTok</b>",
        "en": "🎵 <b>TikTok auto-posting</b>",
    },
    "tts_mode_auto": {
        "ru": "Режим: <b>автоматически</b> — видео выходят сами, без вопросов.",
        "en": "Mode: <b>automatic</b> — videos go out on their own, no questions.",
    },
    "tts_mode_card": {
        "ru": "Режим: <b>с подтверждением</b> — на каждое видео приходит карточка.",
        "en": "Mode: <b>confirm each</b> — every video arrives as a card to approve.",
    },
    "tts_privacy_gone": {
        "ru": (
            "👁 <b>Выбери заново, кто увидит видео</b>: прежний вариант аккаунту "
            "больше не доступен (например, профиль стал приватным)."
        ),
        "en": (
            "👁 <b>Pick who can see videos again</b>: the previous option is no "
            "longer available for the account (e.g. the profile went private)."
        ),
    },
    "tts_overlay_ignored": {
        "ru": (
            "⚠️ Оверлей не применяется: TikTok запрещает свои наложения на "
            "публикуемых видео."
        ),
        "en": (
            "⚠️ The overlay is skipped: TikTok forbids third-party overlays on "
            "posted videos."
        ),
    },
    "tts_consent": {
        "ru": (
            "Нажимая «Включить автопубликацию», ты разрешаешь боту публиковать "
            "видео этой связки в твой аккаунт TikTok с выбранными выше настройками "
            "— без отдельного подтверждения на каждое видео."
        ),
        "en": (
            "By tapping “Enable auto-posting” you allow the bot to publish this "
            "connection's videos to your TikTok account with the settings above "
            "— without confirming each video separately."
        ),
    },
    "tts_consent_given": {
        "ru": (
            "Согласие на автопубликацию выдано. Изменения настроек применяются "
            "к следующим видео; отозвать — кнопкой ниже."
        ),
        "en": (
            "Auto-posting consent is on. Setting changes apply to upcoming videos; "
            "revoke it with the button below."
        ),
    },
    "tts_btn_on": {"ru": "⚡ Включить автопубликацию", "en": "⚡ Enable auto-posting"},
    "tts_btn_off": {
        "ru": "🛑 Выключить (вернуть подтверждение)",
        "en": "🛑 Turn off (confirm each again)",
    },
    "tts_on": {
        "ru": (
            "⚡ Автопубликация включена. Новые видео этой связки будут выходить "
            "в TikTok по расписанию, без карточек."
        ),
        "en": (
            "⚡ Auto-posting enabled. New videos from this connection will go to "
            "TikTok on schedule, with no cards."
        ),
    },
    "tts_on_released": {
        "ru": (
            "⚡ Автопубликация включена. Видео, ожидавших подтверждения: {n} — "
            "они уйдут в TikTok по расписанию связки."
        ),
        "en": (
            "⚡ Auto-posting enabled. Videos that were awaiting confirmation: {n} — "
            "they'll go to TikTok on the connection schedule."
        ),
    },
    "tts_off": {
        "ru": (
            "🛑 Автопубликация выключена. На каждое новое видео снова придёт "
            "карточка подтверждения."
        ),
        "en": (
            "🛑 Auto-posting disabled. Every new video will come back as a "
            "confirmation card."
        ),
    },
    "tts_off_held": {
        "ru": (
            "🛑 Автопубликация выключена. Видео, уже готовых к выходу: {n} — "
            "они ждут подтверждения, карточки пришлю следом."
        ),
        "en": (
            "🛑 Auto-posting disabled. Videos already queued to go live: {n} — "
            "they now await confirmation, cards coming next."
        ),
    },
    "tts_unavailable": {
        "ru": "У этой связки нет автопубликации в TikTok.",
        "en": "This connection has no TikTok auto-posting.",
    },
    "pub_tt_reconnect": {
        "ru": (
            "🔑 Не удалось опубликовать «{title}»: доступ к TikTok устарел.\n"
            "Подключи аккаунт заново — после этого публикации продолжатся."
        ),
        "en": (
            "🔑 Couldn't publish «{title}»: the TikTok access is out of date.\n"
            "Reconnect the account and posting will resume."
        ),
    },
    "btn_reconnect_tiktok": {
        "ru": "🔄 Переподключить TikTok",
        "en": "🔄 Reconnect TikTok",
    },
    "sup_greeting": {
        "ru": (
            "👋 Привет! Это чат поддержки PosttiqBot.\n\n"
            "Опиши свой вопрос или проблему — можно текстом и скриншотами. "
            "Ответим тебе здесь же, как только сможем."
        ),
        "en": (
            "👋 Hi! This is PosttiqBot support chat.\n\n"
            "Describe your question or issue — text and screenshots are fine. "
            "We'll reply right here as soon as we can."
        ),
    },
    "sup_unavailable": {
        "ru": "⚠️ Поддержка временно недоступна. Попробуй чуть позже.",
        "en": "⚠️ Support is temporarily unavailable. Please try again a bit later.",
    },
    "sup_undelivered": {
        "ru": "⚠️ Не удалось доставить ответ пользователю (не начинал чат или заблокировал бота).",
        "en": "⚠️ Couldn't deliver the reply to the user (hasn't started the chat or blocked the bot).",
    },
    "sup_reply": {
        "ru": "💬 <b>Ответ поддержки:</b>\n\n{text}",
        "en": "💬 <b>Support reply:</b>\n\n{text}",
    },
    "support_open": {
        "ru": (
            "💬 <b>Поддержка</b>\n\n"
            "Нажми кнопку ниже — откроется чат поддержки. Напиши там свой вопрос "
            "или проблему, можно со скриншотами. Мы ответим в том же чате."
        ),
        "en": (
            "💬 <b>Support</b>\n\n"
            "Tap the button below to open the support chat. Describe your question "
            "or issue there (screenshots welcome). We'll reply in that chat."
        ),
    },
    "support_open_btn": {
        "ru": "💬 Открыть чат поддержки",
        "en": "💬 Open support chat",
    },
    "inv_title": {"ru": "Подписка PosttiqBot — {plan}", "en": "PosttiqBot subscription — {plan}"},
    "inv_desc": {"ru": "Доступ к авто-репостингу {period}.", "en": "Auto-reposting access {period}."},
    "inv_period_forever": {"ru": "навсегда", "en": "forever"},
    "inv_period_days": {"ru": "на {days} дней", "en": "for {days} days"},
    "inv_label": {"ru": "Подписка {plan}", "en": "Subscription {plan}"},
}


COMMANDS: tuple[tuple[str, dict[str, str]], ...] = (
    ("start", {"ru": "🏠 Главное меню", "en": "🏠 Main menu"}),
    ("profile", {"ru": "👤 Профиль", "en": "👤 Profile"}),
    ("tariffs", {"ru": "💎 Тарифы", "en": "💎 Plans"}),
    ("connections", {"ru": "📋 Мои подключения", "en": "📋 My connections"}),
    ("guide", {"ru": "📖 Как пользоваться", "en": "📖 How to use"}),
    ("referral", {"ru": "🎁 Пригласить друга", "en": "🎁 Invite a friend"}),
    ("support", {"ru": "💬 Поддержка", "en": "💬 Support"}),
    ("docs", {"ru": "📄 Документы", "en": "📄 Documents"}),
    ("policy", {"ru": "🔐 Политика конфиденциальности", "en": "🔐 Privacy Policy"}),
    ("terms", {"ru": "📄 Пользовательское соглашение", "en": "📄 Terms of Service"}),
)


def t(key: str, lang: str, **fmt) -> str:
    text = T.get(key, {}).get(lang) or T.get(key, {}).get(DEFAULT_LANG, key)
    return text.format(**fmt) if fmt else text


def command_descriptions(lang: str) -> list[tuple[str, str]]:
    """[(команда, описание)] на языке lang — для set_my_commands."""
    return [(cmd, txt.get(lang, txt[DEFAULT_LANG])) for cmd, txt in COMMANDS]


def label(action: str, lang: str) -> str:
    return LABELS[action].get(lang, LABELS[action][DEFAULT_LANG])


def labels(action: str) -> set[str]:
    """Все варианты метки (для матчинга нажатия независимо от языка и версии)."""
    return set(LABELS[action].values()) | set(LEGACY_LABELS.get(action, ()))


async def user_lang(telegram_id: int) -> str:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
    return user.lang if user and user.lang in LANGS else DEFAULT_LANG


async def set_user_lang(telegram_id: int, lang: str) -> None:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.lang = lang
