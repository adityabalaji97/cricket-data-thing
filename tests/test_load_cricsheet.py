"""Cricsheet fallback loader (scripts/load_cricsheet.py), the sync's upgrade path and scorecard routing."""
import copy
import os
import sys
from datetime import date
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from load_cricsheet import (  # noqa: E402
    CricsheetMatch,
    NameResolver,
    competition_for,
    legacy_deliveries,
    match_row,
    same_fixture_ids,
    scope_reason,
    stat_deliveries,
)


def _ball(batter, bowler, bat=0, extras=None, wicket=None, non_striker="C Nonstriker"):
    extras = extras or {}
    ball = {
        "batter": batter, "bowler": bowler, "non_striker": non_striker,
        "runs": {"batter": bat, "extras": sum(extras.values()), "total": bat + sum(extras.values())},
    }
    if extras:
        ball["extras"] = extras
    if wicket:
        ball["wickets"] = [wicket]
    return ball


def _match(**info_overrides):
    info = {
        "dates": ["2026-09-12"], "gender": "male", "match_type": "T20", "team_type": "international",
        "balls_per_over": 6, "teams": ["Nepal", "United Arab Emirates"],
        "event": {"name": "ACC Men's Premier Cup", "match_number": 3},
        "venue": "Bayuemas Oval, Kuala Lumpur", "city": "Kuala Lumpur",
        "toss": {"winner": "United Arab Emirates", "decision": "field"},
        "outcome": {"winner": "Nepal", "by": {"runs": 5}},
        "player_of_match": ["A Batter"],
        "registry": {"people": {"A Batter": "p1", "B Bowler": "p2", "C Nonstriker": "p3"}},
    }
    info.update(info_overrides)
    innings = [
        {"team": "Nepal", "overs": [{"over": 0, "deliveries": [
            _ball("A Batter", "B Bowler", extras={"wides": 1}),
            _ball("A Batter", "B Bowler", bat=4),
            _ball("A Batter", "B Bowler", extras={"legbyes": 1}),
            _ball("C Nonstriker", "B Bowler", wicket={"kind": "lbw", "player_out": "C Nonstriker"}),
            _ball("A Batter", "B Bowler", extras={"penalty": 5}),
            # Non-striker run out: a wicket on the ball, but not the striker's.
            _ball("A Batter", "B Bowler", bat=1, wicket={"kind": "run out", "player_out": "C Nonstriker",
                                                          "fielders": [{"name": "B Bowler"}]}),
            _ball("A Batter", "B Bowler", bat=6),
        ]}]},
        {"team": "United Arab Emirates", "overs": [{"over": 0, "deliveries": [
            _ball("B Bowler", "A Batter", bat=2),
        ]}, {"over": 1, "deliveries": [_ball("B Bowler", "A Batter", bat=1)]}]},
        {"team": "Nepal", "super_over": True, "overs": [{"over": 0, "deliveries": [_ball("A Batter", "B Bowler", bat=6)]}]},
    ]
    return CricsheetMatch("1549969", {"info": info, "innings": innings})


def ident(name):
    return name


# ---- scope -------------------------------------------------------------------------------

def test_scope_takes_internationals_and_main_leagues_only():
    assert scope_reason(_match()) is None
    assert scope_reason(_match(match_type="ODI")) is None
    assert scope_reason(_match(team_type="club", event={"name": "Caribbean Premier League"})) is None
    assert scope_reason(_match(team_type="club", event={"name": "Major Clubs T20 Tournament"})) is not None
    assert scope_reason(_match(team_type="club", event={"name": "The Hundred Men's Competition"})) is not None
    assert scope_reason(_match(gender="female")) == "not men"
    assert scope_reason(_match(match_type="Test")) is not None
    assert scope_reason(_match(balls_per_over=5)) is not None


def test_scope_refuses_pre_2015_so_legacy_deliveries_stay_pre_2015_t20():
    assert scope_reason(_match(dates=["2014-12-31"])) == "before 2015"


