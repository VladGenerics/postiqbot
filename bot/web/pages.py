"""Статические страницы: лендинг, Terms of Service, Privacy Policy."""
from __future__ import annotations

from aiohttp import web


def _page(title: str, body: str) -> web.Response:
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{title} — PostiqBot</title></head>"
        "<body style='font-family:sans-serif;max-width:720px;margin:48px auto;"
        "padding:0 16px;line-height:1.6;color:#222'>"
        f"<h1>{title}</h1>{body}"
        "<hr><p style='color:#888'>PostiqBot — automated cross-posting service.</p>"
        "</body></html>"
    )
    return web.Response(text=html, content_type="text/html")


async def landing(_: web.Request) -> web.Response:
    return _page(
        "PostiqBot",
        "<p>PostiqBot automatically reposts videos between a user's own connected "
        "social accounts (YouTube, TikTok) using official platform APIs.</p>"
        "<p>Access is managed via the Telegram bot. "
        "<a href='/terms'>Terms of Service</a> · "
        "<a href='/privacy'>Privacy Policy</a></p>",
    )


async def terms(_: web.Request) -> web.Response:
    return _page(
        "Terms of Service",
        "<p>PostiqBot lets a user connect their own social media accounts and "
        "automatically repost videos between them.</p>"
        "<h3>Use of the service</h3>"
        "<p>You may only connect accounts you own or are authorized to manage, and "
        "only repost content you have the rights to publish. You are responsible for "
        "compliance with the terms of each connected platform (YouTube, TikTok).</p>"
        "<h3>Authorization</h3>"
        "<p>The service acts on your behalf only through access you explicitly grant "
        "via official OAuth, and only for publishing content to accounts you connect. "
        "You can revoke access at any time from the respective platform.</p>"
        "<h3>Disclaimer</h3>"
        "<p>The service is provided “as is”, without warranty. We are not liable for "
        "any action taken by connected platforms on your accounts or content.</p>",
    )


async def privacy(_: web.Request) -> web.Response:
    return _page(
        "Privacy Policy",
        "<p>This policy explains what PostiqBot stores and why.</p>"
        "<h3>What we store</h3>"
        "<ul>"
        "<li>Your Telegram user ID (to identify your account in the bot).</li>"
        "<li>OAuth refresh tokens for the social accounts you connect — stored "
        "<b>encrypted</b> and used only to publish content you configure.</li>"
        "<li>The source channels you choose to monitor and the videos queued for "
        "reposting.</li>"
        "</ul>"
        "<h3>What we do NOT do</h3>"
        "<p>We do not sell your data, and we do not access your accounts for any "
        "purpose other than the reposting you configure.</p>"
        "<h3>Deletion</h3>"
        "<p>Removing a connection in the bot deletes its data. Revoking OAuth access "
        "on the platform invalidates the stored token. Contact the bot operator to "
        "delete all of your data.</p>",
    )


def add_pages(app: web.Application) -> None:
    app.router.add_get("/", landing)
    app.router.add_get("/terms", terms)
    app.router.add_get("/privacy", privacy)
