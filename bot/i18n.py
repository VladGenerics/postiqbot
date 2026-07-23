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
    "more": {"ru": "ℹ️ Ещё", "en": "ℹ️ More"},
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
    "more_title": {"ru": "ℹ️ <b>Дополнительно</b>", "en": "ℹ️ <b>More</b>"},
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
        "ru": "💳 Тариф <b>{plan}</b>. Выбери способ оплаты:",
        "en": "💳 <b>{plan}</b> plan. Choose a payment method:",
    },
    "btn_pay_stars": {"ru": "⭐ Telegram Stars ({stars})", "en": "⭐ Telegram Stars ({stars})"},
    "btn_pay_rub": {"ru": "₽ СБП / карта ({price})", "en": "💳 Card / SBP ({price})"},
    "price_line": {
        "ru": "• {plan} — <b>{price}</b> ({accounts} акк, {videos} видео/день)",
        "en": "• {plan} — <b>{price}</b> ({accounts} accounts, {videos} videos/day)",
    },
    "rub_soon": {
        "ru": "₽ Оплата через СБП/карту скоро подключится. Пока можно оплатить через Telegram Stars (⭐) или написать в «✍️ Поддержка».",
        "en": "₽ Card/SBP payment is coming soon. For now use Telegram Stars (⭐) or contact «✍️ Support».",
    },
    "pay_link": {
        "ru": "💳 Счёт на <b>{amount} ₽</b> ({plan}) создан.\nОплати по кнопке ниже — доступ активируется автоматически после оплаты.",
        "en": "💳 Invoice for <b>{amount} ₽</b> ({plan}) created.\nPay via the button below — access activates automatically after payment.",
    },
    "btn_pay_now": {"ru": "💳 Оплатить {amount} ₽", "en": "💳 Pay {amount} ₽"},
    "pay_error": {
        "ru": "⚠️ Не удалось создать счёт. Попробуй позже или напиши в «✍️ Поддержка».",
        "en": "⚠️ Couldn't create the invoice. Try later or contact «✍️ Support».",
    },
    "status_admin": {"ru": "♾ Безлимитный доступ (админ)", "en": "♾ Unlimited access (admin)"},
    "expiry_soon": {
        "ru": (
            "⏳ Твой доступ заканчивается <b>{date}</b>.\n"
            "Продли подписку, чтобы бот не переставал публиковать — нажми «💳 Тарифы»."
        ),
        "en": (
            "⏳ Your access ends on <b>{date}</b>.\n"
            "Renew to keep the bot publishing — tap «💳 Plans»."
        ),
    },
    "publish_failed_auth": {
        "ru": (
            "❌ Не удалось опубликовать «{title}»: возможно, отозван доступ к каналу.\n"
            "Переподключи аккаунт: «🔗 Подключить аккаунт»."
        ),
        "en": (
            "❌ Couldn't publish «{title}»: channel access may have been revoked.\n"
            "Reconnect the account: «🔗 Connect account»."
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
            "«➕ Подключения» → «➕ Новое подключение» → «🔗 Подключить аккаунт» → "
            "YouTube или TikTok (вход через официальный OAuth).\n\n"
            "<b>2. Добавь источник</b>\n"
            "«➕ Новое подключение» → «➕ Добавить источник» → пришли ссылку на канал "
            "(YouTube @handle/ссылку или ссылку на профиль TikTok).\n\n"
            "<b>3. Настрой связку</b>\n"
            "«📋 Мои подключения» → выбери связку: расписание (сразу/интервал/по времени), "
            "оверлей (картинка/GIF), доступ, пауза.\n"
            "📥 <b>Залить архив</b> — поставить в очередь <b>прошлые</b> видео источника "
            "(старые → новые). Выходят по 4/день на связку.\n\n"
            "<b>Важно</b>\n"
            "• Публикуются только <b>новые</b> видео (одно видео не репостится дважды).\n"
            "• TikTok-публикация приходит в черновики — публикуешь сам в приложении.\n"
            "• Доступ: триал, затем подписка («💎 Тарифы»). Вопросы — «🛠 Поддержка»."
        ),
        "en": (
            "📖 <b>How to use PostiqBot</b>\n\n"
            "The bot automatically takes new videos from a source channel and publishes "
            "them to your channel (YouTube or TikTok) on schedule.\n\n"
            "<b>1. Connect your channel</b>\n"
            "«➕ Connections» → «➕ New connection» → «🔗 Connect account» → "
            "YouTube or TikTok (official OAuth sign-in).\n\n"
            "<b>2. Add a source</b>\n"
            "«➕ New connection» → «➕ Add source» → send a channel link "
            "(YouTube @handle/link or a TikTok profile link).\n\n"
            "<b>3. Configure the link</b>\n"
            "«📋 My connections» → pick a link: schedule (immediate/interval/times), "
            "overlay (image/GIF), visibility, pause.\n"
            "📥 <b>Backfill</b> — queue the source's <b>past</b> videos "
            "(oldest → newest). They publish at 4/day per connection.\n\n"
            "<b>Important</b>\n"
            "• Only <b>new</b> videos are published (a video isn't reposted twice).\n"
            "• TikTok posts land in drafts — you publish them yourself in the app.\n"
            "• Access: trial, then subscription («💎 Plans»). Questions — «🛠 Support»."
        ),
    },
    "referral": {
        "ru": (
            "🎁 <b>Реферальная программа</b>\n\n"
            "Приглашай друзей! Когда приглашённый оформит подписку — тебе "
            "начислят <b>такой же тариф на тот же срок</b>.\n\n"
            "Твоя ссылка:\n{link}\n\n"
            "👥 Приглашено: <b>{invited}</b>\n💳 Оплатили (бонус начислен): <b>{paid}</b>"
        ),
        "en": (
            "🎁 <b>Referral program</b>\n\n"
            "Invite friends! When an invited user buys a subscription, you get "
            "<b>the same plan for the same period</b>.\n\n"
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
    "c_priv_private": {"ru": "🔒 приватное", "en": "🔒 private"},
    "c_priv_unlisted": {"ru": "🔗 по ссылке", "en": "🔗 unlisted"},
    "c_priv_public": {"ru": "🌍 публичное", "en": "🌍 public"},
    "c_card": {
        "ru": (
            "<b>Связка #{id}</b>\n\n"
            "📡 Источник: <b>{src}</b>\n"
            "📤 Публикую на: <b>{dst}</b>\n"
            "👁 Доступ публикаций: {priv}\n"
            "⏰ Расписание: {sched}\n"
            "🖼 Оверлей: {ovl}\n"
            "⚙️ Статус: {status}"
        ),
        "en": (
            "<b>Connection #{id}</b>\n\n"
            "📡 Source: <b>{src}</b>\n"
            "📤 Publishing to: <b>{dst}</b>\n"
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
    "c_btn_delete": {"ru": "🗑 Удалить", "en": "🗑 Delete"},
    "c_btn_to_list": {"ru": "« К списку", "en": "« Back to list"},
    "c_btn_back": {"ru": "« Назад", "en": "« Back"},
    "c_btn_cancel": {"ru": "« Отмена", "en": "« Cancel"},
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
    "bf_choose_daily": {
        "ru": "📅 Сколько видео публиковать в день?",
        "en": "📅 How many videos to publish per day?",
    },
    "gate_prompt": {
        "ru": (
            "👋 Привет! Чтобы получить <b>7 дней бесплатного доступа</b> к PostiqBot, "
            "подпишись на наш канал 👇"
        ),
        "en": (
            "👋 Hi! To get <b>7 days of free access</b> to PostiqBot, "
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
            "🎁 Твой приглашённый оформил подписку <b>{plan}</b> — тебе тоже <b>+{days} дней</b> того же тарифа!\n"
            "Доступ активен до <b>{date}</b>."
        ),
        "en": (
            "🎁 Your referral bought a <b>{plan}</b> subscription — you get <b>+{days} days</b> of the same plan!\n"
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
    "sup_greeting": {
        "ru": (
            "👋 Привет! Это чат поддержки PostiqBot.\n\n"
            "Опиши свой вопрос или проблему — можно текстом и скриншотами. "
            "Ответим тебе здесь же, как только сможем."
        ),
        "en": (
            "👋 Hi! This is PostiqBot support chat.\n\n"
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
    "support_open": {
        "ru": (
            "🛠 <b>Поддержка</b>\n\n"
            "Нажми кнопку ниже — откроется чат поддержки. Напиши там свой вопрос "
            "или проблему, можно со скриншотами. Мы ответим в том же чате."
        ),
        "en": (
            "🛠 <b>Support</b>\n\n"
            "Tap the button below to open the support chat. Describe your question "
            "or issue there (screenshots welcome). We'll reply in that chat."
        ),
    },
    "support_open_btn": {
        "ru": "💬 Открыть чат поддержки",
        "en": "💬 Open support chat",
    },
    "inv_title": {"ru": "Подписка PostiqBot — {plan}", "en": "PostiqBot subscription — {plan}"},
    "inv_desc": {"ru": "Доступ к авто-репостингу {period}.", "en": "Auto-reposting access {period}."},
    "inv_period_forever": {"ru": "навсегда", "en": "forever"},
    "inv_period_days": {"ru": "на {days} дней", "en": "for {days} days"},
    "inv_label": {"ru": "Подписка {plan}", "en": "Subscription {plan}"},
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
