"""Публичный сайт PosttiqBot: главная, разделы продукта, Terms of Service, Privacy Policy."""
from __future__ import annotations

import os
import re

from aiohttp import web

from bot.config import fmt_limit, get_settings
from bot.web.icons import icon

_ASSETS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets"))
_LOGO_PNG = os.path.join(_ASSETS, "logo.png")
_WEB_DIR = os.path.join(_ASSETS, "web")
_ASSET_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

BOT_URL = "https://t.me/Posttiq_bot"


def _app() -> str:
    """Имя приложения для заголовков — должно совпадать с TikTok Developer Portal."""
    return get_settings().site_app_name or "PosttiqBot"


LOGO_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' role='img' aria-label='App logo'>"
    "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
    "<stop offset='0' stop-color='#a855f7'/><stop offset='1' stop-color='#6d28d9'/></linearGradient></defs>"
    "<rect x='3' y='3' width='58' height='58' rx='15' fill='#0d0a17' stroke='url(#g)' stroke-width='3'/>"
    "<rect x='30' y='9' width='4' height='9' rx='2' fill='url(#g)'/><circle cx='32' cy='9' r='3.2' fill='url(#g)'/>"
    "<rect x='17' y='19' width='30' height='24' rx='10' fill='url(#g)'/>"
    "<rect x='24' y='27' width='4.5' height='9' rx='2.2' fill='#fff'/>"
    "<rect x='35.5' y='27' width='4.5' height='9' rx='2.2' fill='#fff'/>"
    "<rect x='22' y='46' width='20' height='10' rx='5' fill='url(#g)'/></svg>"
)

_NAV = (
    ("/", "Home"),
    ("/features", "Features"),
    ("/how-it-works", "How it works"),
    ("/pricing", "Pricing"),
    ("/faq", "FAQ"),
    ("/support", "Support"),
    ("/terms", "Terms"),
    ("/privacy", "Privacy"),
)

_CSS_BASE = """
@font-face{font-family:Geist;src:url(/asset/geist.woff2) format('woff2');font-weight:100 900;font-display:swap}
@font-face{font-family:'Geist Mono';src:url(/asset/geist-mono.woff2) format('woff2');font-weight:400 500;font-display:swap}
:root{--bg:#07060c;--bg-soft:#0c0a14;--panel:#12101c;--panel-hi:#181423;
--line:rgba(255,255,255,.08);--line-hi:rgba(255,255,255,.16);
--fg:#f2f0f7;--body:#d9d5e4;--muted:#9d97b0;
--acc:#c93bf0;--acc-lt:#e4a9ff;--acc-ink:#0a0610;--r:16px;--r-chip:12px;
--glass:rgba(255,255,255,.05);--glass-hi:rgba(255,255,255,.085);
--blur:saturate(150%) blur(20px);
--edge:inset 0 1px 0 rgba(255,255,255,.09),0 22px 44px -34px rgba(0,0,0,.95)}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);line-height:1.65;
font-family:Geist,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
/* Свет за стеклом: слой fixed, поэтому у панелей всегда есть что размывать. */
body::before{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
background:radial-gradient(58% 46% at 78% -8%,rgba(201,59,240,.22),transparent 70%),
radial-gradient(44% 40% at 4% -6%,rgba(124,58,237,.16),transparent 70%),
radial-gradient(52% 34% at 92% 78%,rgba(201,59,240,.10),transparent 72%),
radial-gradient(40% 30% at 2% 46%,rgba(124,58,237,.09),transparent 72%)}
a{color:var(--acc-lt);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
img{max-width:100%;height:auto}
.ic{flex:none;vertical-align:-.18em}
h1,h2,h3,h4{letter-spacing:-.025em;line-height:1.14}
h1{font-size:clamp(30px,4.4vw,44px);font-weight:700;margin:0 0 .3em}
h2{font-size:clamp(22px,2.6vw,28px);font-weight:600;margin:2.4em 0 .6em}
h3{font-size:18px;font-weight:600;margin:1.5em 0 .35em}
p,li{color:var(--body)}
.lead{font-size:clamp(16px,1.7vw,19px);color:var(--muted);max-width:62ch;margin:0 0 1.4em}
.muted,small{color:var(--muted)}
ul,ol{padding-left:22px}li{margin:.35em 0}
b{font-weight:600;color:var(--fg)}
::selection{background:rgba(201,59,240,.35)}
:focus-visible{outline:2px solid var(--acc-lt);outline-offset:3px;border-radius:8px}
"""

_CSS_SHELL = """
header.site{position:sticky;top:0;z-index:20;background:rgba(9,7,16,.62);
backdrop-filter:saturate(150%) blur(22px);-webkit-backdrop-filter:saturate(150%) blur(22px);
border-bottom:1px solid var(--line);box-shadow:inset 0 -1px 0 rgba(255,255,255,.04)}
header.site .in{max-width:1120px;margin:0 auto;padding:12px 22px;display:flex;align-items:center;gap:16px}
.brand{display:flex;align-items:center;gap:10px;color:var(--fg);font-weight:700;font-size:17px;letter-spacing:-.02em;flex:none}
.brand:hover{text-decoration:none}
.brand img{width:30px;height:30px;border-radius:9px;object-fit:cover}
header.site nav{display:flex;gap:3px;margin-right:auto;overflow-x:auto;scrollbar-width:none}
header.site nav::-webkit-scrollbar{display:none}
header.site nav a{color:var(--muted);font-size:14.5px;padding:7px 11px;border-radius:999px;
white-space:nowrap;transition:color .15s,background .15s}
header.site nav a:hover{color:var(--fg);background:rgba(255,255,255,.05);text-decoration:none}
header.site nav a.on{color:var(--fg);background:rgba(201,59,240,.14);box-shadow:inset 0 0 0 1px rgba(201,59,240,.35)}
header.site .btn{flex:none}
@media(max-width:900px){header.site .in{flex-wrap:wrap;gap:10px}
header.site nav{order:3;width:100%;margin:0}header.site .btn{margin-left:auto}}
main{max-width:1120px;margin:0 auto;padding:52px 22px 0}
main.doc{max-width:820px}
main.doc h2{font-size:21px;border-bottom:1px solid var(--line);padding-bottom:.4em}
.pagehead{margin:0 0 30px}
footer.site{border-top:1px solid var(--line);background:var(--bg-soft);margin-top:86px}
footer.site .in{max-width:1120px;margin:0 auto;padding:46px 22px 26px;
display:grid;grid-template-columns:1.5fr repeat(3,1fr);gap:30px}
footer.site h4{font-size:12.5px;text-transform:uppercase;letter-spacing:.09em;
color:var(--muted);margin:0 0 12px;font-weight:600}
footer.site a{color:#cbc6da;font-size:14.5px;display:block;padding:3px 0}
footer.site a:hover{color:var(--fg)}
footer.site p{color:var(--muted);font-size:14px;margin:12px 0 0;max-width:36ch}
footer.site .legal{grid-column:1/-1;border-top:1px solid var(--line);padding-top:20px;
color:var(--muted);font-size:13.5px}
@media(max-width:820px){footer.site .in{grid-template-columns:1fr 1fr}}
"""