def test_competition_buckets_match_the_sync():
    teams = ["Nepal", "United Arab Emirates"]
    assert competition_for(_match(), teams) == ("T20I", "ACC Men's Premier Cup", "international")
    assert competition_for(_match(match_type="ODI"), teams) == ("ODI", "ACC Men's Premier Cup", "international")
    wc = _match(match_type="ODI", event={"name": "ICC World Cup"})
    assert competition_for(wc, ["India", "Australia"])[0] == "ICC World Cup"
    cpl = _match(team_type="club", event={"name": "Caribbean Premier League"})
    assert competition_for(cpl, ["Trinbago Knight Riders", "St Lucia Kings"]) == ("CPL", "Caribbean Premier League", "league")


# ---- conversion --------------------------------------------------------------------------

def test_stat_deliveries_follow_delivery_details_conventions():
    rows = stat_deliveries(_match(), ident)
    first = [r for r in rows if r["innings"] == 1]
    # Every delivery numbered, the wide included; super over left out.
    assert [r["ball"] for r in first] == [1, 2, 3, 4, 5, 6, 7]
    assert {r["innings"] for r in rows} == {1, 2}
    assert first[0]["wide"] == 1 and first[0]["outcome"] == "wide"
    lbw = first[3]
    assert lbw["dismissal"] == "leg before wicket" and lbw["out"] == "true" and lbw["bat_out"] == "true"
    run_out = first[5]
    assert run_out["out"] == "true" and run_out["bat_out"] == "false"
    # Penalty runs are nobody's.
    assert first[4]["score"] == 0
    assert first[0]["bowling_team"] == "United Arab Emirates" and first[0]["format"] == "T20"


def test_stats_writer_reads_converted_balls_with_one_set_of_rules():
    from sync_stats_from_dd import StatsFromDeliveryDetails

    writer = StatsFromDeliveryDetails.__new__(StatsFromDeliveryDetails)  # no DB connection
    rows = stat_deliveries(_match(), ident)
    bowling = writer.calculate_bowling_stats("1549969", 1, "B Bowler", rows)
    assert bowling.wickets == 1  # the lbw; the run out is not the bowler's
    assert bowling.runs_conceded == 1 + 4 + 1 + 6  # wide, four, single, six; no leg-bye, no penalty
    assert bowling.overs == 1.0
    batting = writer.calculate_batting_stats("1549969", 1, "A Batter", rows)
    assert batting.runs == 11 and batting.balls_faced == 5 and batting.wickets == 0
    assert batting.fours == 1 and batting.sixes == 1


def test_legacy_deliveries_keep_cricsheet_wicket_kinds_for_the_scorecard():
    rows = legacy_deliveries(_match(), ident)
    assert rows[3]["wicket_type"] == "lbw" and rows[3]["player_dismissed"] == "C Nonstriker"
    assert rows[5]["fielder"] == "B Bowler"
    assert rows[0]["wides"] == 1 and rows[4]["penalty"] == 5
    assert all(r["innings"] in (1, 2) for r in rows)


def test_match_row_derives_fields_like_the_sync():
    row = match_row(_match(), ident)
    assert row["team1"] == "Nepal" and row["bat_first"] == "Nepal" and row["bowl_first"] == "United Arab Emirates"
    assert row["won_batting_first"] is True and row["won_fielding_first"] is False
    assert row["win_toss_win_match"] is False
    assert row["overs"] == 2  # overs actually bowled (0-indexed max + 1), super over excluded
    assert row["data_source"] == "cricsheet" and row["format"] == "T20" and row["gender"] == "male"
    assert row["date"] == date(2026, 9, 12) and row["event_match_number"] == 3
    assert row["player_of_match"] == "A Batter"


def test_match_row_canonicalises_renamed_franchises():
    m = _match(team_type="club", event={"name": "Indian Premier League"},
               teams=["Kings XI Punjab", "Royal Challengers Bangalore"],
               outcome={"winner": "Kings XI Punjab"}, toss={"winner": "Kings XI Punjab", "decision": "bat"})
    m.data["innings"][0]["team"] = "Kings XI Punjab"
    m.data["innings"][1]["team"] = "Royal Challengers Bangalore"
    row = match_row(m, ident)
    assert (row["team1"], row["team2"], row["winner"]) == ("Punjab Kings", "Royal Challengers Bengaluru", "Punjab Kings")
    assert row["competition"] == "IPL"


