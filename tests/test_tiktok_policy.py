"""Правила Direct Post: где нужно согласие пользователя и где запрещён оверлей."""
from __future__ import annotations

import pytest

from bot.config import get_settings
from bot.services.tiktok_policy import is_direct_post, overlay_allowed


def _direct_post_flag(monkeypatch, enabled: bool) -> None:
    monkeypatch.setenv("TIKTOK_DIRECT_POST", "true" if enabled else "false")
    get_settings.cache_clear()


PAIRS = [
    (("tiktok", "tiktok"), True),
    (("tiktok", "youtube"), False),
    (("youtube", "tiktok"), False),
    (("youtube", "youtube"), False),
    ((None, None), False),
    (("tiktok", None), False),
    ((None, "tiktok"), False),
]


@pytest.mark.parametrize("pair,expected", PAIRS)
def test_only_tiktok_to_tiktok_is_direct_post(monkeypatch, pair, expected):
    _direct_post_flag(monkeypatch, True)
    assert is_direct_post(*pair) is expected


@pytest.mark.parametrize("pair,_expected", PAIRS)
def test_flag_off_means_drafts_everywhere(monkeypatch, pair, _expected):
    """Пока scope video.publish не одобрен, TIKTOK_DIRECT_POST=false должен выключать прямую публикацию целиком."""
    _direct_post_flag(monkeypatch, False)
    assert is_direct_post(*pair) is False


@pytest.mark.parametrize("pair,expected", PAIRS)
def test_overlay_is_forbidden_exactly_for_direct_post(monkeypatch, pair, expected):
    _direct_post_flag(monkeypatch, True)
    assert overlay_allowed(*pair) is (not expected)


def test_overlay_allowed_for_drafts_when_flag_off(monkeypatch):
    _direct_post_flag(monkeypatch, False)
    assert overlay_allowed("tiktok", "tiktok") is True