_CSS_UI = """
.btn{display:inline-flex;align-items:center;gap:8px;background:var(--acc);color:var(--acc-ink);
font-weight:600;font-size:15px;padding:11px 20px;border-radius:999px;white-space:nowrap;
box-shadow:0 6px 24px -8px rgba(201,59,240,.7);transition:transform .12s,box-shadow .2s}
.btn:hover{text-decoration:none;transform:translateY(-1px);box-shadow:0 11px 30px -8px rgba(201,59,240,.85)}
.btn:active{transform:translateY(0) scale(.985)}
.btn.ghost{background:rgba(255,255,255,.05);backdrop-filter:var(--blur);
-webkit-backdrop-filter:var(--blur);color:var(--fg);box-shadow:inset 0 0 0 1px var(--line-hi)}
.btn.ghost:hover{background:rgba(255,255,255,.1);box-shadow:inset 0 0 0 1px var(--line-hi)}
.btn.sm{padding:9px 16px;font-size:14px}
.actions{display:flex;flex-wrap:wrap;gap:12px;margin:28px 0 0}
.hero{display:grid;grid-template-columns:1.05fr .95fr;gap:clamp(26px,5vw,60px);align-items:center;padding:10px 0 24px}
.hero h1{font-size:clamp(34px,5.2vw,56px);line-height:1.03;letter-spacing:-.035em;margin:0 0 18px}
.hero h1 em{font-style:normal;color:var(--acc-lt)}
.hero .lead{margin-bottom:0}
.heroart{position:relative}
.heroart img{width:100%;display:block}
.heroart::after{content:'';position:absolute;inset:10% 8%;z-index:-1;border-radius:50%;
background:radial-gradient(circle,rgba(201,59,240,.5),transparent 70%);filter:blur(48px)}
@media(max-width:860px){.hero{grid-template-columns:1fr}.heroart{order:-1;max-width:330px}}
.trust{display:flex;flex-wrap:wrap;gap:9px 20px;margin:28px 0 0;color:var(--muted);font-size:14px}
.trust span{display:inline-flex;align-items:center;gap:7px}
.trust .ic{color:var(--acc-lt)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin:24px 0}
.cards.w4{grid-template-columns:repeat(auto-fit,minmax(238px,1fr))}
.card{background:var(--glass);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);
border:1px solid var(--line);border-radius:var(--r);padding:22px;box-shadow:var(--edge);
transition:border-color .2s,background .2s,transform .12s}
.card:hover{border-color:var(--line-hi);background:var(--glass-hi);transform:translateY(-2px)}
.chip{width:40px;height:40px;border-radius:var(--r-chip);display:flex;align-items:center;justify-content:center;
background:rgba(201,59,240,.13);color:var(--acc-lt);box-shadow:inset 0 0 0 1px rgba(201,59,240,.28);margin-bottom:14px}
.card h3{margin:0 0 6px;font-size:16.5px}
.card p{margin:0;color:var(--muted);font-size:14.8px;line-height:1.6}
.card p+p{margin-top:.7em}
ol.steps{background:var(--glass);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);
border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--edge);
list-style:none;counter-reset:s;padding:0;margin:24px 0;overflow:hidden}
ol.steps li{counter-increment:s;position:relative;padding:16px 20px 16px 64px;
border-top:1px solid var(--line);transition:background .15s}
ol.steps li:first-child{border-top:0}
ol.steps li:hover{background:rgba(255,255,255,.04)}
ol.steps li::before{content:counter(s);position:absolute;left:18px;top:14px;width:32px;height:32px;
border-radius:999px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600;
color:var(--acc-lt);background:rgba(201,59,240,.13);box-shadow:inset 0 0 0 1px rgba(201,59,240,.3)}
.plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(262px,1fr));gap:16px;margin:24px 0}
.plan{background:var(--glass);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);
border:1px solid var(--line);border-radius:var(--r);padding:24px;box-shadow:var(--edge);
display:flex;flex-direction:column}
.plan.hot{border-color:rgba(201,59,240,.45);
background:linear-gradient(168deg,rgba(201,59,240,.15),rgba(255,255,255,.05) 58%);
box-shadow:var(--edge),0 30px 64px -36px rgba(201,59,240,.8)}
.plan .name{display:flex;align-items:center;gap:9px;font-weight:600;font-size:17px}
.plan .tag{margin-left:auto;font-size:11px;text-transform:uppercase;letter-spacing:.08em;
padding:4px 10px;border-radius:999px;background:rgba(201,59,240,.16);color:var(--acc-lt)}
.plan .price{margin:18px 0 2px;font-size:30px;font-weight:700;letter-spacing:-.03em}
.plan .price span{font-size:14px;font-weight:400;color:var(--muted);letter-spacing:0}
.plan .alt{color:var(--muted);font-size:14px;margin:0 0 18px}
.plan ul{list-style:none;padding:0;margin:0 0 22px}
.plan li{display:flex;gap:9px;align-items:flex-start;font-size:14.8px;margin:.5em 0}
.plan li .ic{color:var(--acc-lt);margin-top:4px}
.plan .btn{margin-top:auto;justify-content:center}
.faqlist{margin:20px 0 8px;background:var(--glass);backdrop-filter:var(--blur);
-webkit-backdrop-filter:var(--blur);border:1px solid var(--line);border-radius:var(--r);
box-shadow:var(--edge);overflow:hidden}
.faqlist details{border-top:1px solid var(--line)}
.faqlist details:first-child{border-top:0}
.faqlist summary{cursor:pointer;list-style:none;padding:16px 48px 16px 20px;position:relative;
font-weight:600;font-size:16px;color:var(--fg);transition:background .15s,color .15s}
.faqlist summary::-webkit-details-marker{display:none}
.faqlist summary .ic{position:absolute;right:18px;top:17px;color:var(--acc-lt);transition:transform .2s}
.faqlist details[open] summary .ic{transform:rotate(45deg)}
.faqlist summary:hover{color:var(--acc-lt);background:rgba(255,255,255,.04)}
.faqlist .a{padding:0 48px 18px 20px;color:var(--muted);font-size:15px}
.faqlist .a p{margin:0 0 .7em;color:var(--muted)}
.faqlist .a p:last-child{margin:0}
figure.shot{margin:26px 0;padding:0}
figure.shot img{width:100%;display:block}
figure.shot figcaption{color:var(--muted);font-size:13.5px;margin-top:10px}
.split{display:grid;grid-template-columns:1fr 1fr;gap:clamp(22px,4vw,46px);align-items:center;margin:28px 0}
.split figure.shot,.split p:last-child{margin:0}
@media(max-width:860px){.split{grid-template-columns:1fr}}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(238px,1fr));gap:16px;margin:24px 0}
.gallery img{width:100%;display:block}
.band{margin:70px 0 0;padding:clamp(26px,4vw,42px);border-radius:var(--r);
border:1px solid rgba(201,59,240,.3);box-shadow:var(--edge);
background:linear-gradient(140deg,rgba(201,59,240,.2),rgba(124,58,237,.07) 55%,rgba(255,255,255,.05));
backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);
display:flex;flex-wrap:wrap;align-items:center;gap:22px}
.band h2{margin:0;font-size:clamp(21px,2.6vw,27px)}
.band p{margin:8px 0 0;color:var(--muted);max-width:52ch}
.band .actions{margin:0 0 0 auto}
/* Картинки в стеклянной рамке: тонкая полупрозрачная подложка + внутренний
   отступ, чтобы неоновые баннеры не примыкали к краю вплотную. */
.heroart img,figure.shot img,.gallery img{border-radius:var(--r);
padding:6px;background:var(--glass);backdrop-filter:var(--blur);
-webkit-backdrop-filter:var(--blur);box-shadow:var(--edge);
border:1px solid var(--line)}
.gallery img{transition:border-color .2s,transform .12s}
.gallery img:hover{border-color:var(--line-hi);transform:translateY(-2px)}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.pagehead,.hero>*{animation:rise .5s cubic-bezier(.2,.7,.3,1) both}
.hero>*+*{animation-delay:.09s}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
/* Откат на непрозрачные панели: старые браузеры без backdrop-filter и
   пользователи, которые просили меньше прозрачности. Без этого текст на
   просвечивающем градиенте теряет контраст. */
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
:root{--glass:#12101c;--glass-hi:#181423}
header.site{background:var(--bg)}}
@media(prefers-reduced-transparency:reduce){
:root{--glass:#12101c;--glass-hi:#181423}
header.site{background:var(--bg)}
.card,.plan,.faqlist,ol.steps,.band,.btn.ghost,
.heroart img,figure.shot img,.gallery img{backdrop-filter:none;-webkit-backdrop-filter:none}
.btn.ghost{background:var(--panel-hi)}
.plan.hot,.band{background:var(--panel-hi)}}
/* Страница результата OAuth (/oauth/callback, /tiktok/callback): одна карточка
   по центру. Пользователь попадает сюда из браузера сразу после согласия — тут
   не нужны ни hero, ни сетки, только «получилось / не получилось» и путь назад. */
.result{max-width:560px;margin:min(8vh,72px) auto 0;text-align:center;
background:var(--glass);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);
border:1px solid var(--line);border-radius:var(--r);padding:clamp(26px,5vw,40px);
box-shadow:var(--edge);animation:rise .5s cubic-bezier(.2,.7,.3,1) both}
.result .seal{position:relative;width:72px;height:72px;margin:0 auto 22px;
border-radius:20px;display:flex;align-items:center;justify-content:center;
background:rgba(201,59,240,.13);color:var(--acc-lt);box-shadow:inset 0 0 0 1px rgba(201,59,240,.28)}
.result .seal .badge{position:absolute;right:-9px;bottom:-9px;width:30px;height:30px;
border-radius:999px;display:flex;align-items:center;justify-content:center;
background:var(--bg-soft);color:var(--acc-lt);box-shadow:inset 0 0 0 1px var(--line-hi)}
.result.bad .seal{background:rgba(255,255,255,.06);color:var(--fg);
box-shadow:inset 0 0 0 1px var(--line-hi)}
.result h1{font-size:clamp(23px,3.2vw,31px);margin:0 0 12px}
.result p{color:var(--muted);margin:0}
.result .why{font-family:'Geist Mono',ui-monospace,monospace;font-size:13px;
color:var(--muted);text-align:left;word-break:break-word;background:rgba(255,255,255,.04);
border:1px solid var(--line);border-radius:var(--r-chip);padding:11px 14px;margin:18px 0 0}
.result .actions{justify-content:center;margin-top:26px}
.result .note{margin-top:18px;font-size:14px}
"""

