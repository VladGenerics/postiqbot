"""Не прошедший аудит клиент TikTok: видео уходит в черновики, а не в мусор."""
from __future__ import annotations

import asyncio

import pytest

from bot.config import get_settings
from bot.services import publisher, tiktok_api
from bot.services.tiktok_api import (
    TikTokScopeError,
    TikTokUnauditedError,
    _raise_for_error,
)

UNAUDITED = "unaudited_client_can_only_post_to_private_accounts"
GUIDELINES = "Please review our integration guidelines"


def _err(code: str, message: str = "") -> dict:
    return {"error": {"code": code, "message": message}}


def _task(**over) -> publisher._Task:
    fields = dict(
        job_id=1122,
        user_id=6075105131,
        title="Он приструнил неуправляемого ребёнка",
        local_path="/tmp/video.mp4",
        platform="tiktok",
        refresh_token="rt",
        account_id=23,
        connection_id=57,
        source_platform="tiktok",
        tt_privacy="PUBLIC_TO_EVERYONE",
    )
    fields.update(over)
    return publisher._Task(**fields)


@pytest.fixture
def direct_on(monkeypatch):
    monkeypatch.setenv("TIKTOK_DIRECT_POST", "true")
    monkeypatch.setenv("TIKTOK_DIRECT_ANY_SOURCE", "true")
    get_settings.cache_clear()


@pytest.fixture
def tt_calls(monkeypatch):
    """Подменить сетевые вызовы TikTok и записать, что было вызвано."""
    calls: list[str] = []

    async def access_token(account_id: int) -> str:
        calls.append(f"token:{account_id}")
        return "at"

    async def creator_info(access: str) -> dict:
        calls.append("creator_info")
        return {"privacy_level_options": ["PUBLIC_TO_EVERYONE", "SELF_ONLY"],
                "max_video_post_duration_sec": 0}

    async def inbox(access: str, path: str) -> str:
        calls.append("inbox")
        return "inbox-publish-id"

    monkeypatch.setattr(publisher.tiktok_tokens, "access_token", access_token)
    monkeypatch.setattr(publisher.tiktok_api, "get_creator_info", creator_info)
    monkeypatch.setattr(publisher.tiktok_api, "upload_to_inbox", inbox)
    return calls


def test_unaudited_code_becomes_its_own_error():
    """Своё исключение, а не ValueError: publisher ловит именно его."""
    with pytest.raises(TikTokUnauditedError) as e:
        _raise_for_error(_err(UNAUDITED, GUIDELINES), "direct init")
    assert UNAUDITED in str(e.value)


def test_other_errors_keep_their_classes():
    """Соседние ветки не задеты: scope — своя ошибка, остальное — ValueError."""
    with pytest.raises(TikTokScopeError):
        _raise_for_error(_err("scope_not_authorized"), "direct init")
    with pytest.raises(ValueError) as e:
        _raise_for_error(_err("spam_risk_too_many_posts"), "direct init")
    assert not isinstance(e.value, TikTokUnauditedError)
    _raise_for_error({"error": {"code": "ok"}}, "direct init")


def test_unaudited_is_not_a_rate_limit():
    """Лестница повторов тут не поможет: аудит не пройдёт сам через час."""
    assert publisher._publish_retry_delay(0, f"TikTok direct init: {UNAUDITED}") is None


def test_direct_post_falls_back_to_drafts(direct_on, tt_calls, monkeypatch):
    async def direct_post(*a, **kw):
        raise TikTokUnauditedError(f"TikTok direct init: {UNAUDITED} {GUIDELINES}")

    monkeypatch.setattr(publisher.tiktok_api, "direct_post", direct_post)
    task = _task()
    assert task.tt_direct is True

    remote_id = asyncio.run(publisher._publish(task, "/tmp/video.mp4"))

    assert remote_id == "inbox-publish-id"
    assert tt_calls == ["token:23", "creator_info", "inbox"]
    assert task.fell_back_to_draft is True


def test_successful_direct_post_does_not_touch_drafts(direct_on, tt_calls, monkeypatch):
    async def direct_post(*a, **kw):
        return "direct-publish-id"

    async def poll(access: str, publish_id: str) -> None:
        return None

    monkeypatch.setattr(publisher.tiktok_api, "direct_post", direct_post)
    monkeypatch.setattr(publisher.tiktok_api, "poll_publish_status", poll)
    task = _task()

    assert asyncio.run(publisher._publish(task, "/tmp/video.mp4")) == "direct-publish-id"
    assert "inbox" not in tt_calls
    assert task.fell_back_to_draft is False


def test_other_publish_errors_still_fail_the_job(direct_on, tt_calls, monkeypatch):
    """Откат — только для аудита. Прочие ошибки должны дойти до пользователя."""
    async def direct_post(*a, **kw):
        raise ValueError("TikTok direct init: spam_risk_too_many_posts")

    monkeypatch.setattr(publisher.tiktok_api, "direct_post", direct_post)
    with pytest.raises(ValueError):
        asyncio.run(publisher._publish(_task(), "/tmp/video.mp4"))
    assert "inbox" not in tt_calls


def test_draft_connections_go_straight_to_inbox(direct_on, tt_calls, monkeypatch):
    """Связка без Direct Post и раньше публиковала в черновики — путь не изменился (и флаг «откатились» не ставится."""
    monkeypatch.setenv("TIKTOK_DIRECT_POST", "false")
    get_settings.cache_clear()
    task = _task()
    assert task.tt_direct is False

    assert asyncio.run(publisher._publish(task, "/tmp/video.mp4")) == "inbox-publish-id"
    assert tt_calls == ["token:23", "inbox"]
    assert task.fell_back_to_draft is False


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_fallback_message_explains_audit_and_drafts(direct_on, lang):
    task = _task()
    task.fell_back_to_draft = True
    text = publisher._success_msg(task, "inbox-publish-id", lang)

    assert task.title in text
    assert "{" not in text
    words = ("аудит", "черновик") if lang == "ru" else ("audit", "draft")
    assert all(w in text.lower() for w in words)
    assert text.startswith("⚠️")


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_normal_messages_unchanged(direct_on, monkeypatch, lang):
    live = publisher._success_msg(_task(), "id", lang)
    monkeypatch.setenv("TIKTOK_DIRECT_ANY_SOURCE", "false")
    get_settings.cache_clear()
    draft = publisher._success_msg(_task(source_platform="youtube"), "id", lang)

    live_word, draft_word = (
        ("опубликовано", "черновики") if lang == "ru" else ("published", "drafts")
    )
    assert live_word in live.lower() and live.startswith("✅")
    assert draft_word in draft.lower() and draft.startswith("✅")


def test_unaudited_error_is_not_reported_as_a_crash(direct_on):
    """Страховка от «поймали и забыли»: _fail_msg для этой ошибки существовать не должен — до него дело не доходит."""
    assert issubclass(TikTokUnauditedError, RuntimeError)
    assert not issubclass(TikTokUnauditedError, TikTokScopeError)
    assert tiktok_api.TikTokUnauditedError is TikTokUnauditedError
