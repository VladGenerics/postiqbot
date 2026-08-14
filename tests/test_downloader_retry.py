"""Классификация ошибок скачивания и лестница повторов."""
from __future__ import annotations

from datetime import timedelta

import pytest

from bot.services import downloader as dl

TRANSIENT_MESSAGES = [
    "ERROR: [TikTok] 7530000000000000001: Unexpected response from webpage request",
    "ERROR: [TikTok] 7530000000000000002: Unable to extract universal data",
    "ERROR: [TikTok] 7530000000000000003: Unable to extract challenge data",
    "ERROR: [youtube] abcdefghijk: Unable to solve JS challenge",
    "ERROR: [TikTok] 7530000000000000004: Unable to extract aweme detail",
]

PERMANENT_MESSAGES = [
    "ERROR: [youtube] abcdefghijk: Sign in to confirm your age. "
    "This video may be inappropriate for some users.",
    "ERROR: [youtube] abcdefghijk: Video unavailable",
    "ERROR: [youtube] abcdefghijk: Private video. Sign in if you've been granted access",
    "ERROR: [TikTok] 7530000000000000005: Video not available",
    "HTTPError 403: Forbidden",
    "",
]


class TestIsTransient:
    @pytest.mark.parametrize("message", TRANSIENT_MESSAGES)
    def test_waf_stubs_are_transient(self, message):
        assert dl._is_transient(message) is True

    @pytest.mark.parametrize("message", PERMANENT_MESSAGES)
    def test_real_failures_are_permanent(self, message):
        assert dl._is_transient(message) is False

    def test_matching_ignores_case(self):
        assert dl._is_transient("UNABLE TO EXTRACT UNIVERSAL DATA") is True

    def test_every_marker_is_lowercase(self):
        """_is_transient сравнивает с error.lower() — маркер с заглавной никогда не сматчится, и это молча ломает ретрай."""
        assert all(m == m.lower() for m in dl._TRANSIENT_ERRORS)


class TestRequeueDelay:
    def test_ladder_matches_configuration(self):
        got = [dl._requeue_delay(i) for i in range(len(dl._REQUEUE_DELAYS_MINUTES))]
        assert got == [timedelta(minutes=m) for m in dl._REQUEUE_DELAYS_MINUTES]

    def test_gives_up_after_last_attempt(self):
        assert dl._requeue_delay(len(dl._REQUEUE_DELAYS_MINUTES)) is None
        assert dl._requeue_delay(len(dl._REQUEUE_DELAYS_MINUTES) + 7) is None

    def test_delays_never_shrink(self):
        assert list(dl._REQUEUE_DELAYS_MINUTES) == sorted(dl._REQUEUE_DELAYS_MINUTES)

    def test_first_retry_is_soon_and_total_covers_multiday_outage(self):
        """Первая попытка — быстро (ошибка часто секундная), суммарно ретраим больше двух суток."""
        assert dl._requeue_delay(0) <= timedelta(hours=1)
        total = sum(dl._REQUEUE_DELAYS_MINUTES)
        assert timedelta(days=2) <= timedelta(minutes=total) <= timedelta(days=5)


class TestFastRetries:
    def test_in_process_retries_are_short(self):
        """Быстрые ретраи внутри download() держат поток воркера — они должны оставаться секундами, а не минутами."""
        assert dl._RETRY_DELAYS
        assert sum(dl._RETRY_DELAYS) <= 120


class TestAgeRestricted:
    def test_detects_age_wall(self):
        assert dl._is_age_restricted(PERMANENT_MESSAGES[0]) is True

    @pytest.mark.parametrize("message", TRANSIENT_MESSAGES + ["Video unavailable"])
    def test_other_errors_are_not_age_wall(self, message):
        assert dl._is_age_restricted(message) is False