_CSS = _CSS_BASE + _CSS_SHELL + _CSS_UI


_DOC_PATHS = ("/terms", "/privacy")


def _page(title: str, h1: str, body: str, path: str = "", hero: str = "") -> web.Response:
    """Каркас страницы."""
    app = _app()
    nav = "".join(
        "<a href='{}'{}>{}</a>".format(href, " class='on'" if href == path else "", label)
        for href, label in _NAV
    )
    head = hero or f"<div class='pagehead'><h1>{h1}</h1></div>"
    main_cls = " class='doc'" if path in _DOC_PATHS else ""
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<link rel='icon' href='/logo'>"
        "<meta name='theme-color' content='#07060c'>"
        f"<meta name='description' content='{app} automates cross-posting your videos "
        "between your own YouTube and TikTok accounts.'>"
        f"<title>{title}</title><style>{_CSS}</style></head><body>"
        "<header class='site'><div class='in'>"
        f"<a class='brand' href='/'><img src='/logo' alt=''>{app}</a>"
        f"<nav>{nav}</nav>"
        f"<a class='btn sm' href='{BOT_URL}'>{icon('telegram-logo', 18)}Open bot</a>"
        "</div></header>"
        f"<main{main_cls}>{head}{body}</main>"
        f"{_footer(app)}</body></html>"
    )
    return web.Response(text=html, content_type="text/html")


def _footer(app: str) -> str:
    return (
        "<footer class='site'><div class='in'>"
        f"<div><a class='brand' href='/'><img src='/logo' alt=''>{app}</a>"
        f"<p>Automated cross-posting between your own YouTube and TikTok accounts, "
        "run from a Telegram bot.</p></div>"
        "<div><h4>Product</h4><a href='/features'>Features</a>"
        "<a href='/how-it-works'>How it works</a><a href='/pricing'>Pricing</a></div>"
        "<div><h4>Help</h4><a href='/faq'>FAQ</a><a href='/support'>Support</a>"
        f"<a href='{BOT_URL}'>Telegram bot</a></div>"
        "<div><h4>Legal</h4><a href='/terms'>Terms of Service</a>"
        "<a href='/privacy'>Privacy Policy</a></div>"
        f"<div class='legal'>© 2026 {app}. All rights reserved. "
        "Not affiliated with YouTube, Google or TikTok; publishing happens through "
        "their official APIs with the authorization you grant.</div>"
        "</div></footer>"
    )


def _card(icon_name: str, title: str, text: str) -> str:
    """Карточка с иконкой Phosphor."""
    return (
        f"<div class='card'><div class='chip'>{icon(icon_name, 21)}</div>"
        f"<h3>{title}</h3><p>{text}</p></div>"
    )


