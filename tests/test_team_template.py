"""The winners' template's pieces (TEAM_TEMPLATE_PLAN.md)."""
from datetime import date

from services import season_ledger as L
from services import team_template as T
from services.team_roles import bat_slot


def test_seasons_split_at_july_for_leagues_across_new_year():
    assert L._season_of(date(2025, 5, 1), cross_year=False) == "2025"
    assert L._season_of(date(2024, 12, 20), cross_year=True) == "2024-25"
    assert L._season_of(date(2025, 1, 25), cross_year=True) == "2024-25"


def test_renamed_franchises_are_one_side():
    assert L.team_key("Royal Challengers Bangalore") == L.team_key("Royal Challengers Bengaluru")
    assert L.team_key("Delhi Daredevils") == L.team_key("Delhi Capitals")


def test_every_ipl_season_is_pinned():
    assert sorted(L.VERIFIED["IPL"]) == [str(y) for y in range(2008, 2027)]
    assert all(champ in sides for champ, sides in L.VERIFIED["IPL"].values())


def test_batting_slots():
    assert [bat_slot(p) for p in (1, 2, 3, 4, 5, 7, 8, 11)] == ["openers"] * 2 + ["top"] * 2 + ["middle"] * 2 + ["lower"] * 2


def test_percentiles_run_worst_to_best_both_ways():
    assert T.percentiles({"a": 7.0, "b": 8.0, "c": 9.0}, lower=True) == {"a": 1.0, "b": 0.5, "c": 0.0}
    assert T.percentiles({"a": 30.0, "b": 40.0, "c": 50.0}, lower=False) == {"a": 0.0, "b": 0.5, "c": 1.0}
    assert T.percentiles({"a": 1.0, "b": None}, lower=False) == {}       # too few to rank
    assert T.lower_is_better("bowl:death:economy") and T.lower_is_better("bat:openers:dot_pct")
    assert not T.lower_is_better("bowl:death:dot_pct") and not T.lower_is_better("bat:openers:average")
