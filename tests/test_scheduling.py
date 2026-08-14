"""Расписание публикаций: compute_scheduled_at."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bot.services.scheduling import compute_scheduled_at

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)


def _at(mode: str, **kw) -> datetime:
    defaults = dict(
        mode=mode,
        interval_minutes=0,
        post_times=None,
        tz_name="UTC",
        last_scheduled=None,
        now=NOW,
    )
    defaults.update(kw)
    return compute_scheduled_at(**defaults)  # type: ignore[arg-type]


class TestImmediate:
    def test_immediate_is_now(self):
        assert _at("immediate") == NOW

    @pytest.mark.parametrize("mode", ["", "unknown", "interval", "times"])
    def test_without_parameters_falls_back_to_now(self, mode):
        assert _at(mode) == NOW


class TestInterval:
    def test_first_job_goes_now(self):
        assert _at("interval", interval_minutes=480) == NOW

    def test_next_job_is_interval_after_previous(self):
        last = NOW - timedelta(minutes=10)
        assert _at("interval", interval_minutes=480, last_scheduled=last) == (
            last + timedelta(minutes=480)
        )

    def test_stale_previous_does_not_schedule_into_the_past(self):
        last = NOW - timedelta(days=1)
        assert _at("interval", interval_minutes=480, last_scheduled=last) == NOW

    def test_queue_is_strictly_increasing(self):
        """Пачка подтверждённых видео растягивается, а не выходит залпом."""
        last, seen = None, []
        for _ in range(5):
            last = _at("interval", interval_minutes=480, last_scheduled=last)
            seen.append(last)
        assert seen == sorted(seen)
        assert len(set(seen)) == len(seen)
        assert seen[-1] - seen[0] == timedelta(minutes=480 * 4)


class TestTimes:
    def test_picks_next_slot_today_in_connection_tz(self):
        got = _at(
            "times", post_times=["09:00", "21:00"], tz_name="Europe/Moscow"
        )
        assert got == datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)

    def test_rolls_over_to_tomorrow_when_slots_passed(self):
        got = _at(
            "times",
            post_times=["09:00"],
            tz_name="Europe/Moscow",
            now=datetime(2026, 8, 14, 20, 0, tzinfo=timezone.utc),
        )
        assert got == datetime(2026, 8, 15, 6, 0, tzinfo=timezone.utc)

    def test_slot_is_after_previous_job(self):
        """Слот занят предыдущим джобом → берём следующий, а не тот же самый."""
        last = datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)
        got = _at(
            "times",
            post_times=["09:00", "21:00"],
            tz_name="Europe/Moscow",
            last_scheduled=last,
        )
        assert got == datetime(2026, 8, 15, 6, 0, tzinfo=timezone.utc)

    def test_unparsable_times_are_skipped(self):
        got = _at(
            "times",
            post_times=["", "оценка", "21:00", "99"],
            tz_name="Europe/Moscow",
        )
        assert got == datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)

    def test_all_times_broken_falls_back_to_now(self):
        assert _at("times", post_times=["nope", "-"], tz_name="UTC") == NOW

    def test_unknown_tz_falls_back_to_utc(self):
        got = _at("times", post_times=["13:00"], tz_name="Nowhere/Nope")
        assert got == datetime(2026, 8, 14, 13, 0, tzinfo=timezone.utc)

    def test_result_is_utc_aware(self):
        got = _at("times", post_times=["09:00"], tz_name="Asia/Tokyo")
        assert got.tzinfo is timezone.utc
        assert got > NOW