def _shot(name: str, alt: str, caption: str = "", lazy: bool = True) -> str:
    """Картинка бренда из bot/assets/web (те же баннеры, что в боте)."""
    load = " loading='lazy' decoding='async'" if lazy else ""
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return (
        f"<figure class='shot'><img src='/asset/{name}.jpg' alt='{alt}' "
        f"width='1000' height='654'{load}>{cap}</figure>"
    )


def _band(heading: str, text: str, label: str = "Open the bot") -> str:
    """Финальная CTA-полоса."""
    return (
        f"<section class='band'><div><h2>{heading}</h2><p>{text}</p></div>"
        f"<div class='actions'><a class='btn' href='{BOT_URL}'>"
        f"{icon('telegram-logo', 18)}{label}</a></div></section>"
    )


def _contact_sentence() -> str:
    """Контакт поддержки: бот всегда, e-mail/username — если задан в настройках."""
    extra = get_settings().support_contact
    return (
        f"<a href='{BOT_URL}'>@Posttiq_bot</a>"
        + (f" or {extra}" if extra else "")
    )


_RESULT_TXT: dict[str, dict[str, str]] = {
    "ru": {
        "back": "Вернуться в Telegram",
        "note": "Эту страницу можно закрыть — дальше всё в боте.",
    },
    "en": {
        "back": "Back to Telegram",
        "note": "You can close this page — the rest happens in the bot.",
    },
}

_RESULT_ICONS = {"tiktok": "tiktok-logo", "youtube": "youtube-logo"}


def web_lang(request: web.Request) -> str:
    """ru/en по Accept-Language браузера (по умолчанию — язык сайта, en)."""
    accept = request.headers.get("Accept-Language", "")
    return "ru" if accept[:2].lower() == "ru" else "en"


def result_page(
    title: str,
    text: str,
    *,
    lang: str = "en",
    ok: bool = True,
    platform: str | None = None,
    detail: str = "",
) -> web.Response:
    """Результат подключения аккаунта — в оформлении сайта."""
    txt = _RESULT_TXT.get(lang, _RESULT_TXT["en"])
    if ok:
        seal = (
            f"{icon(_RESULT_ICONS.get(platform or '', 'link-simple'), 34)}"
            f"<span class='badge'>{icon('check-circle', 19)}</span>"
        )
    else:
        seal = icon("warning-circle", 34)
    card = (
        f"<section class='result{'' if ok else ' bad'}'>"
        f"<div class='seal'>{seal}</div>"
        f"<h1>{title}</h1><p>{text}</p>"
        + (f"<p class='why'>{detail}</p>" if detail else "")
        + f"<div class='actions'><a class='btn' href='{BOT_URL}'>"
        f"{icon('telegram-logo', 18)}{txt['back']}</a></div>"
        f"<p class='note muted'>{txt['note']}</p>"
        "</section>"
    )
    return _page(f"{_app()} — {title}", title, "", hero=card)


async def logo(_: web.Request) -> web.Response:
    """Иконка приложения: PNG-робот из assets, иначе SVG-запас."""
    if os.path.exists(_LOGO_PNG):
        return web.FileResponse(_LOGO_PNG, headers={"Cache-Control": "public, max-age=86400"})
    return web.Response(text=LOGO_SVG, content_type="image/svg+xml")


async def asset(request: web.Request) -> web.Response:
    """Статика сайта из bot/assets/web: баннеры (jpg) и шрифты (woff2)."""
    name = request.match_info["name"]
    if not _ASSET_NAME.match(name):
        raise web.HTTPNotFound()
    path = os.path.normpath(os.path.join(_WEB_DIR, name))
    if os.path.dirname(path) != _WEB_DIR or not os.path.isfile(path):
        raise web.HTTPNotFound()
    headers = {"Cache-Control": "public, max-age=604800"}
    if name.endswith(".woff2"):
        headers["Content-Type"] = "font/woff2"
    return web.FileResponse(path, headers=headers)


async def landing(_: web.Request) -> web.Response:
    app = _app()
    hero = (
        "<section class='hero'>"
        "<div>"
        f"<h1>{app} reposts your videos <em>for you</em></h1>"
        f"<p class='lead'>{app} watches a source channel and re-publishes every new "
        "video to your own YouTube and TikTok accounts on the schedule you set. "
        "Connect once in Telegram; no manual downloading, no re-uploading.</p>"
        "<div class='actions'>"
        f"<a class='btn' href='{BOT_URL}'>{icon('telegram-logo', 18)}Open in Telegram</a>"
        "<a class='btn ghost' href='/how-it-works'>See how it works</a>"
        "</div>"
        "<div class='trust'>"
        f"<span>{icon('seal-check', 17)}Official YouTube and TikTok APIs</span>"
        f"<span>{icon('lock-key', 17)}Encrypted OAuth tokens</span>"
        f"<span>{icon('gift', 17)}Free trial for new users</span>"
        "</div></div>"
        "<div class='heroart'>"
        f"<img src='/asset/hero.jpg' alt='{app} mascot' width='900' height='992' "
        "decoding='async'></div>"
        "</section>"
    )
    body = (
        f"<h2>What {app} does</h2>"
        "<div class='cards'>"
        + _card("link-simple", "Connect your accounts",
                "Link your own YouTube and TikTok accounts through official OAuth. "
                "You stay in control and can revoke access at any time.")
        + _card("broadcast", "Add a source",
                f"Choose a channel to watch. When a new video appears, {app} picks it "
                "up automatically.")
        + _card("calendar-check", "Schedule",
                "Publish immediately, at a fixed interval, or at set times of day, so "
                "your posts are spread evenly.")
        + _card("image-square", "Overlay",
                "Add an image or GIF watermark over every video, with a live preview "
                "of position and size.")
        + _card("eye", "Visibility",
                "For YouTube, choose public, unlisted or private per connection.")
        + _card("stack", "Backfill",
                "Optionally queue a channel's past videos and re-publish them "
                "oldest-to-newest.")
        + "</div>"
        "<p><a href='/features'>See all features →</a></p>"

        "<h2>Supported platforms</h2>"
        "<div class='cards'>"
        + _card("youtube-logo", "YouTube",
                "Publishing through the official YouTube Data API v3, with the "
                "visibility you pick for each connection.")
        + _card("tiktok-logo", "TikTok",
                "Publishing through the official TikTok Content Posting API. Videos "
                "land in your TikTok drafts, so you review and post them yourself.")
        + "</div>"

        "<h2>Set up in three steps</h2>"
        "<ol class='steps'>"
        "<li><b>Open the bot</b> in Telegram and start a free trial.</li>"
        "<li><b>Connect the account</b> you want to publish to, via official OAuth.</li>"
        "<li><b>Add a source channel</b> and set your schedule. That is it.</li>"
        "</ol>"
        "<p><a href='/how-it-works'>Read the detailed walkthrough →</a> · "
        "<a href='/pricing'>See pricing →</a></p>"

        "<h2>How it looks in Telegram</h2>"
        "<p class='lead'>The whole product lives in a chat: connect an account, point "
        "it at a source, and manage everything from the same place.</p>"
        "<div class='gallery'>"
        f"<img src='/asset/connect.jpg' alt='Connecting an account in the bot' "
        "width='1000' height='654' loading='lazy' decoding='async'>"
        f"<img src='/asset/source.jpg' alt='Adding a source channel' "
        "width='1000' height='654' loading='lazy' decoding='async'>"
        f"<img src='/asset/connections.jpg' alt='Managing connections' "
        "width='1000' height='654' loading='lazy' decoding='async'>"
        "</div>"

        + _band(
            "Ready to stop re-uploading by hand?",
            "Start with the free trial: connect an account, add a source, and watch "
            "the first video publish itself.",
            "Get started",
        )
    )
    return _page(f"{app} · Automated video cross-posting", app, body, "/", hero=hero)


