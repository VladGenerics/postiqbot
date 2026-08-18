"""Правила Direct Post: где нужно согласие пользователя и где запрещён оверлей."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from bot.config import get_settings
from bot.services.tiktok_policy import (
    effective_toggles,
    is_auto_post,
    is_direct_post,
    needs_confirm_card,
    overlay_allowed,
)

CONSENT = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def _flags(monkeypatch, *, direct: bool, any_source: bool = True) -> None:
    monkeypatch.setenv("TIKTOK_DIRECT_POST", "true" if direct else "false")
    monkeypatch.setenv("TIKTOK_DIRECT_ANY_SOURCE", "true" if any_source else "false")
    get_settings.cache_clear()


PAIRS = [
    (("tiktok", "tiktok"), True),
    (("tiktok", "youtube"), True),
    (("youtube", "tiktok"), False),
    (("youtube", "youtube"), False),
    ((None, None), False),
    (("tiktok", None), True),
    ((None, "tiktok"), False),
]


@pytest.mark.parametrize("pair,expected", PAIRS)
def test_direct_post_only_when_destination_is_tiktok(monkeypatch, pair, expected):
    _flags(monkeypatch, direct=True)
    assert is_direct_post(*pair) is expected


@pytest.mark.parametrize("pair,_expected", PAIRS)
def test_flag_off_means_drafts_everywhere(monkeypatch, pair, _expected):
    """TIKTOK_DIRECT_POST=false выключает прямую публикацию целиком — без исключений."""
    _flags(monkeypatch, direct=False)
    assert is_direct_post(*pair) is False


def test_any_source_flag_returns_youtube_sources_to_drafts(monkeypatch):
    """Рубильник на случай претензий TikTok к копированию с других платформ: TikTok → TikTok продолжает работать."""
    _flags(monkeypatch, direct=True, any_source=False)
    assert is_direct_post("tiktok", "tiktok") is True
    assert is_direct_post("tiktok", "youtube") is False


@pytest.mark.parametrize("pair,expected", PAIRS)
def test_overlay_is_forbidden_exactly_for_direct_post(monkeypatch, pair, expected):
    _flags(monkeypatch, direct=True)
    assert overlay_allowed(*pair) is (not expected)


def test_overlay_allowed_for_drafts_when_flag_off(monkeypatch):
    _flags(monkeypatch, direct=False)
    assert overlay_allowed("tiktok", "tiktok") is True


def test_auto_post_requires_privacy_and_consent(monkeypatch):
    _flags(monkeypatch, direct=True)
    full = dict(tt_auto=True, tt_privacy="PUBLIC_TO_EVERYONE", tt_consent_at=CONSENT)
    assert is_auto_post("tiktok", "tiktok", **full) is True
    assert is_auto_post("tiktok", "tiktok", **{**full, "tt_privacy": None}) is False
    assert is_auto_post("tiktok", "tiktok", **{**full, "tt_consent_at": None}) is False
    assert is_auto_post("tiktok", "tiktok", **{**full, "tt_auto": False}) is False


def test_auto_post_impossible_without_direct_post(monkeypatch):
    """Без Direct Post «авто» бессмысленно: в черновики публикует сам пользователь из приложения."""
    _flags(monkeypatch, direct=False)
    assert is_auto_post(
        "tiktok", "tiktok",
        tt_auto=True, tt_privacy="PUBLIC_TO_EVERYONE", tt_consent_at=CONSENT,
    ) is False


def test_card_needed_for_direct_post_until_auto_configured(monkeypatch):
    _flags(monkeypatch, direct=True)
    unset = dict(tt_auto=False, tt_privacy=None, tt_consent_at=None)
    assert needs_confirm_card("tiktok", "tiktok", **unset) is True
    assert needs_confirm_card(
        "tiktok", "tiktok",
        tt_auto=True, tt_privacy="SELF_ONLY", tt_consent_at=CONSENT,
    ) is False
    assert needs_confirm_card("tiktok", "youtube", **unset) is True
    _flags(monkeypatch, direct=True, any_source=False)
    assert needs_confirm_card("tiktok", "youtube", **unset) is False


def test_card_never_needed_for_youtube_destination(monkeypatch):
    _flags(monkeypatch, direct=True)
    assert needs_confirm_card(
        "youtube", "youtube", tt_auto=False, tt_privacy=None, tt_consent_at=None
    ) is False


def test_creator_disabled_interactions_win():
    saved = dict(
        tt_disable_comment=False, tt_disable_duet=False, tt_disable_stitch=False
    )
    info = {"comment_disabled": True, "duet_disabled": False, "stitch_disabled": True}
    assert effective_toggles(info, **saved) == {
        "tt_disable_comment": True,
        "tt_disable_duet": False,
        "tt_disable_stitch": True,
    }


def test_effective_toggles_keeps_unrelated_flags():
    """Раскрытие рекламы creator_info не ограничивает — оно должно пройти как есть."""
    out = effective_toggles(
        {"comment_disabled": True},
        tt_disable_comment=False,
        tt_brand_content=True,
    )
    assert out == {"tt_disable_comment": True, "tt_brand_content": True}
