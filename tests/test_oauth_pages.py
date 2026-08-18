"""Страницы результата OAuth и приглашения «Войти через …»."""
from __future__ import annotations

import asyncio
import html
import types

from aiohttp.test_utils import make_mocked_request

from bot.handlers import accounts, menu
from bot.services import login_prompts
from bot.web import tiktok_callback as tt
from bot.web.oauth_callback import oauth_callback
from bot.web.pages import result_page, web_lang

NASTY = '<script>alert(1)</script>'


def _get(path: str, lang: str = "ru") -> object:
    """Запрос как от браузера: Accept-Language определяет язык страницы."""
    return make_mocked_request(
        "GET", path, headers={"Accept-Language": lang}, app={"bot": None}
    )


def _body(response) -> str:
    return response.text


def test_success_page_carries_design_and_way_back():
    page = _body(result_page("TikTok подключён", "Готово.", platform="tiktok"))
    assert "class='result'" in page
    assert "--acc:#c93bf0" in page
    assert "https://t.me/Posttiq_bot" in page
    assert "<svg" in page


def test_error_page_is_marked_and_shows_reason():
    page = _body(result_page(
        "Ошибка подключения", "Не вышло.", ok=False, platform="youtube",
        detail="invalid_grant",
    ))
    assert "class='result bad'" in page
    assert "invalid_grant" in page


def test_page_title_has_app_name():
    """Ревью TikTok/Google требует имя приложения в <title> каждой страницы."""
    page = _body(result_page("TikTok подключён", "Готово.", platform="tiktok"))
    assert "<title>" in page and "PosttiqBot" in page.split("</title>")[0]


def test_result_page_does_not_double_escape_what_caller_escaped():
    """Вызывающий экранирует сам — страница не должна портить уже безопасный текст."""
    page = _body(result_page("ok", f"Аккаунт «{html.escape(NASTY)}»"))
    assert NASTY not in page
    assert "&lt;script&gt;" in page


def test_web_lang_follows_browser():
    assert web_lang(_get("/tiktok/callback", "ru-RU,ru;q=0.9")) == "ru"
    assert web_lang(_get("/tiktok/callback", "en-US,en;q=0.9")) == "en"
    assert web_lang(make_mocked_request("GET", "/tiktok/callback")) == "en"


def test_tiktok_denied_shows_page_and_escapes_description():
    """error_description приходит от TikTok — в HTML он должен быть обезврежен."""
    request = _get(f"/tiktok/callback?error=access_denied&error_description={NASTY}")
    response = asyncio.run(tt.tiktok_callback(request))
    assert response.status == 200
    page = _body(response)
    assert "Доступ не выдан" in page
    assert NASTY not in page and "&lt;script&gt;" in page


def test_tiktok_without_code_and_with_dead_state():
    no_code = asyncio.run(tt.tiktok_callback(_get("/tiktok/callback?state=x")))
    assert "Некорректный запрос" in _body(no_code)
    dead = asyncio.run(tt.tiktok_callback(_get("/tiktok/callback?code=c&state=broken")))
    assert "Ссылка устарела" in _body(dead)


def test_youtube_denied_and_bad_request_render_in_english():
    denied = asyncio.run(oauth_callback(_get("/oauth/callback?error=access_denied", "en")))
    assert "Access not granted" in _body(denied)
    bad = asyncio.run(oauth_callback(_get("/oauth/callback", "en")))
    assert "Invalid request" in _body(bad)


class _FakeBot:
    def __init__(self) -> None:
        self.deleted: list[tuple[int, int]] = []

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        self.deleted.append((chat_id, message_id))


def test_prompt_is_deleted_after_login():
    bot = _FakeBot()
    asyncio.run(login_prompts.remember(bot, 42, "tiktok", 100))
    asyncio.run(login_prompts.clear(bot, 42, "tiktok"))
    assert bot.deleted == [(42, 100)]
    asyncio.run(login_prompts.clear(bot, 42, "tiktok"))
    assert bot.deleted == [(42, 100)]


def test_new_prompt_replaces_the_previous_one():
    """Пользователь нажал «Войти» дважды — в чате должно остаться одно сообщение."""
    bot = _FakeBot()
    asyncio.run(login_prompts.remember(bot, 7, "youtube", 1))
    asyncio.run(login_prompts.remember(bot, 7, "youtube", 2))
    assert bot.deleted == [(7, 1)]
    asyncio.run(login_prompts.clear(bot, 7, "youtube"))
    assert bot.deleted == [(7, 1), (7, 2)]


def test_platforms_do_not_clear_each_other():
    """Вход в TikTok не должен убирать приглашение войти в YouTube."""
    bot = _FakeBot()
    asyncio.run(login_prompts.remember(bot, 5, "youtube", 10))
    asyncio.run(login_prompts.remember(bot, 5, "tiktok", 11))
    asyncio.run(login_prompts.clear(bot, 5, "tiktok"))
    assert bot.deleted == [(5, 11)]
    assert login_prompts.forget(5, "youtube") == 10


def test_failed_delete_does_not_break_the_flow():
    """Сообщение старше 48 ч или уже удалено — подключение важнее приглашения."""
    class _Broken(_FakeBot):
        async def delete_message(self, chat_id: int, message_id: int) -> None:
            raise RuntimeError("message can't be deleted")

    bot = _Broken()
    asyncio.run(login_prompts.remember(bot, 9, "tiktok", 3))
    asyncio.run(login_prompts.clear(bot, 9, "tiktok"))


class _FakeMessage:
    """Дублёр сообщения: приглашение уходит через message.answer."""

    def __init__(self, bot) -> None:
        self.bot = bot
        self.sent: list[tuple[str, object]] = []

    async def answer(self, text, reply_markup=None, **_):
        self.sent.append((text, reply_markup))
        return types.SimpleNamespace(message_id=555)


def test_new_connection_screen_leads_straight_to_sign_in():
    """Экран «Новое подключение» сам предлагает вход — промежуточного экрана нет."""
    for lang, word in (("ru", "Войти"), ("en", "Sign in")):
        _, caption, kb = asyncio.run(menu._build("newconn", 1, lang, None))
        buttons = [b for row in kb.inline_keyboard for b in row]
        data = [b.callback_data for b in buttons]
        assert "connect_youtube" in data and "connect_tiktok" in data
        assert "nav:addsrc" in data
        assert sum(word in b.text for b in buttons) == 2
        assert caption


def test_login_prompt_is_remembered_so_it_can_disappear():
    """Без записи в реестре сообщение с кнопкой входа останется в чате навсегда."""
    bot = _FakeBot()
    message = _FakeMessage(bot)
    asyncio.run(accounts._send_login_prompt(
        message, 42, "tiktok", "текст", "🔓 Войти через TikTok", "https://tiktok.test/auth"
    ))
    text, markup = message.sent[0]
    button = markup.inline_keyboard[0][0]
    assert text == "текст" and button.url == "https://tiktok.test/auth"
    assert login_prompts.forget(42, "tiktok") == 555