async def features(_: web.Request) -> web.Response:
    app = _app()
    body = (
        f"<p class='lead'>Everything {app} can do for your own channels, in detail. "
        "Every plan includes the full feature set.</p>"

        "<div class='cards w4'>"
        + _card("eye", "Automatic monitoring",
                "One source channel, checked on a schedule. Anything new is queued "
                "without you touching it.")
        + _card("clock-countdown", "Schedule and pacing",
                "Immediately, by interval, or at fixed times of day, with queued "
                "videos spread out instead of dumped at once.")
        + _card("image-square", "Overlay watermark",
                "Your image or animated GIF over every video, previewed before "
                "anything is published.")
        + _card("stack", "Backfill",
                "Queue a channel's archive and publish it oldest-to-newest across "
                "days.")
        + _card("folders", "Folders",
                "Group, rename, pause and resume connections as their number grows.")
        + _card("text-aa", "AI titles",
                "Generate a title and description per video instead of copying the "
                "original text.")
        + _card("bell-ringing", "Notifications",
                "Telegram messages on every publication, every failure, and before "
                "your access expires.")
        + _card("shield-check", "Encrypted tokens",
                "OAuth refresh tokens are stored encrypted, and you can revoke them "
                "from your platform account at any time.")
        + "</div>"

        "<h2>Automatic monitoring</h2>"
        "<div class='split'><div>"
        "<p>You point the bot at a source channel once. It checks that channel for "
        "new uploads on a schedule and queues anything new. YouTube sources are "
        "watched through the channel's public RSS feed, so monitoring itself does not "
        "consume any API quota.</p></div>"
        + _shot("source", "Adding a source channel in the bot")
        + "</div>"

        "<h2>Publishing to your accounts</h2>"
        "<h3>YouTube</h3>"
        "<p>Uploads go through the official YouTube Data API v3 using the OAuth "
        "authorization you grant. Each connection has its own visibility setting: "
        "public, unlisted or private. Daily upload volume respects the API quota "
        "assigned to your project.</p>"
        "<h3>TikTok</h3>"
        "<p>Uploads go through the official TikTok Content Posting API. By default a "
        "video is delivered to your TikTok <b>drafts (inbox)</b>, so you always review "
        "and confirm the post yourself inside the TikTok app before it goes live.</p>"

        "<h2>Flexible scheduling</h2>"
        "<ul>"
        "<li><b>Immediately.</b> Publish as soon as a new video is picked up.</li>"
        "<li><b>Fixed interval.</b> For example one video every 6 hours.</li>"
        "<li><b>Times of day.</b> For example 10:00, 15:00 and 21:00 in your "
        "timezone.</li>"
        "<li><b>Pacing.</b> Queued videos are spread evenly instead of being dumped "
        "all at once, which keeps your channel looking natural.</li>"
        "</ul>"

        "<h2>Overlay (watermark)</h2>"
        "<p>Place your own image or animated GIF over every published video. You pick "
        "the corner, size and margin, and the bot renders a preview frame so you can "
        "see the result before anything is published.</p>"

        "<h2>Backfill an archive</h2>"
        "<p>Beyond new uploads, you can queue a source channel's existing videos and "
        "re-publish them oldest-to-newest, spread across days according to your plan's "
        "daily limit.</p>"

        "<h2>Folders and management</h2>"
        "<div class='split'>"
        + _shot("connections", "Connections grouped into folders")
        + "<div><p>Group your connections into folders, rename them, pause or resume "
        "any connection, and open a connection's card to see its source, target "
        "channel, schedule and queue. Removing a connection deletes its data.</p></div>"
        "</div>"

        "<h2>AI titles and descriptions</h2>"
        "<p>Optionally let the bot generate a title and description for each "
        "re-published video instead of copying the original text.</p>"

        "<h2>Notifications</h2>"
        "<p>The bot messages you in Telegram when a video is published, when a "
        "download or upload fails, and before your access expires.</p>"

        "<h2>Security</h2>"
        "<p>OAuth refresh tokens are stored encrypted. The bot never asks for your "
        "platform password: authorization always happens on YouTube's or TikTok's "
        "own sign-in page, and you can revoke it at any time.</p>"

        + _band(
            "See the features on your own channel",
            "The free trial covers the whole list, so you can test the parts that "
            "matter to you before choosing a plan.",
            "Try it in Telegram",
        )
    )
    return _page(f"{app} · Features", f"{app} Features", body, "/features")


