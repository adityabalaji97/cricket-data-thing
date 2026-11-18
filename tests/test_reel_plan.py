"""The motion Reel planner (MOTION_REEL_PLAN.md M5): cards and a script into an anchored reel spec that, timed by the
voice (here estimated: no voice, no model), passes the Reel checks."""
from services import reel_plan as P
from services import reel_timing as T
from services.social_rules import reel_problems

BARS = {"id": "carried", "visual": "metric_bars", "sample": "IPL 2025-26, any side",
        "payload": {"metric": {"label": "Wins added since the 2025 auction", "format": "signed2", "signed": True},
                    "rows": [{"name": "Jasprit Bumrah", "value": 1.98, "highlight": True, "detail": "22 wkts"},
                             {"name": "Arshdeep Singh", "value": 1.89}, {"name": "Deepak Chahar", "value": -0.56}]}}
BATTING = {"id": "batting", "visual": "metric_bars", "kicker": "Batting by role", "sample": "60+ balls",
           "payload": {"metric": {"label": "Runs above par per 100 balls", "format": "signed1"},
                       "rows": [{"name": "Opener · R Rickelton", "value": 17.0, "highlight": True},
                                {"name": "Finisher · C Bosch", "value": -3.5, "highlight": True}]}}
GRID = {"id": "bowling", "visual": "grid_heat", "kicker": "Bowling by phase", "sample": "per 24 balls",
        "payload": {"cols": ["Powerplay", "Death"], "rows": [{"name": "J Bumrah", "cells": [{"value": 3.5}, {"value": 11.2}]},
                                                             {"name": "T Boult", "cells": [{"value": -5.7}, {"value": 4.0}]}]}}
CASES = {"id": "cases", "visual": "case_board", "sample": "prices: 2026 squad",
         "payload": {"cases": [{"name": "Rohit Sharma", "price": "₹16.30 crore", "for": "+18", "against": "−0.09"},
                               {"name": "Deepak Chahar", "price": "₹9.25 crore", "for": "32 wkts", "against": "−0.56"}]}}
LINES = [
    "Bumrah added 1.98 wins since the auction. Arshdeep, traded in: 1.89.",
    "Rickelton leads the batting, seventeen above par.",
    "Bumrah at the death saves eleven runs every four overs.",
    "Two calls: Rohit at 16.3 crore, Chahar at 9.25 crore.",
    "Rohit Sharma, keep or release? Send this to a Mumbai fan.",
]
CLOSE = {"question": "Rohit Sharma, ₹16.30 crore:", "lit": "keep or release?", "send": "Send this to a Mumbai fan"}


def test_lit_keys():
    assert P.lit_keys(BARS) == [{"key": "Jasprit Bumrah", "value": 1.98}]
    assert P.lit_keys(GRID) == [{"key": "J Bumrah · Death", "value": 11.2}]
    assert [k["key"] for k in P.lit_keys(CASES)] == ["Rohit Sharma", "Deepak Chahar"]


def test_a_below_par_highlight_is_never_the_lit_item():
    s = P.card_scene(BATTING, 1, LINES[1])
    assert [b["key"] for b in s["beats"]] == ["Opener · R Rickelton"]


def test_beats_land_on_the_spoken_name():
    s = P.card_scene(BATTING, 1, LINES[1])
    assert s["beats"][0]["anchor"] == {"line": 1, "word": 0}  # "Rickelton"
    c = P.card_scene(CASES, 3, LINES[3])
    assert [b["anchor"]["word"] for b in c["beats"]] == [2, 6]  # "Rohit", "Chahar"
    assert c["pages"]["field"] == "cases"


def test_hero_opens_on_the_name_and_number():
    h = P.hero_scene(BARS, LINES[0], "MI")
    assert h["kind"] == "hero" and h["data"]["name"] == "Jasprit Bumrah" and h["data"]["value"] == 1.98
    assert h["data"]["second"]["name"] == "Arshdeep Singh" and h["data"]["second"]["anchor"]["word"] == 7


def test_planned_and_timed_reel_passes_the_checks():
    spec = P.plan([BARS, BATTING, GRID, CASES], LINES, team="MI", close=CLOSE)
    timing = T.estimate(LINES)
    placed = T.place(spec, timing, hold=2.0)
    # an estimated 5-line script is short: stretch it to Reel length for the checks (the voice sets real times)
    assert [s["kind"] for s in placed["scenes"]] == ["hero", "metric_bars", "grid_heat", "case_board", "pick_one"]
    assert placed["scenes"][-1]["captions"] is False
    assert all(b["at"] >= s["start"] for s in placed["scenes"] for b in s.get("beats", []))
    probs = [p for p in reel_problems(placed) if "keep it 28-33s" not in p]
    assert probs == []


def test_line_count_must_match():
    import pytest
    with pytest.raises(ValueError):
        P.plan([BARS, BATTING], LINES, close=CLOSE)


