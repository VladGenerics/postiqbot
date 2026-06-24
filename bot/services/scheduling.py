"""Расчёт времени публикации job'а по расписанию связки."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def _next_time_slot(
    post_times: list[str], tz_name: str, after_utc: datetime
) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    parsed: list[tuple[int, int]] = []
    for t in post_times:
        try:
            h, m = t.split(":")
            parsed.append((int(h), int(m)))
        except Exception:
            continue
    if not parsed:
        return after_utc
    parsed.sort()
    after_local = after_utc.astimezone(tz)
    for day_offset in range(0, 8):
        day = (after_local + timedelta(days=day_offset)).date()
        for h, m in parsed:
            cand_local = datetime(day.year, day.month, day.day, h, m, tzinfo=tz)
            cand_utc = cand_local.astimezone(timezone.utc)
            if cand_utc > after_utc:
                return cand_utc
    return after_utc


def compute_scheduled_at(
    *,
    mode: str,
    interval_minutes: int,
    post_times: list[str] | None,
    tz_name: str,
    last_scheduled: datetime | None,
    now: datetime,
) -> datetime:
    """Когда публиковать следующий job этой связки."""
    if mode == "interval" and interval_minutes > 0:
        if last_scheduled is None:
            return now
        return max(now, last_scheduled + timedelta(minutes=interval_minutes))

    if mode == "times" and post_times:
        after = now
        if last_scheduled is not None and last_scheduled > after:
            after = last_scheduled + timedelta(seconds=1)
        return _next_time_slot(post_times, tz_name, after)

    return now
