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


def test_ipl_team_names_are_restored_to_what_they_were_that_season():
    assert dg.historical_team("Punjab Kings", 2019) == "Kings XI Punjab"
    assert dg.historical_team("Punjab Kings", 2021) == "Punjab Kings"
    assert dg.historical_team("Delhi Capitals", 2016) == "Delhi Daredevils"
    assert dg.historical_team("Royal Challengers Bengaluru", 2023) == "Royal Challengers Bangalore"
    assert dg.historical_team("Rising Pune Supergiants", 2016) == "Rising Pune Supergiant"
    assert dg.historical_team("Deccan Chargers", 2010) == "Deccan Chargers"


def test_journey_collapses_consecutive_seasons_and_splits_on_gaps():
    stints = dg.collapse_journey({("CSK", 2008), ("CSK", 2009), ("RPS", 2016), ("CSK", 2018), ("CSK", 2019)})
    assert stints == [
        {"team": "CSK", "years": "2008-2009"},
        {"team": "RPS", "years": "2016"},
        {"team": "CSK", "years": "2018-2019"},
    ]
