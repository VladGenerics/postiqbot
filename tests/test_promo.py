"""Промокоды: арифметика скидки, правила применимости, разбор аргументов /promo."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bot.i18n import LANGS, T
from bot.services import promo

PLANS = ("starter", "pro", "premium")
NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def _rules(**over) -> str | None:
    base = dict(
        is_active=True,
        expires_at=None,
        used_count=0,
        max_uses=0,
        promo_plan=None,
        plan="pro",
        already_used=False,
        now=NOW,
    )
    return promo.check_rules(**{**base, **over})


@pytest.mark.parametrize(
    "price, percent, expected",
    [
        (100, 30, 70),
        (199, 30, 140),
        (59, 90, 6),
        (1499, 50, 750),
        (199, 0, 199),
        (199, -5, 199),
        (10, 100, 1),
        (1, 90, 1),
    ],
)
def test_discounted(price, percent, expected):
    assert promo.discounted(price, percent) == expected


def test_discount_never_drops_to_zero():
    """Инвойс на 0 не принимает ни Platega, ни Telegram Stars."""
    for price in range(1, 200):
        assert promo.discounted(price, promo.MAX_PERCENT) >= 1


def test_valid_code_passes():
    assert _rules() is None


def test_disabled_code_rejected():
    assert _rules(is_active=False) == promo.INACTIVE


def test_expired_code_rejected_including_the_exact_moment():
    assert _rules(expires_at=NOW - timedelta(seconds=1)) == promo.EXPIRED
    assert _rules(expires_at=NOW) == promo.EXPIRED
    assert _rules(expires_at=NOW + timedelta(seconds=1)) is None


def test_uses_limit():
    assert _rules(max_uses=5, used_count=4) is None
    assert _rules(max_uses=5, used_count=5) == promo.EXHAUSTED
    assert _rules(max_uses=0, used_count=9999) is None


def test_plan_scope():
    assert _rules(promo_plan=None, plan="starter") is None
    assert _rules(promo_plan="pro", plan="pro") is None
    assert _rules(promo_plan="pro", plan="starter") == promo.WRONG_PLAN
    assert _rules(promo_plan="pro", plan=None) is None


def test_second_use_by_the_same_client_rejected():
    assert _rules(already_used=True) == promo.ALREADY_USED


def test_every_reason_has_a_message_in_both_languages():
    """Причина без текста = молчаливый отказ вместо объяснения."""
    for reason in promo.REASONS:
        key = f"promo_bad_{reason}"
        assert key in T, key
        assert set(T[key]) == set(LANGS), key


@pytest.mark.parametrize(
    "raw, expected",
    [("  sale30 ", "SALE30"), ("sa le30", "SALE30"), ("SALE-30", "SALE-30"), ("", "")],
)
def test_normalize_code(raw, expected):
    assert promo.normalize_code(raw) == expected


@pytest.mark.parametrize("code", ["AB", "SALE30", "SALE30-K7QM", "A_B-1", "X" * 32])
def test_valid_codes(code):
    assert promo.is_valid_code(code)


@pytest.mark.parametrize("code", ["", "A", "-AB", "СКИДКА", "SALE 30", "X" * 33, "SALE!"])
def test_invalid_codes(code):
    assert not promo.is_valid_code(code)


@pytest.mark.parametrize(
    "raw, expected", [("30", 30), ("30%", 30), ("-30%", 30), ("0", 0), ("abc", None), ("", None)]
)
def test_parse_percent(raw, expected):
    assert promo.parse_percent(raw) == expected


def test_generated_code_is_usable():
    code = promo.generate_code(30)
    assert code.startswith("SALE30-")
    assert promo.is_valid_code(code)
    assert promo.normalize_code(code) == code


def test_minimal_form_is_just_the_percent():
    data, error = promo.parse_new(["30"], PLANS)
    assert error is None
    assert (data.percent, data.plan, data.max_uses, data.days) == (30, None, 0, None)
    assert promo.is_valid_code(data.code)


def test_full_form():
    data, error = promo.parse_new(
        ["CREATOR50", "50", "pro", "uses=100", "days=7"], PLANS
    )
    assert error is None
    assert data.code == "CREATOR50"
    assert (data.percent, data.plan, data.max_uses, data.days) == (50, "pro", 100, 7)


def test_arguments_work_in_any_order():
    data, error = promo.parse_new(["uses=5", "premium", "30%", "mycode"], PLANS)
    assert error is None
    assert (data.code, data.percent, data.plan, data.max_uses) == ("MYCODE", 30, "premium", 5)


@pytest.mark.parametrize("token", ["all", "все", "*"])
def test_all_plans_can_be_stated_explicitly(token):
    data, error = promo.parse_new([token, "30"], PLANS)
    assert error is None and data.plan is None


@pytest.mark.parametrize(
    "args, expected",
    [
        (["pro"], "no_percent"),
        ([], "no_percent"),
        (["0"], "bad_percent"),
        (["100"], "bad_percent"),
        (["91"], "bad_percent"),
        (["30", "SALE!"], "bad_code"),
        (["30", "uses=много"], "bad_uses"),
        (["30", "days=0"], "bad_days"),
        (["30", "срок=7"], "bad_token"),
        (["30", "CODE1", "CODE2"], "bad_token"),
    ],
)
def test_bad_arguments_are_named(args, expected):
    data, error = promo.parse_new(args, PLANS)
    assert data is None and error == expected
