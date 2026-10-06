"""Instagram debate posts (services/ig_posts): planner rules, contestedness, cards and the split verdict, on synthetic
fields (no database). Jev is stubbed: the rules must hold whatever it says."""
from services.ig_posts import angles as A
from services.ig_posts import cards as C
from services.ig_posts import planner, questions
from services.ig_posts.context import QuestionContext


def field(n=12, role="batter"):
    """Batter i: strike rate rises with i, balls per dismissal falls with i, RAA peaks in the middle."""
    rows = []
    for i in range(n):
        rows.append({"name": f"Player {chr(65 + i)} Batter{i}", "balls": 500, "metric_balls": 500, "innings_count": 20,
                     "strike_rate": 120 + 5 * i, "balls_per_dismissal": 40 - 2 * i, "average": 30 - i,
                     "raa_per_100": 10 - abs(i - 6), "impact_per_100": i, "wpa": 0.5 + 0.1 * (n - i),
                     "wpa_per_100": (0.5 + 0.1 * (n - i)) / 5, "boundary_percentage": 15 + i, "dot_percentage": 40 - i,
                     "control_percentage": 80 + (i % 5), "control_coverage_pct": 99.0, "sixes_per_100": 3 + i / 2})
    ctx = QuestionContext(db=None, role=role, fmt="T20", params={}, min_balls=100)
    ctx.__dict__["rows"] = rows  # cached_property: the field without a query
    return ctx


def test_planner_keeps_value_angles_and_family_cap(monkeypatch):
    ctx = field()
    # Jev loves the pace angles and calls the value ones irrelevant: the rules still put RAA/Impact and WPA in.
    monkeypatch.setattr(planner, "score", lambda q, role, angles: {a.id: (4.0 if a.family == "pace" else 0.2) for a in angles})
    p = planner.plan(ctx, "Who is the best finisher?", A.available("batter", "T20"))
    ids = [a.id for a in p["angles"]]
    assert {"wpa"} <= set(ids) and ({"raa", "impact"} & set(ids))
    assert sum(1 for a in p["angles"] if a.family == "pace") <= planner.MAX_PER_FAMILY
    assert planner.MIN_ANGLES <= len(ids) <= planner.MAX_ANGLES and p["by"] == "jev"


def test_planner_falls_back_without_jev(monkeypatch):
    monkeypatch.setattr(planner, "score", lambda q, role, angles: None)
    p = planner.plan(field(), "Who is the most complete batter?", A.available("batter", "T20"))
    assert p["by"] == "default" and [a.id for a in p["angles"]][:2] == ["raa", "wpa"]


def test_odi_has_no_primer_angles():
    assert not any(a.t20_only for a in A.available("batter", "ODI"))
    assert not any(a.t20_only for a in A.available("batter", "T20", ["The Hundred"]))


def test_contested_needs_different_leaders():
    ctx = field()
    chosen = [A.by_id("batter", "sr"), A.by_id("batter", "bpd"), A.by_id("batter", "raa")]
    c = questions.contested(ctx, chosen)
    assert c["contested"] and c["distinct"] == 3  # fastest, hardest to dismiss and best RAA are three players
    one = questions.contested(ctx, [A.by_id("batter", "sr"), A.by_id("batter", "boundary")])
    assert not one["contested"]  # the same player leads both


def test_scorecard_verdict_is_split_and_names_leaders():
    ctx = field()
    chosen = [A.by_id("batter", a) for a in ("raa", "sr", "bpd", "wpa")]
    card = C.scorecard(ctx, chosen, "sample")
    v = card["payload"]["verdict"]
    assert "leads overall" in v and "scores fastest" in v and "hardest to dismiss" in v
    # Every cell's percentile is from the whole field; leaders are ringed.
    rows = card["payload"]["rows"]
    assert all(0 <= p <= 100 for r in rows for p in r["pct"].values())
    assert any(r["leader"] for r in rows)


def test_bars_and_scatter_titles_come_from_the_rows():
    ctx = field()
    sr = A.by_id("batter", "sr")
    bars = C.bars(ctx, sr, "sample")
    assert bars["title"] == "Player L Batter11 leads on strike rate: 175.0"
    sc = C.scatter(ctx, sr, A.by_id("batter", "bpd"), "sample", A.by_id("batter", "raa"))
    assert sc["visual"] == "scatter_plus" and len(sc["payload"]["points"]) == 12
    assert sum(1 for p in sc["payload"]["points"] if p["label"]) == 6


