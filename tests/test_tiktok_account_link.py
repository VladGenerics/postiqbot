"""Ник получателя — рабочая ссылка на профиль TikTok."""
from __future__ import annotations

import types

from bot.handlers import tiktok_confirm as tc
from bot.handlers import tiktok_settings as ts
from bot.services import tiktok_api

INFO = {
    "creator_nickname": "Кино и сериалы",
    "creator_username": "kino_serial.1",
    "privacy_level_options": ["PUBLIC_TO_EVERYONE", "SELF_ONLY"],
}

PROFILE = "https://www.tiktok.com/@kino_serial.1"


def _job(**over):
    fields = dict(
        id=42,
        connection_id=7,
        title="Видео",
        tt_privacy=None,
        tt_disable_comment=True,
        tt_disable_duet=True,
        tt_disable_stitch=True,
        tt_brand_organic=False,
        tt_brand_content=False,
    )
    fields.update(over)
    return types.SimpleNamespace(**fields)


def _conn(**over):
    fields = dict(
        id=7,
        tt_auto=False,
        tt_privacy=None,
        tt_disable_comment=True,
        tt_disable_duet=True,
        tt_disable_stitch=True,
        tt_brand_organic=False,
        tt_brand_content=False,
        tt_consent_at=None,
        overlay_file_id=None,
        overlay_position=None,
        publish_account=types.SimpleNamespace(platform="tiktok"),
        source_channel=types.SimpleNamespace(platform="youtube"),
    )
    fields.update(over)
    return types.SimpleNamespace(**fields)


def test_profile_url_is_built_from_username():
    assert tiktok_api.profile_url(INFO) == PROFILE


def test_profile_url_tolerates_at_sign_and_spaces():
    """@ и пробелы приходят из разных версий ответа TikTok; адрес один и тот же."""
    assert tiktok_api.profile_url({"creator_username": " @kino_serial.1 "}) == PROFILE


def test_profile_url_is_none_without_username():
    """Урезанный creator_info — не повод падать: ник останется просто текстом."""
    assert tiktok_api.profile_url({}) is None
    assert tiktok_api.profile_url({"creator_username": ""}) is None
    assert tiktok_api.profile_url({"creator_nickname": "tester"}) is None


def test_profile_url_escapes_unexpected_characters():
    """Username идёт из внешнего ответа прямо в href — пробел или кавычка не должны разорвать HTML-атрибут."""
    url = tiktok_api.profile_url({"creator_username": 'a b"c'})
    assert url is not None
    assert " " not in url and '"' not in url


def test_card_account_is_a_link():
    text = tc._card_text(_job(), INFO, "ru")
    assert f'<a href="{PROFILE}">Кино и сериалы</a>' in text


def test_card_renders_without_username():
    """Без адреса ник остаётся текстом."""
    text = tc._card_text(_job(), {"creator_nickname": "tester"}, "ru")
    assert "<b>tester</b>" in text and "tiktok.com/@" not in text


def test_card_escapes_nickname_inside_the_link():
    """Ник приходит из TikTok: разметка внутри него ломала бы parse_mode=HTML."""
    text = tc._card_text(_job(), dict(INFO, creator_nickname="<b>x</b>"), "ru")
    assert "&lt;b&gt;x&lt;/b&gt;" in text
    assert "<b>x</b>" not in text


def test_settings_account_is_a_link():
    text = ts._screen_text(_conn(), INFO, "ru")
    assert f'<a href="{PROFILE}">Кино и сериалы</a>' in text


def test_settings_renders_without_username():
    text = ts._screen_text(_conn(), {"creator_nickname": "tester"}, "ru")
    assert "<b>tester</b>" in text and "tiktok.com/@" not in text


def test_link_preview_is_disabled_on_both_screens():
    """Иначе Telegram подтянет превью страницы TikTok: в карточке оно перекроет кадр видео."""
    assert tc._NO_PREVIEW.is_disabled is True
    assert ts._NO_PREVIEW.is_disabled is True
