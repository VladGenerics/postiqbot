"""Публичный сайт PostiqBot: главная, Terms of Service, Privacy Policy."""
from __future__ import annotations

import os

from aiohttp import web

from bot.config import get_settings

_LOGO_PNG = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")

APP_NAME = "PostiqBot"
BOT_URL = "https://t.me/Posttiq_bot"

LOGO_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' role='img' aria-label='PostiqBot'>"
    "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
    "<stop offset='0' stop-color='#a855f7'/><stop offset='1' stop-color='#6d28d9'/></linearGradient></defs>"
    "<rect x='3' y='3' width='58' height='58' rx='15' fill='#0d0a17' stroke='url(#g)' stroke-width='3'/>"
    "<rect x='30' y='9' width='4' height='9' rx='2' fill='url(#g)'/><circle cx='32' cy='9' r='3.2' fill='url(#g)'/>"
    "<rect x='17' y='19' width='30' height='24' rx='10' fill='url(#g)'/>"
    "<rect x='24' y='27' width='4.5' height='9' rx='2.2' fill='#fff'/>"
    "<rect x='35.5' y='27' width='4.5' height='9' rx='2.2' fill='#fff'/>"
    "<rect x='22' y='46' width='20' height='10' rx='5' fill='url(#g)'/></svg>"
)

_CSS = """
:root{--bg:#0b0713;--card:#140d22;--line:#2a1f3d;--text:#eae6f2;--muted:#a99fc0;--acc:#a855f7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.65}
a{color:#c58cff;text-decoration:none}a:hover{text-decoration:underline}
header.site{display:flex;align-items:center;gap:12px;padding:16px 22px;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(11,7,19,.9);backdrop-filter:blur(6px)}
header.site .logo{width:34px;height:34px;border-radius:8px;object-fit:cover;vertical-align:middle}
header.site .brand{font-weight:800;font-size:19px;letter-spacing:.2px}
header.site nav{margin-left:auto;display:flex;gap:18px;font-size:15px}
main{max-width:860px;margin:0 auto;padding:34px 20px 10px}
h1{font-size:30px;margin:.2em 0 .6em;display:flex;align-items:center;gap:12px}
h1 .logo{width:32px;height:32px;flex:none;border-radius:8px;object-fit:cover}
h2{font-size:21px;margin:1.7em 0 .5em;border-bottom:1px solid var(--line);padding-bottom:.3em}
h3{font-size:17px;margin:1.2em 0 .3em}
p,li{color:var(--text)}small,.muted{color:var(--muted)}
.hero{padding:16px 0 6px}.hero p{font-size:18px;color:var(--muted);max-width:640px}
.btn{display:inline-block;background:linear-gradient(135deg,#a855f7,#6d28d9);color:#fff;font-weight:700;padding:12px 20px;border-radius:12px;margin:14px 8px 4px 0}
.btn.sec{background:transparent;border:1px solid var(--acc);color:#c58cff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}
.card h3{margin:.1em 0 .3em}.card p{color:var(--muted);margin:.2em 0 0;font-size:15px}
ol.steps{padding-left:0;list-style:none;counter-reset:s}
ol.steps li{counter-increment:s;position:relative;padding:10px 0 10px 44px;border-bottom:1px solid var(--line)}
ol.steps li::before{content:counter(s);position:absolute;left:0;top:8px;width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#a855f7,#6d28d9);color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center}
footer{max-width:860px;margin:30px auto;padding:20px;border-top:1px solid var(--line);color:var(--muted);font-size:14px}
"""


def _page(title: str, h1: str, body: str) -> web.Response:
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<link rel='icon' href='/logo'>"
        f"<meta name='description' content='{APP_NAME} — automate cross-posting your videos "
        "between your YouTube and TikTok accounts.'>"
        f"<title>{title}</title><style>{_CSS}</style></head><body>"
        "<header class='site'>"
        f"<img class='logo' src='/logo' alt='{APP_NAME}'><span class='brand'>{APP_NAME}</span>"
        "<nav><a href='/'>Home</a><a href='/terms'>Terms of Service</a>"
        "<a href='/privacy'>Privacy Policy</a></nav></header>"
        f"<main><h1><img class='logo' src='/logo' alt='{APP_NAME}'>{h1}</h1>{body}</main>"
        f"<footer>© 2026 {APP_NAME}. All rights reserved. · "
        "<a href='/terms'>Terms of Service</a> · <a href='/privacy'>Privacy Policy</a> · "
        f"<a href='{BOT_URL}'>Telegram bot</a></footer></body></html>"
    )
    return web.Response(text=html, content_type="text/html")


