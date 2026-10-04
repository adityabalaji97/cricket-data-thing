"""Story-style preview cards (services/preview_cards): titles, sample rules, ordering, formats."""
from datetime import date
from types import SimpleNamespace

from services.preview_cards import build_story
from services.preview_cards.context import GroundMatch, PreviewContext
from services.preview_cards.copy import leader_line, plural, span
from services.preview_cards.spec import Card, CardSpec, Info, SampleRule
from services.preview_cards.stats import wilson, within_noise


def _innings(runs, won, full=True, toss_bat=None, pp=60, mid=80, death=None):
    death = runs - pp - mid if death is None else death
    return {"runs": runs, "wins": int(won), "losses": int(not won), "full_length": int(full),
            "pct_batting_side_won_toss": toss_bat, "powerplay_runs": pp, "middle_runs": mid, "death_runs": death}


def _match(i, year, first_runs, second_runs, chase_won, full=True, no_result=False, toss_chose_field=True):
    first = _innings(first_runs, not chase_won, full, toss_bat=0 if toss_chose_field else 100)
    second = _innings(second_runs, chase_won)
    if no_result:
        first.update(wins=0, losses=0)
    return GroundMatch(id=str(i), year=year, first=first, second=second)


def _ground(n_bat=15, n_chase=13, years=(2022, 2023, 2024, 2025, 2026)):
    out = []
    for i in range(n_bat):
        out.append(_match(i, years[i % len(years)], 190 + i, 170, chase_won=False))
    for i in range(n_chase):
        out.append(_match(100 + i, years[i % len(years)], 180, 200 + i, chase_won=True))
    return out


def _ctx(ground=None, h2h=(1, 4, 0), fmt="T20", par_series=((2024, 189, 7), (2025, 180, 7), (2026, 212, 7)),
         international=False):
    ctx = PreviewContext(db=None, venue="Wankhede Stadium, Mumbai", team1="Mumbai Indians", team2="Chennai Super Kings",
                         fmt=fmt, start=date(2022, 1, 1), end=date(2026, 10, 4), team1_short="MI", team2_short="CSK")
    history = {
        "h2h_stats": {"team1_wins": h2h[0], "team2_wins": h2h[1], "draws": h2h[2]},
        "venue_results": [{"winner": "MI", "won_batting_first": False}, {"winner": "CSK", "won_batting_first": False},
                          {"winner": "RR", "won_batting_first": True}, {"winner": "-", "won_batting_first": None}],
        "team1_results": [{"winner": "MI"}, {"winner": "MI"}, {"winner": "RCB"}],
        "team2_results": [{"winner": "CSK"}, {"winner": "KKR"}, {"winner": "KKR"}],
    }
    primer = None
    if par_series:
        primer = {"competition": "T20Is" if international else "IPL", "where": "in India" if international else "here",
                  "international": international,
                  "series": [{"year": y, "par": p, "n": n} for y, p, n in par_series]}
    # cached_property values can be preset on the instance.
    ctx.__dict__.update(
        history=history, primer_par=primer if fmt == "T20" else None,
        ground_matches=_ground() if ground is None else ground,
        scope={"leagues": ["IPL"], "include_international": True, "top_teams": 20},
    )
    return ctx


def _cards(story):
    return {c["id"]: c for ch in story["chapters"] for c in ch["cards"]}


def test_titles_state_the_finding():
    cards = _cards(build_story(_ctx()))
    assert cards["par"]["title"] == "Par here is about 212"
    assert cards["par"]["payload"]["caption"] == "Up from 189 in 2024."
    assert cards["results"]["title"] == "Batting first is no clear edge here: 15 of 28 won"
    assert cards["winning-phases"]["title"] == "Winning sides here cut loose at the death"
    assert cards["totals"]["title"] == "190 has been defended here, and 212 chased"
    assert cards["head-to-head"]["title"] == "CSK lead 4–1 in their last 5 meetings"
    assert cards["form"]["title"] == "MI come in with 2 wins from their last 5"
    # A no-result counts towards neither side, and the title counts all the matches shown.
    assert cards["recent-results"]["title"] == "Chasing sides won 2 of the last 4 here"


def test_ground_cards_count_the_same_matches():
    cards = _cards(build_story(_ctx()))
    assert cards["results"]["payload"]["decided"] == 28
    assert cards["totals"]["payload"]["total_matches"] == 28
    assert cards["winning-phases"]["n"] == 28
    assert cards["results"]["sample"] == "28 decided matches at Wankhede Stadium · 2022–26"