async def how_it_works(_: web.Request) -> web.Response:
    app = _app()
    body = (
        f"<p class='lead'>A full walkthrough of setting up {app}, from opening the "
        "bot to your first automatic publication.</p>"

        "<h2>Step by step</h2>"
        "<ol class='steps'>"
        "<li><b>Open the bot in Telegram.</b> Start <a href='" + BOT_URL + "'>"
        "@Posttiq_bot</a> and press <i>Start</i>. New users get a free trial period, "
        "so you can set everything up before paying.</li>"
        "<li><b>Connect the account you publish to.</b> Choose YouTube or TikTok. The "
        "bot sends you an authorization link that opens the platform's own sign-in "
        "page. You approve the requested permissions there; the bot never sees your "
        "password. Only accounts you own or are authorized to manage may be connected.</li>"
        "<li><b>Add a source channel.</b> Paste a link or handle of the channel whose "
        "videos you want to mirror: a YouTube channel link or handle, or a TikTok "
        "profile link. The bot confirms it can read the channel.</li>"
        "<li><b>Configure the connection.</b> Pick the schedule (immediately, by "
        "interval, or at set times), YouTube visibility, an optional overlay "
        "watermark, and whether titles come from the original video or are generated "
        "for you.</li>"
        "<li><b>Optionally backfill.</b> If you want the channel's existing videos "
        "too, queue them: they are published oldest-to-newest, spread over days.</li>"
        "<li><b>Let it run.</b> The bot checks the source, downloads new videos, "
        "publishes them to your connected account on schedule, and notifies you in "
        "Telegram. Downloaded files are deleted after publishing.</li>"
        "</ol>"

        "<div class='gallery'>"
        "<img src='/asset/connect.jpg' alt='Connecting an account' "
        "width='1000' height='654' loading='lazy' decoding='async'>"
        "<img src='/asset/guide.jpg' alt='Built-in guide inside the bot' "
        "width='1000' height='654' loading='lazy' decoding='async'>"
        "<img src='/asset/more.jpg' alt='Connection settings' "
        "width='1000' height='654' loading='lazy' decoding='async'>"
        "</div>"

        "<h2>What happens to a single video</h2>"
        "<div class='cards w4'>"
        + _card("eye", "1. Detected",
                "A new video appears in the source channel and is added to the queue.")
        + _card("cloud-arrow-down", "2. Downloaded",
                "The file is downloaded to the service's server, only so it can be "
                "uploaded onward.")
        + _card("arrows-clockwise", "3. Published",
                "It is uploaded to your connected account through the platform's "
                "official API. For TikTok, into your drafts.")
        + _card("trash", "4. Cleaned up",
                "You get a Telegram notification and the downloaded file is removed "
                "from the server.")
        + "</div>"

        "<h2>Managing connections</h2>"
        "<p>Every connection can be paused, renamed, moved into a folder, or deleted. "
        "Pausing stops new publications but keeps your settings. Deleting removes the "
        "connection and its queued videos.</p>"

        "<h2>Disconnecting</h2>"
        "<p>You can stop the service at any time: remove the connection in the bot, "
        "and/or revoke access in your platform account settings "
        "(<i>Google Account → Security → Third-party access</i> for YouTube, "
        "<i>TikTok → Settings → Security → Manage app permissions</i> for TikTok). "
        "Revoking makes the stored token unusable immediately.</p>"

        + _band(
            "Walk through it yourself",
            "Setup takes a few minutes, and the trial starts as soon as you open the "
            "bot.",
        )
    )
    return _page(f"{app} · How it works", f"How {app} works", body, "/how-it-works")


_PLAN_ICONS = {0: "lightning", 1: "rocket-launch", 2: "crown-simple"}


async def pricing(_: web.Request) -> web.Response:
    """Тарифы — строятся из settings.plans, чтобы сайт не расходился с ботом."""
    app = _app()
    check = icon("check-circle", 17)
    star = icon("sparkle", 16)
    cards = ""
    for plan in get_settings().plans.values():
        hot = plan["priority"] == 1
        cards += (
            f"<div class='plan{' hot' if hot else ''}'>"
            f"<div class='name'>{icon(_PLAN_ICONS.get(plan['priority'], 'lightning'), 19)}"
            f"{plan['name']}"
            + ("<span class='tag'>Most popular</span>" if hot else "")
            + "</div>"
            f"<div class='price'>{plan['month']['rub']} ₽ <span>/ 30 days</span></div>"
            f"<p class='alt'>or {plan['month']['stars']}{star} in Telegram Stars. "
            f"Lifetime access: {plan['forever']['rub']} ₽ / "
            f"{plan['forever']['stars']}{star}.</p>"
            "<ul>"
            f"<li>{check}<span>{fmt_limit(plan['accounts'])} connected channels</span></li>"
            f"<li>{check}<span>{fmt_limit(plan['videos'])} videos per day per "
            "connection</span></li>"
            f"<li>{check}<span>All features, nothing locked to a higher plan</span></li>"
            f"<li>{check}<span>YouTube and TikTok publishing</span></li>"
            f"<li>{check}<span>Support in the bot</span></li>"
            "</ul>"
            f"<a class='btn{'' if hot else ' ghost'}' href='{BOT_URL}'>"
            f"Choose {plan['name']}</a></div>"
        )
    body = (
        f"<p class='lead'>Every new user starts with a free trial. After that, {app} "
        "runs on a subscription. All plans include the full feature set and differ "
        "only in how many channels and videos per day you can process.</p>"

        f"<div class='plans'>{cards}</div>"
        "<p class='muted'>Prices are shown in Russian rubles (₽) and Telegram Stars "
        f"({star}). The exact amount and the available payment methods are displayed in the "
        "bot before you confirm any payment. ∞ means no fixed limit beyond the "
        "platform's own API limits.</p>"

        "<h2>Free trial</h2>"
        "<div class='split'><div>"
        "<p>You can connect an account, add a source and see real publications during "
        "the trial, before deciding on a plan. Invite a friend and you both get extra "
        "days when they first subscribe.</p>"
        "<p><a href='/how-it-works'>See what setup looks like →</a></p></div>"
        + _shot("tariffs", "Plan selection inside the bot")
        + "</div>"

        "<h2>Payment and billing</h2>"
        "<div class='cards w4'>"
        + _card("lock-key", "No card details in the bot",
                "Payments are handled by third-party payment providers and by Telegram "
                "Stars. Card data is never entered in the bot.")
        + _card("calendar-check", "Clear periods",
                "Monthly access lasts 30 days from purchase. Lifetime access is a "
                "one-off payment.")
        + _card("bell-ringing", "No silent renewals",
                "The bot warns you before your access expires and you choose whether "
                "to extend.")
        + _card("file-text", "Refunds",
                "Except where required by applicable law, payments are "
                "non-refundable. See the <a href='/terms'>Terms of Service</a>.")
        + "</div>"

        + _band(
            "Start on the free trial",
            "No payment needed to set everything up and watch the first video "
            "publish itself.",
            "Start free trial",
        )
    )
    return _page(f"{app} · Pricing", f"{app} Pricing", body, "/pricing")


def _qa(items: tuple[tuple[str, str], ...]) -> str:
    """Аккордеон FAQ на <details> — раскрывается без JS."""
    plus = icon("plus-circle", 20)
    return "<div class='faqlist'>" + "".join(
        f"<details><summary>{q}{plus}</summary><div class='a'><p>{a}</p></div></details>"
        for q, a in items
    ) + "</div>"