# ---- database-facing ---------------------------------------------------------------------

def _session(*results):
    session = MagicMock()
    session.execute.return_value.fetchall.side_effect = list(results)
    return session


def test_name_resolver_prefers_feed_name_then_alias_then_cricsheet():
    register = {"p1": [111], "p2": [222], "p3": [333]}
    session = _session(
        [(111, "Aasif Sheikh"), (333, "Vaibhav Suryavanshi")],          # feed names by cricinfo id
        [("B Bowler", "Bravo Bowler", "bbb_dataset"),                   # alias fallback
         ("Vaibhav Suryavanshi", "Vaibhav Sooryavanshi", "spelling_variant")],
    )
    resolve = NameResolver.build(session, [_match()], register)
    assert resolve("A Batter") == "Aasif Sheikh"
    assert resolve("B Bowler") == "Bravo Bowler"
    assert resolve("C Nonstriker") == "Vaibhav Sooryavanshi"  # reviewed spelling -> main name
    assert resolve("Someone Else") == "Someone Else"


def test_name_resolver_ignores_ambiguous_aliases():
    session = _session([], [("B Bowler", "Ben Bowler", "bbb_dataset"), ("B Bowler", "Bob Bowler", "bbb_dataset")])
    assert NameResolver.build(session, [_match()], {})("B Bowler") == "B Bowler"


def test_same_fixture_guard_sees_through_renames_and_team_order():
    m = _match(teams=["Kings XI Punjab", "Mumbai Indians"])
    session = _session([("1000", "Mumbai Indians", "Punjab Kings"), ("1001", "Mumbai Indians", "Chennai Super Kings")])
    assert same_fixture_ids(session, m) == ["1000"]


def test_upgrade_refreshes_row_and_drops_cricsheet_rows():
    from sync_from_delivery_details import DeliveryDetailsSync

    sync = DeliveryDetailsSync.__new__(DeliveryDetailsSync)
    session = MagicMock()
    sync.SessionLocal = lambda: session
    sync.get_cricsheet_match_ids_to_upgrade = lambda s: ["1549969"]
    sync.extract_match_data_from_dd = lambda s, mid: {"id": mid, "venue": "Bayuemas Oval", "data_source": "bbb"}

    assert sync.upgrade_cricsheet_matches() == {"upgraded": 1, "errors": 0}
    statements = [str(call.args[0]) for call in session.execute.call_args_list]
    assert any(s.startswith("UPDATE matches SET") and "data_source = :data_source" in s for s in statements)
    for table in ("batting_stats", "bowling_stats", "deliveries"):
        assert any(f"DELETE FROM {table}" in s for s in statements)
    session.commit.assert_called_once()


def test_scorecard_reads_legacy_deliveries_for_cricsheet_matches(monkeypatch):
    import services.match_scorecard as sc

    match = {"id": "1549969", "date": date(2026, 9, 12), "format": "ODI", "gender": "male",
             "data_source": "cricsheet", "team1": "Nepal", "team2": "United Arab Emirates"}
    monkeypatch.setattr(sc, "_fetch_match", lambda mid, db: dict(match))
    called = {}
    monkeypatch.setattr(sc, "_build_details_innings", lambda *a, **k: pytest.fail("read delivery_details"))
    monkeypatch.setattr(sc, "_build_legacy_innings", lambda *a, **k: called.setdefault("legacy", [{"innings": 1}]))
    monkeypatch.setattr(sc, "_build_summary", lambda m, i: {})
    monkeypatch.setattr(sc, "_format_match", lambda m, i: m)

    result = sc.get_match_scorecard_service("1549969", 1, MagicMock())
    assert "legacy" in called
    assert result["meta"]["data_source"] == "deliveries"
    assert result["meta"]["warnings"][0].startswith("Basic data from Cricsheet")
    assert result["summary"]["primer"] is None
