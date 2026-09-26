"""Daily games: deterministic seeds, IST rollover, numbering (no database needed)."""

from datetime import date, datetime, timezone

from services import daily_games as dg


def test_same_day_same_puzzle_order():
    a = dg.rng_for("call-it", date(2026, 10, 1)).random()
    b = dg.rng_for("call-it", date(2026, 10, 1)).random()
    assert a == b


def test_games_and_days_get_different_seeds():
    day = date(2026, 10, 1)
    assert dg.rng_for("call-it", day).random() != dg.rng_for("higher-lower", day).random()
    assert dg.rng_for("call-it", day).random() != dg.rng_for("call-it", date(2026, 10, 2)).random()


def test_day_rolls_over_at_ist_midnight():
    # 18:29 UTC is 23:59 IST; 18:31 UTC is the next day in India.
    assert dg.today_ist(datetime(2026, 10, 1, 18, 29, tzinfo=timezone.utc)) == date(2026, 10, 1)
    assert dg.today_ist(datetime(2026, 10, 1, 18, 31, tzinfo=timezone.utc)) == date(2026, 10, 2)


def test_puzzle_numbers_start_at_one_on_launch():
    assert dg.puzzle_number(dg.LAUNCH_DATE) == 1


def test_resolve_day_never_serves_the_future_or_pre_launch():
    today = dg.today_ist()
    assert dg.resolve_day(None) == today
    assert dg.resolve_day(date(2099, 1, 1)) == today
    assert dg.resolve_day(date(2000, 1, 1)) == dg.LAUNCH_DATE