def test_candidates_are_questions_without_results():
    qs = questions.candidates()
    assert len({q.key for q in qs}) == len(qs) and len(qs) > 30
    import re

    # A hook names no result: no numbers beyond formats ("T20Is") and the scope's years.
    bare = lambda t: re.sub(r"T20Is?|\b(19|20)\d\d\b", "", t)  # noqa: E731
    assert all(q.text.endswith("?") and not re.search(r"\d", bare(q.text)) for q in qs)


def test_match_day_helpers():
    from services.ig_posts import match, records

    assert [match.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22)] == ["1st", "2nd", "3rd", "4th", "11th", "12th",
                                                                         "13th", "21st", "22nd"]
    story = {"chapters": [{"cards": [{"id": "h2h"}, {"id": "key-battles"}, {"id": "par"}, {"id": "xis"}]}]}
    assert match.pick_preview_cards(story) == ["par", "key-battles"]  # in PREVIEW_CARDS order, others left out
    # A race line runs from (0, 0) to the innings that reached the target, and no further.
    rows = [("A", 30, 400), ("A", 60, 1010), ("A", 90, 1100), ("B", 50, 990)]
    assert records._cut(rows, 1000) == {"A": [(0, 0), (30, 400), (60, 1010)], "B": [(0, 0), (50, 990)]}


def test_recap_window_runs_to_the_next_meeting_or_three_days():
    from datetime import date, datetime, timezone

    from services.ig_backlog import RECAP_DAYS, recap_post_by

    fixtures = [{"team1": "West Indies", "team2": "India", "start_utc": "2026-10-09T13:30:00+00:00"},
                {"team1": "India", "team2": "Australia", "start_utc": "2026-10-08T13:30:00+00:00"}]
    # Next meeting of the same sides (either way round), not the other fixture.
    assert recap_post_by(date(2026, 10, 6), "India", "West Indies", fixtures) == datetime(2026, 10, 9, 13, 30, tzinfo=timezone.utc)
    # No next meeting: the end of the third day after the match.
    end = recap_post_by(date(2026, 10, 6), "India", "Pakistan", fixtures)
    assert end.date() == date(2026, 10, 6 + RECAP_DAYS) and end.hour == 23


def test_trend_mentions_need_a_full_name_or_a_unique_surname():
    from services.ig_posts import trends

    players = {"Shreyas Iyer": {}, "Ishan Kishan": {}, "Abhishek Sharma": {}, "Rohit Sharma": {}, "Tilak Varma": {}}
    titles = [{"source": "Cricinfo", "title": "Kishan and Bumrah ride roughshod"},
              {"source": "Reddit", "title": "Sharma smashes another fifty"},          # two Sharmas: nobody
              {"source": "News", "title": "Shreyas Iyer 'ecstatic' after win"},
              {"source": "News", "title": "Varma backed for No. 3"}]
    named = trends.mentions(titles, players)
    assert set(named) == {"Ishan Kishan", "Shreyas Iyer", "Tilak Varma"}


def test_myth_spec_builds_from_the_result_file():
    from services.ig_posts import myths

    built = myths.build({"title": "Does one bad over break Varun Chakravarthy?", "status": "published"})
    kinds = [s["type"] for s in built["slides"]]
    assert kinds[:2] == ["hook", "text"] and kinds[-2:] == ["verdict", "end"] and kinds.count("card") >= 3
    forest = next(s["card"] for s in built["slides"] if s.get("card", {}).get("visual") == "forest")
    assert forest["title"].startswith("1 of 5 tests finds")  # the pooled-spinners test is the clear one
    assert myths.build({"title": "Does one bad over break Varun Chakravarthy?", "status": "draft"}) is None


def test_reel_is_optional_without_ffmpeg(monkeypatch, tmp_path):
    import shutil

    from services import ig_slides

    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert ig_slides.make_reel("x", [tmp_path / "1.png", tmp_path / "2.png"]) is None  # the carousel is unaffected
    total = ig_slides.REEL_HOOK + 3 * ig_slides.REEL_SLIDE + ig_slides.REEL_END
    assert 10 < total < 60  # a five-slide post is a sensible Reel length


def test_comment_kit_drops_lines_that_need_their_chart():
    from services import ig_plan

    assert ig_plan.NEEDS_CHART.match("1 of 5 tests finds a clear effect")
    assert ig_plan.NEEDS_CHART.match("Only 2 of 93 beat Kohli on both strike rate and average")
    assert not ig_plan.NEEDS_CHART.match("Jasprit Bumrah saves the most at the death: +33 runs per 100 balls")
    assert ig_plan.SAME_AS_FIELD.search("Kohli hits 20% of boundaries to midwicket (field: 20%)")
    assert not ig_plan.SAME_AS_FIELD.search("Iyer hits 27% of boundaries to midwicket (field: 18%)")