async def faq(_: web.Request) -> web.Response:
    app = _app()
    body = (
        f"<p class='lead'>Common questions about {app}. If yours is not here, ask us "
        "on the <a href='/support'>support page</a>.</p>"

        "<h2>Getting started</h2>"
        + _qa((
            ("Do I need to install anything?",
             f"No. {app} runs entirely inside Telegram: open the bot and follow the "
             "prompts."),
            ("Does the bot need my YouTube or TikTok password?",
             "Never. Authorization happens on the platform's own sign-in page through "
             "official OAuth. The bot only receives a token with the permissions you "
             "approve."),
            ("Which accounts may I connect?",
             "Only accounts you own or are authorized to manage, and you may only "
             "publish content you have the rights to publish. See the "
             "<a href='/terms'>Terms of Service</a>."),
        ))

        + "<h2>Publishing</h2>"
        + _qa((
            ("Where do TikTok videos appear?",
             "In your TikTok drafts (inbox) by default. You open the TikTok app, "
             "review the video, and post it yourself."),
            ("Can I choose when videos go out?",
             "Yes: immediately, on a fixed interval, or at specific times of day. "
             "Queued videos are also paced so they do not all publish at once."),
            ("How many videos per day?",
             "It depends on your plan and on the platform's own limits. YouTube's API "
             "quota allows roughly 6 uploads per day per Google project. See "
             "<a href='/pricing'>Pricing</a>."),
            ("Can I publish my channel's older videos?",
             "Yes, with backfill: the archive is queued and published oldest-to-newest "
             "over several days."),
            ("A publication failed. What now?",
             "The bot notifies you with the reason (quota exhausted, platform "
             "rejection, download error) and retries where retrying makes sense."),
        ))

        + "<h2>Data and privacy</h2>"
        + _qa((
            ("What data do you store?",
             "Your Telegram user ID, encrypted OAuth tokens for accounts you connect, "
             "identifiers of the connected accounts, your connection settings, and the "
             "queue of videos. Full detail is in the "
             "<a href='/privacy'>Privacy Policy</a>."),
            ("Are downloaded videos kept?",
             "No. A video file is downloaded only to publish it and is deleted from "
             "the server afterwards."),
            ("How do I revoke access?",
             "Remove the connection in the bot, and/or revoke the app in your Google "
             "or TikTok account settings. Either way the stored token can no longer "
             "be used."),
            ("How do I delete my data?",
             "Remove your connections in the bot, or ask us to delete everything. See "
             "the <a href='/support'>support page</a>."),
            ("Do you sell data or use it for ads?",
             "No. Platform data is used only to perform the publishing you configure."),
        ))

        + "<h2>Billing</h2>"
        + _qa((
            ("Is there a free trial?", "Yes, every new user gets one."),
            ("How do I pay?",
             "Through the payment methods offered in the bot, including Telegram "
             "Stars. Card details are never entered in the bot."),
            ("Can I get a refund?",
             "Except where required by applicable law, payments are non-refundable. If "
             "something on our side went wrong, contact support and we will sort it "
             "out."),
        ))

        + _band(
            "Still have a question?",
            "Support runs inside the bot, where your account and connections live, so "
            "answers come fastest there.",
            "Ask in the bot",
        )
    )
    return _page(f"{app} · FAQ", f"{app} FAQ", body, "/faq")


async def support(_: web.Request) -> web.Response:
    app = _app()
    body = (
        f"<p class='lead'>Support for {app} runs through the Telegram bot: that is "
        "where your account and connections live, so we can help fastest there.</p>"

        "<h2>Contact us</h2>"
        "<div class='cards'>"
        + _card("telegram-logo", "In the bot",
                f"Open <a href='{BOT_URL}'>@Posttiq_bot</a> and use the "
                "<b>Support</b> section. Messages reach us directly and we answer in "
                "the same chat.")
        + _card("envelope-simple", "Direct contact", _contact_sentence())
        + _card("globe", "Languages", "Russian and English.")
        + "</div>"

        "<h2>Before you write</h2>"
        "<div class='split'><div>"
        "<p>Many questions are already answered in the <a href='/faq'>FAQ</a> and the "
        "<a href='/how-it-works'>How it works</a> walkthrough. If you are reporting a "
        "problem, it helps to include:</p>"
        "<ul>"
        "<li>which platform the connection publishes to (YouTube or TikTok);</li>"
        "<li>the source channel and the connection name;</li>"
        "<li>what you expected and what happened instead, with the error text the bot "
        "showed you.</li>"
        "</ul></div>"
        + _shot("support", "The support section inside the bot")
        + "</div>"

        "<h2>Account and data requests</h2>"
        "<div class='cards'>"
        + _card("trash", "Delete your data",
                "You can act yourself at any time: remove a connection in the bot to "
                "delete its data. To request deletion of <b>all</b> data associated "
                f"with your account, message us ({_contact_sentence()}) with the "
                "request. We process it and confirm when it is done. Details are in "
                "the <a href='/privacy'>Privacy Policy</a>.")
        + _card("key", "Revoke authorization",
                "Revoke the app in your Google or TikTok account settings. The stored "
                "token becomes unusable immediately, even before we delete it.")
        + _card("flag", "Report abuse",
                "If you believe someone is using the service to publish content they "
                "have no rights to, or otherwise breaks the "
                f"<a href='/terms'>Terms of Service</a>, report it to us "
                f"({_contact_sentence()}). We investigate and, where warranted, "
                "suspend the account.")
        + "</div>"

        + _band(
            "We answer in the bot",
            "Open the Support section and describe what happened. Include the "
            "connection name and the error text if you have one.",
            "Message support",
        )
    )
    return _page(f"{app} · Support", f"{app} Support", body, "/support")


