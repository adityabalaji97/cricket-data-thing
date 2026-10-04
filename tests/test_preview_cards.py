"""Story-style preview cards (services/preview_cards): titles, sample rules, ordering, formats."""
from datetime import date
from types import SimpleNamespace

from services.preview_cards import build_story
from services.preview_cards.context import PreviewContext
from services.preview_cards.copy import leader_line, plural, span
from services.preview_cards.spec import Card, CardSpec, Info, SampleRule


def _ctx(venue_matches=28, bat=15, chase=13, h2h=(1, 4, 0), fmt="T20", phases=True):
    ctx = PreviewContext(db=None, venue="Wankhede Stadium, Mumbai", team1="Mumbai Indians", team2="Chennai Super Kings",
                         fmt=fmt, start=date(2022, 1, 1), end=date(2026, 10, 4), team1_short="MI", team2_short="CSK")
    record = {"total_matches": venue_matches, "batting_first_wins": bat, "batting_second_wins": chase,
              "lowest_total_defended": 169, "highest_total_chased": 243, "average_first_innings": 194,
              "average_winning_score": 209, "average_chasing_score": 181, "average_second_innings": 178}
    expect = {"venue": {"total_matches": venue_matches, "avg_winning_score": 215.4, "avg_first_innings": 194},
              "winning_phases": {"batting_first": {"powerplay": 62, "middle": 84, "death": 63, "total": 209},
                                 "chasing": {"powerplay": 57, "middle": 75, "death": 48, "total": 181}} if phases else {}}
    history = {
        "h2h_stats": {"team1_wins": h2h[0], "team2_wins": h2h[1], "draws": h2h[2]},
        "venue_results": [{"winner": "MI", "won_batting_first": False}, {"winner": "CSK", "won_batting_first": False},
                          {"winner": "RR", "won_batting_first": True}, {"winner": "-", "won_batting_first": None}],
        "team1_results": [{"winner": "MI"}, {"winner": "MI"}, {"winner": "RCB"}],
        "team2_results": [{"winner": "CSK"}, {"winner": "KKR"}, {"winner": "KKR"}],
    }
    # cached_property values can be preset on the instance.
    ctx.__dict__.update(venue_record=record, history=history, preview={"expect": expect})
    return ctx


def _cards(story):
    return {c["id"]: c for ch in story["chapters"] for c in ch["cards"]}


def test_titles_state_the_finding():
    cards = _cards(build_story(_ctx()))
    assert cards["par"]["title"] == "Par here is about 215"
    assert cards["results"]["title"] == "Sides batting first have won 15 of 28 here"
    assert cards["winning-phases"]["title"] == "Winning sides here cut loose at the death"
    assert cards["totals"]["title"] == "169 has been defended here, and 243 chased"
    assert cards["head-to-head"]["title"] == "CSK lead 4–1 in their last 5 meetings"
    assert cards["form"]["title"] == "MI come in with 2 wins from their last 5"
    # A no-result is not counted as a chase or a defence.
    assert cards["recent-results"]["title"] == "Chasing sides won 2 of the last 3 here"


def test_sample_line_and_small_sample_flag():
    cards = _cards(build_story(_ctx()))
    assert cards["results"]["sample"] == "28 matches at Wankhede Stadium · 2022–26"
    assert not cards["results"]["small_sample"]
    assert cards["head-to-head"]["small_sample"]  # 5 meetings < 15


def test_thin_ground_drops_ground_cards_but_keeps_team_cards():
    story = build_story(_ctx(venue_matches=2, bat=1, chase=1, phases=False))
    cards = _cards(story)
    assert "results" not in cards and "par" not in cards and "totals" not in cards
    assert "head-to-head" in cards


def test_chapters_keep_their_order_and_cards_rank_inside():
    story = build_story(_ctx())
    assert [c["id"] for c in story["chapters"]] == ["glance", "ground", "teams"]
    ground = [c["relevance"] for c in story["chapters"][1]["cards"]]
    assert ground == sorted(ground, reverse=True)


def test_cards_carry_info_and_query_links():
    cards = _cards(build_story(_ctx()))
    assert cards["results"]["info"]["what"]
    assert cards["results"]["query_url"].startswith("https://hindsightcricket.com/query?")
    assert "query_mode=team_innings" in cards["results"]["query_url"]


def test_format_and_failure_handling():
    def boom(ctx):
        raise RuntimeError("nope")

    t20_only = CardSpec("x", "ground", "?", lambda ctx: Card("x", "ground", "stat", "t", "s", {}, 50, Info("w")),
                        formats=("T20",))
    story = build_story(_ctx(fmt="ODI"), registry=[t20_only, CardSpec("b", "ground", "?", boom)])
    assert story["chapters"] == []  # T20-only card skipped for ODI; the failing card left out


def test_copy_helpers():
    assert plural(1, "match") == "1 match" and plural(3, "match") == "3 matches"
    assert span(date(2022, 1, 1), date(2026, 10, 4)) == "2022–26"
    assert leader_line("MI", 2, "CSK", 2) == ("Level at 2–2", None)
    assert leader_line("MI", 1, "CSK", 4) == ("CSK lead 4–1", "CSK")


def test_sample_rule_hides_below_floor():
    spec = CardSpec("x", "ground", "?", lambda ctx: Card("x", "ground", "stat", "t", "s", {}, 2, Info("w")),
                    sample=SampleRule(hide_below=3))
    assert spec.make(SimpleNamespace(fmt="T20")) is None