async def logo(_: web.Request) -> web.Response:
    """Иконка приложения: PNG-робот из assets, иначе SVG-запас."""
    if os.path.exists(_LOGO_PNG):
        return web.FileResponse(_LOGO_PNG)
    return web.Response(text=LOGO_SVG, content_type="image/svg+xml")


async def landing(_: web.Request) -> web.Response:
    body = (
        "<section class='hero'>"
        "<p>PostiqBot automatically cross-posts your videos between your own "
        "YouTube and TikTok accounts. Connect your channels once, add a source, "
        "and every new video is re-published for you on schedule — no manual "
        "re-uploading.</p>"
        f"<a class='btn' href='{BOT_URL}'>Open in Telegram</a>"
        "<a class='btn sec' href='#how'>How it works</a>"
        "</section>"

        "<h2>What PostiqBot does</h2>"
        "<div class='grid'>"
        "<div class='card'><h3>🔗 Connect your accounts</h3><p>Link your own YouTube "
        "and TikTok accounts through official OAuth. You stay in control and can "
        "revoke access anytime.</p></div>"
        "<div class='card'><h3>📡 Add a source</h3><p>Choose a channel to watch. When "
        "a new video appears, PostiqBot picks it up automatically.</p></div>"
        "<div class='card'><h3>⏰ Schedule</h3><p>Publish immediately, at a fixed "
        "interval, or at set times of day — spread your posts evenly.</p></div>"
        "<div class='card'><h3>🖼 Overlay</h3><p>Add an image or GIF watermark over "
        "every video, with a live preview of position and size.</p></div>"
        "<div class='card'><h3>👁 Visibility</h3><p>For YouTube, choose public, "
        "unlisted or private for each connection.</p></div>"
        "<div class='card'><h3>📥 Backfill</h3><p>Optionally queue a channel's past "
        "videos to re-publish them oldest-to-newest.</p></div>"
        "</div>"

        "<h2 id='how'>How it works</h2>"
        "<ol class='steps'>"
        "<li><b>Connect your channel.</b> Sign in to your YouTube or TikTok account "
        "via official OAuth. This is where PostiqBot will publish.</li>"
        "<li><b>Add a source.</b> Paste a link to the channel you want to mirror "
        "(YouTube handle/link or a TikTok profile link).</li>"
        "<li><b>Configure &amp; relax.</b> Set the schedule, optional overlay and "
        "visibility. New videos are downloaded and published for you automatically.</li>"
        "</ol>"

        "<h2>Supported platforms</h2>"
        "<p><b>YouTube</b> — publishing via the official YouTube Data API. "
        "<b>TikTok</b> — publishing via the official TikTok Content Posting API "
        "(videos are delivered to your TikTok drafts for you to review and post).</p>"

        "<h2>Access &amp; pricing</h2>"
        "<p>New users get a free trial. Continued access is available via a "
        "subscription. Manage everything from the Telegram bot.</p>"

        "<h2>Contact</h2>"
        f"<p>PostiqBot is operated as a Telegram service. Reach us through the bot: "
        f"<a href='{BOT_URL}'>@Posttiq_bot</a> (the “Support” section). "
        + (f"You can also contact us at {get_settings().support_contact}." if get_settings().support_contact else "")
        + "</p>"

        "<p style='margin-top:22px'>"
        f"<a class='btn' href='{BOT_URL}'>Get started</a></p>"
    )
    return _page(APP_NAME, f"{APP_NAME} — automated video cross-posting", body)


