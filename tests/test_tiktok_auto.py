"""Авто-режим TikTok: экран настроек, scope и лестница повторов при лимитах."""
from __future__ import annotations

import types
from datetime import datetime, timedelta, timezone

import pytest

from bot.config import get_settings
from bot.handlers import tiktok_settings as ts
from bot.services import publisher
from bot.services.tiktok_oauth import get_scopes
from bot.services.tiktok_policy import POST_FIELDS

CONSENT = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)

MARK_CHOSEN = "🔘 "
MARK_FREE = "⚪ "
MARK_ON = "☑️"
MARK_OFF = "⬜️"
MARK_BLOCKED = "🚫"

INFO = {
    "creator_nickname": "tester",
    "creator_username": "tester_1",
    "privacy_level_options": ["PUBLIC_TO_EVERYONE", "SELF_ONLY"],
    "duet_disabled": True,
    "max_video_post_duration_sec": 600,
}


def _flags(monkeypatch, *, direct: bool, any_source: bool = True) -> None:
    monkeypatch.setenv("TIKTOK_DIRECT_POST", "true" if direct else "false")
    monkeypatch.setenv("TIKTOK_DIRECT_ANY_SOURCE", "true" if any_source else "false")
    get_settings.cache_clear()


def _conn(**over):
    """Дублёр Connection: у экрана настроек нет БД, только атрибуты связки."""
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


def _buttons(conn, lang="ru"):
    return [b for row in ts._screen_markup(conn, INFO, lang).inline_keyboard for b in row]


def test_auto_needs_flag_privacy_and_consent(monkeypatch):
    _flags(monkeypatch, direct=True)
    assert ts.auto_enabled(_conn()) is False
    assert ts.auto_enabled(_conn(tt_auto=True)) is False
    assert ts.auto_enabled(_conn(tt_auto=True, tt_privacy="SELF_ONLY")) is False
    full = _conn(tt_auto=True, tt_privacy="SELF_ONLY", tt_consent_at=CONSENT)
    assert ts.auto_enabled(full) is True


def test_settings_screen_only_for_direct_post_connections(monkeypatch):
    _flags(monkeypatch, direct=True)
    assert ts.tt_settings_available(_conn()) is True
    assert ts.tt_settings_available(
        _conn(publish_account=types.SimpleNamespace(platform="youtube"))
    ) is False
    _flags(monkeypatch, direct=False)
    assert ts.tt_settings_available(_conn()) is False


def test_auto_dies_with_the_flag(monkeypatch):
    """Аварийное выключение TIKTOK_DIRECT_POST должно остановить и авто-режим."""
    full = _conn(tt_auto=True, tt_privacy="PUBLIC_TO_EVERYONE", tt_consent_at=CONSENT)
    _flags(monkeypatch, direct=True)
    assert ts.auto_enabled(full) is True
    _flags(monkeypatch, direct=False)
    assert ts.auto_enabled(full) is False


def test_privacy_has_no_preselected_value(monkeypatch):
    """«No default value» из гайдлайнов: пока пользователь не выбрал уровень, ни одна кнопка не отмечена."""
    _flags(monkeypatch, direct=True)
    conn = _conn()
    marks = [b.text for b in _buttons(conn) if b.callback_data.startswith("ttsp:")]
    assert marks and all(m.startswith(MARK_FREE) for m in marks)
    assert "выбери" in ts._screen_text(conn, INFO, "ru")


def test_only_allowed_privacy_levels_are_offered(monkeypatch):
    """Уровень не из privacy_level_options вернул бы 403 privacy_level_option_mismatch."""
    _flags(monkeypatch, direct=True)
    offered = {
        b.callback_data.split(":")[2]
        for b in _buttons(_conn())
        if b.callback_data.startswith("ttsp:")
    }
    assert offered == {"PUBLIC_TO_EVERYONE", "SELF_ONLY"}


def test_chosen_privacy_is_marked(monkeypatch):
    _flags(monkeypatch, direct=True)
    conn = _conn(tt_privacy="SELF_ONLY")
    chosen = [
        b.text for b in _buttons(conn)
        if b.callback_data == f"ttsp:{conn.id}:SELF_ONLY"
    ]
    assert chosen[0].startswith(MARK_CHOSEN)


def test_disappeared_privacy_level_asks_to_choose_again(monkeypatch):
    """Профиль стал приватным → PUBLIC_TO_EVERYONE ушёл из creator_info."""
    _flags(monkeypatch, direct=True)
    info = dict(INFO, privacy_level_options=["SELF_ONLY"])
    text = ts._screen_text(_conn(tt_privacy="PUBLIC_TO_EVERYONE"), info, "ru")
    assert "заново" in text
    assert "Все (Public)" not in text


def test_privacy_must_still_be_offered_by_the_account():
    """Тот же чек охраняет и включение авто-режима: включить автопубликацию с уровнем."""
    assert ts._privacy_ok(_conn(tt_privacy="SELF_ONLY"), INFO) is True
    assert ts._privacy_ok(_conn(), INFO) is False
    assert ts._privacy_ok(
        _conn(tt_privacy="PUBLIC_TO_EVERYONE"),
        dict(INFO, privacy_level_options=["SELF_ONLY"]),
    ) is False
    assert ts._privacy_ok(_conn(tt_privacy="SELF_ONLY"), {}) is False


def test_creator_disabled_interaction_is_greyed(monkeypatch):
    """Дуэты запрещены в настройках аккаунта — метка 🚫 и включить нельзя."""
    _flags(monkeypatch, direct=True)
    by_field = {
        b.callback_data.split(":")[2]: b.text
        for b in _buttons(_conn()) if b.callback_data.startswith("ttst:")
    }
    assert by_field["tt_disable_duet"].startswith(MARK_BLOCKED)
    assert by_field["tt_disable_comment"].startswith(MARK_OFF)