def _retention_slides():
    board = {"colour": "#0a63a4", "groups": [{"label": "Pace", "players": [
        {"name": "J Bumrah", "value": 1.98}, {"name": "A Singh", "value": 1.89}, {"name": "T Boult", "value": 0.36},
        {"name": "D Chahar", "value": -0.56}]}]}
    return {"slides": [
        {"type": "hook", "hero": {"kind": "visual", "visual": "squad_board", "payload": board}},
        {"type": "card", "card": BARS},
        {"type": "card", "card": BATTING},
        {"type": "card", "card": GRID},
        {"type": "card", "card": {**CASES, "payload": {"cases": [
            {"name": "Rohit Sharma", "price": "₹16.30 crore", "for": "+18", "against": "−0.09"},
            {"name": "Deepak Chahar", "price": "₹9.25 crore", "for": "32", "against": "−0.56"},
            {"name": "Ryan Rickelton", "price": "₹1 crore", "for": "+84", "against": "little"}]}}},
        {"type": "card", "card": {"id": "fits", "visual": "gap_fits", "payload": {"rows": [
            {"label": "Middle-overs spin", "status": "gap", "now": "0.93", "playoff": "1.20", "like": [],
             "options": [{"name": "Karn Sharma", "value": "1.37"}]}]}}},
    ]}


def test_retention_preset_writes_the_script_from_the_cards():
    r = P.retention(_retention_slides(), "MI", "Mumbai")
    lines = r["lines"]
    assert lines[0] == "Bumrah added 1.98 wins since the 2025 auction. Arshdeep, 1.89."  # Arshdeep, not Singh
    assert lines[1] == "Only one other added more than a quarter of a win: Boult."      # named, so the ring lands on him
    assert r["spec"]["scenes"][1]["beats"] == [{"key": "T Boult", "anchor": {"line": 1, "word": 11}}]
    assert "Rohit at 16.3 crore" in lines[4] and lines[-1].endswith("Send this to a Mumbai fan.")
    assert [s["kind"] for s in r["spec"]["scenes"]] == ["hero", "squad_board", "metric_bars", "grid_heat",
                                                         "case_board", "gap_fits", "pick_one"]
    assert T.budget_problems(lines) == []
    placed = T.place(r["spec"], T.estimate(lines), hold=3.0)
    assert [p for p in reel_problems(placed) if "28-33s" not in p] == []


def test_names_are_said_whole_never_an_initial():
    fulls = ["Urvil Patel", "Arshdeep Singh", "Noor Ahmad"]
    assert P._say("Opener · U Patel", fulls) == "Urvil"      # Patel is common: the first name
    assert P._say("A Singh", fulls) == "Arshdeep"
    assert P._say("N Ahmad", fulls) == "Noor"
    assert P._say("S Khan", []) == "Khan"                    # no full name on the cards: the surname, not "S"
    r = P.retention(_retention_slides(), "MI", "Mumbai")
    import re
    assert not [w for x in r["lines"] for w in re.findall(r"\b[A-Z]\b", x) if w not in ("I", "A")]


def test_phase_said_in_words_and_the_hook_prefers_an_indian_player():
    r = P.retention(_retention_slides(), "MI", "Mumbai")
    assert "saves 11 runs every four overs at the death." in r["lines"][3]
    slides = _retention_slides()
    rows = slides["slides"][1]["card"]["payload"]["rows"]
    rows[0]["name"], rows[1]["name"] = "Trent Boult", "Arshdeep Singh"      # an overseas leader
    r2 = P.retention(slides, "MI", "Mumbai", overseas=["Trent Boult"])
    assert r2["lines"][0].startswith("Arshdeep added 1.89 wins")           # the Indian player opens (1.89 >= half of 1.98)


def test_sections_with_nothing_above_par_are_left_out():
    slides = _retention_slides()
    for s in slides["slides"]:
        if s.get("card", {}).get("id") == "batting":
            for r in s["card"]["payload"]["rows"]:
                r["value"] = -abs(r["value"])
    r = P.retention(slides, "MI", "Mumbai")
    assert not any("leads the batting" in x for x in r["lines"])
    assert "metric_bars" not in [s["kind"] for s in r["spec"]["scenes"][1:]]


def test_smat_round_one_team_per_beat_in_its_colour():
    import json
    from pathlib import Path
    rnd = json.loads((Path(__file__).resolve().parent / "fixtures/reel_timing/smat_round2_round.json").read_text())
    r = P.smat_round(rnd)
    scenes, lines = r["spec"]["scenes"], r["lines"]
    assert lines[0] == "Rajat Patidar: 135 not out, off 48 balls."
    assert [s["kind"] for s in scenes] == ["hero_card"] * 4 + ["pool_count", "pick_one"]
    assert [s.get("team") for s in scenes[:4]] == ["RCB", "MI", "CSK", "SRH"]           # the hero's side, then the next three
    assert [c["team"] for c in r["spec"]["chapters"]] == ["RCB", "MI", "CSK", "SRH"]     # one coloured segment a team
    assert scenes[0]["data"]["value"] == 135 and scenes[0]["data"]["done"] == "*"
    assert P._line_parts("4/12 in 3") == {"value": 4, "done": "/12", "detail": "in 3 overs"}
    placed = T.place(r["spec"], T.estimate(lines))
    assert T.budget_problems(lines) == [] and reel_problems(placed) == []