def test_rain_shortened_and_no_result_matches():
    ground = _ground() + [_match(900, 2026, 90, 91, chase_won=True, full=False),
                          _match(901, 2026, 120, 0, chase_won=False, no_result=True)]
    cards = _cards(build_story(_ctx(ground=ground)))
    assert cards["results"]["payload"]["decided"] == 29       # the rain-cut chase still has a winner
    assert cards["totals"]["payload"]["lowest_total_defended"] == 190  # but a 90 in 8 overs is no benchmark
    assert cards["totals"]["payload"]["total_matches"] == 29  # the no-result ran its full first innings


def test_chase_record_carries_its_likely_range():
    lo, hi = wilson(32, 59)
    assert (round(lo * 100), round(hi * 100)) == (42, 66)  # the audit's Wankhede figure
    assert within_noise(32, 59) and not within_noise(45, 59)
    card = _cards(build_story(_ctx(ground=_ground(n_bat=5, n_chase=25))))["results"]
    assert card["title"] == "Chasing sides win more here: 25 of 30"
    assert not card["payload"]["within_noise"]
    assert card["payload"]["notes"] == ["Since 2025: chasing sides won 10 of 12.",
                                        "Toss winners chose to chase 30 of 30 times."]


def test_thin_ground_keeps_par_but_drops_ground_records():
    cards = _cards(build_story(_ctx(ground=_ground(n_bat=4, n_chase=3))))
    assert "results" not in cards and "totals" not in cards and "winning-phases" not in cards
    assert "par" in cards and not cards["par"]["small_sample"]  # Primer par is shrunk, not raw
    assert "head-to-head" in cards


def test_international_par_is_by_country():
    cards = _cards(build_story(_ctx(international=True)))
    assert cards["par"]["title"] == "Par for a T20I in India is about 212"
    assert cards["par"]["sample"] == "T20Is in India · 2026 · T20 Primer par"


def test_odi_par_is_the_average_complete_first_innings():
    cards = _cards(build_story(_ctx(fmt="ODI")))
    assert cards["par"]["title"].startswith("Par here is about ")
    assert cards["par"]["sample"] == "28 complete first innings at Wankhede Stadium · 2022–26"


def test_only_meeting_copy():
    assert _cards(build_story(_ctx(h2h=(1, 0, 0))))["head-to-head"]["title"] == "MI won their only meeting"
    assert _cards(build_story(_ctx(h2h=(0, 0, 1))))["head-to-head"]["title"] == "Their only meeting had no winner"


def test_chapters_keep_their_order_and_cards_rank_inside():
    story = build_story(_ctx())
    assert [c["id"] for c in story["chapters"]] == ["glance", "ground", "teams"]
    ground = [c["relevance"] for c in story["chapters"][1]["cards"]]
    assert ground == sorted(ground, reverse=True)


def test_data_links_carry_the_cards_scope():
    url = _cards(build_story(_ctx()))["results"]["query_url"]
    assert url.startswith("https://hindsightcricket.com/query?")
    assert "query_mode=team_innings" in url
    assert "leagues=IPL" in url and "include_international=true" in url and "top_teams=20" in url


def test_format_and_failure_handling():
    def boom(ctx):
        raise RuntimeError("nope")

    t20_only = CardSpec("x", "ground", "?", lambda ctx: Card("x", "ground", "stat", "t", "s", {}, 50, Info("w")),
                        formats=("T20",))
    story = build_story(_ctx(fmt="ODI"), registry=[t20_only, CardSpec("b", "ground", "?", boom)])
    assert story["chapters"] == []  # T20-only card skipped for ODI; the failing card left out


def test_copy_helpers():
    assert plural(1, "match") == "1 match" and plural(3, "match") == "3 matches"
    assert plural(2, "decided match") == "2 decided matches" and plural(5, "complete first innings").endswith("innings")
    assert span(date(2022, 1, 1), date(2026, 10, 4)) == "2022–26"
    assert leader_line("MI", 2, "CSK", 2) == ("Level at 2–2", None)
    assert leader_line("MI", 1, "CSK", 4) == ("CSK lead 4–1", "CSK")


def test_sample_rule_hides_below_floor():
    spec = CardSpec("x", "ground", "?", lambda ctx: Card("x", "ground", "stat", "t", "s", {}, 2, Info("w")),
                    sample=SampleRule(hide_below=3))
    assert spec.make(SimpleNamespace(fmt="T20")) is None