async def terms(_: web.Request) -> web.Response:
    body = (
        "<p class='muted'>Last updated: 8 July 2026</p>"

        "<h2>1. Acceptance of these Terms</h2>"
        "<p>These Terms of Service (“Terms”) govern your use of PostiqBot (the "
        "“Service”), operated via the Telegram bot @Posttiq_bot and this website. "
        "By connecting an account or using the Service, you agree to these Terms. "
        "If you do not agree, do not use the Service.</p>"

        "<h2>2. Description of the Service</h2>"
        "<p>PostiqBot lets you connect your own social media accounts (YouTube and "
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
        "Prices and limits are shown in the bot. Payments are processed by "
        "third-party payment providers. Except where required by applicable law, "
        "payments are non-refundable.</p>"

        "<h2>7. Intellectual property</h2>"
        "<p>You retain all rights to your content. You grant the Service only the "
        "limited technical rights needed to download and re-publish your content to "
        "the accounts you connect. The PostiqBot name, website and software remain "
        "the property of their owner.</p>"

        "<h2>8. Disclaimers</h2>"
        "<p>The Service is provided “as is” and “as available”, without warranties "
        "of any kind. We do not guarantee that publishing will always succeed or "
        "that connected platforms will not restrict, remove or reject content or "
        "accounts.</p>"

        "<h2>9. Limitation of liability</h2>"
        "<p>To the maximum extent permitted by law, PostiqBot and its operator are "
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
        f"<p>Questions about these Terms: <a href='{BOT_URL}'>@Posttiq_bot</a>"
        + (f", or {get_settings().support_contact}" if get_settings().support_contact else "")
        + ".</p>"
    )
    return _page(f"{APP_NAME} Terms of Service", f"{APP_NAME} Terms of Service", body)


async def privacy(_: web.Request) -> web.Response:
    body = (
        "<p class='muted'>Last updated: 8 July 2026</p>"

        "<p>This Privacy Policy explains what information PostiqBot (the “Service”) "
        "collects, how it is used, and your choices. By using the Service you agree "
        "to this policy.</p>"

        "<h2>1. Information we collect</h2>"
        "<ul>"
        "<li><b>Telegram account identifier</b> — your Telegram user ID, to identify "
        "you in the bot.</li>"
        "<li><b>OAuth tokens</b> for the social accounts you connect (YouTube, "
        "TikTok) — stored <b>encrypted</b> and used only to publish content you "
        "configure.</li>"
        "<li><b>Connected account identifiers</b> — such as your channel ID / TikTok "
        "open_id and display name, to show which account is linked.</li>"
        "<li><b>Service configuration</b> — the source channels you choose to watch, "
        "connection settings, and the videos queued for re-publishing.</li>"
        "<li><b>Support messages</b> — messages you send to support, so we can help "
        "you.</li>"
        "<li><b>Payment records</b> — limited transaction data required to provide "
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

        "<h2>5. Data retention and deletion</h2>"
        "<p>We keep your data only as long as needed to provide the Service. "
        "Removing a connection in the bot deletes that connection’s data. Revoking "
        "OAuth access on the platform invalidates the stored token. You can request "
        "deletion of all your data by contacting us (see below).</p>"

        "<h2>6. Security</h2>"
        "<p>OAuth refresh tokens are stored encrypted. We apply reasonable technical "
        "and organizational measures to protect your data. No method of transmission "
        "or storage is 100% secure.</p>"

        "<h2>7. Children</h2>"
        "<p>The Service is not directed to children and should not be used by anyone "
        "below the minimum age required to hold accounts on the connected platforms.</p>"

        "<h2>8. Your rights</h2>"
        "<p>You may access, correct or delete your data, and withdraw access at any "
        "time by revoking OAuth or removing your connections. Contact us for any "
        "data request.</p>"

        "<h2>9. Changes to this policy</h2>"
        "<p>We may update this Privacy Policy from time to time. The “Last updated” "
        "date reflects the latest revision.</p>"

        "<h2>10. Contact</h2>"
        f"<p>Privacy questions or data requests: <a href='{BOT_URL}'>@Posttiq_bot</a>"
        + (f", or {get_settings().support_contact}" if get_settings().support_contact else "")
        + ".</p>"
    )
    return _page(f"{APP_NAME} Privacy Policy", f"{APP_NAME} Privacy Policy", body)


async def tiktok_verify(request: web.Request) -> web.Response:
    code = request.match_info["code"]
    return web.Response(
        text=f"tiktok-developers-site-verification={code}",
        content_type="text/plain",
    )


def add_pages(app: web.Application) -> None:
    app.router.add_get("/", landing)
    app.router.add_get("/terms", terms)
    app.router.add_get("/privacy", privacy)
    app.router.add_get("/logo", logo)
    app.router.add_get(r"/tiktok{code}.txt", tiktok_verify)