async def terms(_: web.Request) -> web.Response:
    app = _app()
    body = (
        "<p class='muted'>Last updated: 31 July 2026</p>"

        "<h2>1. Acceptance of these Terms</h2>"
        f"<p>These Terms of Service (“Terms”) govern your use of {app} (the "
        "“Service”), operated via the Telegram bot @Posttiq_bot and this website. "
        "By connecting an account or using the Service, you agree to these Terms. "
        "If you do not agree, do not use the Service.</p>"

        "<h2>2. Description of the Service</h2>"
        f"<p>{app} lets you connect your own social media accounts (YouTube and "
        "TikTok) and automatically re-publish videos from a source channel to your "
        "connected accounts, according to the schedule and settings you configure. "
        "The Service acts only on your behalf and only for the accounts you connect.</p>"

        "<h2>3. Eligibility and accounts</h2>"
        "<ul>"
        "<li>You must be old enough to hold accounts on the connected platforms and "
        "to enter into these Terms in your jurisdiction.</li>"
        "<li>You may connect only accounts that you own or are authorized to manage.</li>"
        "<li>You are responsible for all activity performed through your connections.</li>"
        "</ul>"

        "<h2>4. Content and acceptable use</h2>"
        "<ul>"
        "<li>You may only publish content that you own or have the necessary rights "
        "and permissions to publish.</li>"
        "<li>You must comply with the terms, policies and community guidelines of "
        "every connected platform (including YouTube and TikTok).</li>"
        "<li>You must not use the Service to publish illegal, infringing, harmful, "
        "misleading or otherwise prohibited content, or to spam.</li>"
        "<li>You are solely responsible for the content you publish and for any "
        "consequences of publishing it.</li>"
        "</ul>"

        "<h2>5. Authorization (OAuth)</h2>"
        "<p>The Service accesses your connected accounts only through the official "
        "OAuth authorization you explicitly grant, and only to perform the publishing "
        "you configure. You can revoke access at any time from the respective "
        "platform’s settings or by removing the connection in the bot.</p>"

        "<h2>6. Subscriptions and payments</h2>"
        "<p>The Service offers a free trial followed by paid subscription plans. "
        "Prices and limits are shown in the bot and on the "
        "<a href='/pricing'>Pricing</a> page. Payments are processed by third-party "
        "payment providers. Except where required by applicable law, payments are "
        "non-refundable.</p>"

        "<h2>7. Intellectual property</h2>"
        "<p>You retain all rights to your content. You grant the Service only the "
        "limited technical rights needed to download and re-publish your content to "
        f"the accounts you connect. The {app} name, website and software remain "
        "the property of their owner.</p>"

        "<h2>8. Disclaimers</h2>"
        "<p>The Service is provided “as is” and “as available”, without warranties "
        "of any kind. We do not guarantee that publishing will always succeed or "
        "that connected platforms will not restrict, remove or reject content or "
        "accounts.</p>"

        "<h2>9. Limitation of liability</h2>"
        f"<p>To the maximum extent permitted by law, {app} and its operator are "
        "not liable for any indirect, incidental or consequential damages, or for "
        "any action taken by a connected platform on your account or content.</p>"

        "<h2>10. Termination</h2>"
        "<p>You may stop using the Service at any time by removing your connections "
        "and revoking access. We may suspend or terminate access for violations of "
        "these Terms or platform policies.</p>"

        "<h2>11. Changes to these Terms</h2>"
        "<p>We may update these Terms from time to time. Continued use of the "
        "Service after changes take effect constitutes acceptance of the updated "
        "Terms.</p>"

        "<h2>12. Contact</h2>"
        f"<p>Questions about these Terms: {_contact_sentence()}. See also the "
        "<a href='/support'>Support</a> page.</p>"
    )
    return _page(f"{app} Terms of Service", f"{app} Terms of Service", body, "/terms")


async def privacy(_: web.Request) -> web.Response:
    app = _app()
    body = (
        "<p class='muted'>Last updated: 31 July 2026</p>"

        f"<p>This Privacy Policy explains what information {app} (the “Service”) "
        "collects, how it is used, and your choices. By using the Service you agree "
        "to this policy.</p>"

        "<h2>1. Information we collect</h2>"
        "<ul>"
        "<li><b>Telegram account identifier:</b> your Telegram user ID, to identify "
        "you in the bot.</li>"
        "<li><b>OAuth tokens</b> for the social accounts you connect (YouTube, "
        "TikTok), stored <b>encrypted</b> and used only to publish content you "
        "configure.</li>"
        "<li><b>Connected account identifiers:</b> such as your channel ID or TikTok "
        "open_id and display name, to show which account is linked.</li>"
        "<li><b>Service configuration:</b> the source channels you choose to watch, "
        "connection settings, and the videos queued for re-publishing.</li>"
        "<li><b>Support messages:</b> messages you send to support, so we can help "
        "you.</li>"
        "<li><b>Payment records:</b> limited transaction data required to provide "
        "and confirm your subscription (handled by third-party payment providers).</li>"
        "</ul>"

        "<h2>2. How we use information</h2>"
        "<ul>"
        "<li>To provide the core service: watch your chosen source, download new "
        "videos, and publish them to the accounts you connect, per your settings.</li>"
        "<li>To authenticate to YouTube and TikTok on your behalf via official APIs.</li>"
        "<li>To operate subscriptions and respond to support requests.</li>"
        "</ul>"

        "<h2>3. Platform data (YouTube &amp; TikTok)</h2>"
        "<p>We access data from connected platforms only through their official APIs "
        "and only to perform the actions you configure (identifying your account and "
        "publishing your content). We do not use platform data for advertising, "
        "profiling or any purpose unrelated to the Service, and we comply with the "
        "respective platform developer policies.</p>"

        "<h2>4. How we share information</h2>"
        "<p>We <b>do not sell</b> your data. We share information only:</p>"
        "<ul>"
        "<li>with the platforms you connect (YouTube, TikTok), as needed to publish "
        "your content;</li>"
        "<li>with payment providers, to process subscription payments;</li>"
        "<li>where required by law.</li>"
        "</ul>"

        "<h2>5. Video files</h2>"
        "<p>To re-publish a video the Service downloads it to its server temporarily. "
        "The file is deleted after the publication completes; we do not build a "
        "long-term library of your videos.</p>"

        "<h2>6. Data retention and deletion</h2>"
        "<p>We keep your data only as long as needed to provide the Service. "
        "Removing a connection in the bot deletes that connection’s data. Revoking "
        "OAuth access on the platform invalidates the stored token. You can request "
        "deletion of all your data by contacting us. See the "
        "<a href='/support'>Support</a> page.</p>"

        "<h2>7. Security</h2>"
        "<p>OAuth refresh tokens are stored encrypted. We apply reasonable technical "
        "and organizational measures to protect your data. No method of transmission "
        "or storage is 100% secure.</p>"

        "<h2>8. Children</h2>"
        "<p>The Service is not directed to children and should not be used by anyone "
        "below the minimum age required to hold accounts on the connected platforms.</p>"

        "<h2>9. Your rights</h2>"
        "<p>You may access, correct or delete your data, and withdraw access at any "
        "time by revoking OAuth or removing your connections. Contact us for any "
        "data request.</p>"

        "<h2>10. Changes to this policy</h2>"
        "<p>We may update this Privacy Policy from time to time. The “Last updated” "
        "date reflects the latest revision.</p>"

        "<h2>11. Contact</h2>"
        f"<p>Privacy questions or data requests: {_contact_sentence()}.</p>"
    )
    return _page(f"{app} Privacy Policy", f"{app} Privacy Policy", body, "/privacy")


async def tiktok_verify(request: web.Request) -> web.Response:
    code = request.match_info["code"]
    return web.Response(
        text=f"tiktok-developers-site-verification={code}",
        content_type="text/plain",
    )


def add_pages(app: web.Application) -> None:
    app.router.add_get("/", landing)
    app.router.add_get("/features", features)
    app.router.add_get("/how-it-works", how_it_works)
    app.router.add_get("/pricing", pricing)
    app.router.add_get("/faq", faq)
    app.router.add_get("/support", support)
    app.router.add_get("/terms", terms)
    app.router.add_get("/privacy", privacy)
    app.router.add_get("/logo", logo)
    app.router.add_get("/asset/{name}", asset)
    app.router.add_get(r"/tiktok{code}.txt", tiktok_verify)