def test_interactions_and_disclosure_are_off_by_default(monkeypatch):
    """Гайдлайны требуют: взаимодействия и раскрытие рекламы — выключены."""
    _flags(monkeypatch, direct=True)
    conn = _conn()
    assert all(getattr(conn, f) for f in ("tt_disable_comment", "tt_disable_stitch"))
    assert not conn.tt_brand_organic and not conn.tt_brand_content
    marks = [b.text for b in _buttons(conn) if b.callback_data.startswith("ttst:")]
    assert all(m.startswith((MARK_OFF, MARK_BLOCKED)) for m in marks)
    on = _buttons(_conn(tt_disable_comment=False))
    comment = next(b.text for b in on if b.callback_data.endswith("tt_disable_comment"))
    assert comment.startswith(MARK_ON)


def test_consent_text_switches_after_enabling(monkeypatch):
    _flags(monkeypatch, direct=True)
    off = ts._screen_text(_conn(), INFO, "ru")
    on = ts._screen_text(
        _conn(tt_auto=True, tt_privacy="SELF_ONLY", tt_consent_at=CONSENT), INFO, "ru"
    )
    assert "Нажимая" in off and "Согласие" in on


def test_music_confirmation_always_shown_and_branded_adds_policy(monkeypatch):
    """Music Usage Confirmation обязателен всегда; при рекламе другого бренда — плюс Branded Content Policy."""
    _flags(monkeypatch, direct=True)
    plain = ts._screen_text(_conn(), INFO, "ru")
    branded = ts._screen_text(_conn(tt_brand_content=True), INFO, "ru")
    assert "music-usage-confirmation" in plain
    assert "music-usage-confirmation" in branded and "bc-policy" in branded


def test_overlay_warning_only_when_overlay_configured(monkeypatch):
    """Оверлей на Direct Post запрещён и молча пропускается — пользователь должен узнать об этом здесь."""
    _flags(monkeypatch, direct=True)
    assert "Оверлей не применяется" not in ts._screen_text(_conn(), INFO, "ru")
    with_ovl = _conn(overlay_file_id="AgAC", overlay_position="bottom_right")
    assert "Оверлей не применяется" in ts._screen_text(with_ovl, INFO, "ru")


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_screen_renders_in_both_languages(monkeypatch, lang):
    _flags(monkeypatch, direct=True)
    conn = _conn(tt_privacy="PUBLIC_TO_EVERYONE")
    text = ts._screen_text(conn, INFO, lang)
    assert "{" not in text
    assert ts.mode_label(conn, lang)
    assert _buttons(conn, lang)


def test_toggle_button_switches_between_on_and_off(monkeypatch):
    _flags(monkeypatch, direct=True)
    off = _conn()
    on = _conn(tt_auto=True, tt_privacy="SELF_ONLY", tt_consent_at=CONSENT)
    assert [b.callback_data for b in _buttons(off) if b.callback_data.startswith("ttsa:")] \
        == ["ttsa:7:1"]
    assert [b.callback_data for b in _buttons(on) if b.callback_data.startswith("ttsa:")] \
        == ["ttsa:7:0"]


def test_nickname_is_escaped(monkeypatch):
    """Ник приходит из TikTok и уходит в parse_mode=HTML."""
    _flags(monkeypatch, direct=True)
    info = dict(INFO, creator_nickname="<b>x</b>")
    assert "&lt;b&gt;" in ts._screen_text(_conn(), info, "ru")


def test_scopes_include_both_when_direct_post_approved(monkeypatch):
    """Аудит покрывает publish и upload: просим оба."""
    _flags(monkeypatch, direct=True)
    assert get_scopes().split(",") == [
        "user.info.basic", "video.publish", "video.upload"
    ]


def test_scopes_omit_publish_without_approval(monkeypatch):
    """Неодобренный scope в authorize-ссылке ломает весь OAuth-флоу."""
    _flags(monkeypatch, direct=False)
    assert get_scopes() == "user.info.basic,video.upload"


def test_job_settings_fall_back_to_connection(monkeypatch):
    """Джоб, созданный до включения авто-режима, не имеет своей приватности."""
    conn = _conn(tt_privacy="PUBLIC_TO_EVERYONE", tt_brand_organic=True)
    job = types.SimpleNamespace(**{f: None for f in POST_FIELDS})
    assert publisher._tt_settings(job, conn)["tt_privacy"] == "PUBLIC_TO_EVERYONE"
    assert publisher._tt_settings(job, conn)["tt_brand_organic"] is True
    job.tt_privacy = "SELF_ONLY"
    job.tt_brand_organic = False
    assert publisher._tt_settings(job, conn)["tt_privacy"] == "SELF_ONLY"
    assert publisher._tt_settings(job, conn)["tt_brand_organic"] is False


@pytest.mark.parametrize(
    "attempts,expected_hours", [(0, 1), (1, 3), (2, 6), (3, 12)]
)
def test_rate_limit_retry_ladder(attempts, expected_hours):
    delay = publisher._publish_retry_delay(attempts, "spam_risk_too_many_posts")
    assert delay == timedelta(hours=expected_hours)


def test_rate_limit_ladder_gives_up_eventually():
    assert publisher._publish_retry_delay(4, "rate_limit_exceeded") is None


def test_only_rate_limit_errors_are_retried():
    """Остальные ошибки — приговор: повторять «видео слишком длинное» бессмысленно."""
    assert publisher._publish_retry_delay(0, "video too long: 900s > 600s") is None
    assert publisher._publish_retry_delay(0, "privacy_level_option_mismatch") is None
