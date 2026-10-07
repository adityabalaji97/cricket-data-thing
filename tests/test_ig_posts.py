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
    story = {"chapters": [{"id": "glance", "cards": [{"id": "glance"}]},
                          {"id": "ground", "cards": [{"id": "par"}, {"id": "where-won"}]},
                          {"id": "teams", "cards": []},
                          {"id": "players", "cards": [{"id": "key-battles"}, {"id": "death-hitters"}]},
                          {"id": "more", "cards": [{"id": "ask"}]}]}
    assert match.chapter_leads(story) == ["glance", "par", "key-battles"]  # leads in order; no empty chapter, no links
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


def test_search_titles_use_searched_wording_and_honest_years(monkeypatch):
    from services import search_titles as T

    fake = {"india vs west indies 2nd t20": ("india vs west indies 2nd t20 tickets", "india vs west indies 2nd t20",
                                             "india vs west indies 2nd t20 2026", "india vs west indies 2nd t20 live score"),
            "best finisher in ipl": ("best finisher in ipl", "best finisher in ipl 2026", "best finisher in ipl history")}
    monkeypatch.setattr(T, "suggestions", lambda seed: fake.get(seed.lower(), ()))
    assert T.match_title("India", "West Indies", "T20", 2, 2026, "preview", "par about 185") == \
        "India vs West Indies 2nd T20 2026 preview: Par about 185"
    # Data since 2023 never gets "2026" in its title, even though people search it.
    assert T.debate_title("finisher", "IPL", "since 2023", ["Impact", "strike rate"]) == \
        "Best finisher in IPL since 2023: Impact and strike rate compared"
    assert T.best_phrase("india vs west indies 2nd t20", years=[2026]) == "india vs west indies 2nd t20"  # no tickets
    assert T.best_phrase("india vs west indies 2nd t20", years=[2026], prefer=["2026"]) == "india vs west indies 2nd t20 2026"


def test_note_tables_and_youtube_copy():
    from services import ig_notes

    card = {"visual": "metric_bars", "title": "X leads", "payload": {"metric": {"label": "strike rate", "format": "dec1"},
            "rows": [{"name": "A B", "value": 150.0}, {"name": "C D", "value": 140.0}]}}
    assert ig_notes.card_table(card).splitlines()[:3] == ["| # | Player | Strike rate |", "|---|---|---|", "| 1 | A B | 150.0 |"]
    yt = ig_notes.youtube_copy({"kicker": "IPL"}, "Who?\n\nAnswer.\n\nFree ball-by-ball cricket stats: link in bio.\n.\n#a #b",
                               "Best finisher in IPL since 2023: Impact compared")
    assert yt["title"].endswith("#shorts") and len(yt["title"]) <= 100
    assert "link in bio" not in yt["description"] and yt["description"].endswith("#cricket #IPL #shorts")


def test_innings_scorecards_one_card_per_innings_batting_with_strike_rate(monkeypatch):
    import services.match_scorecard as msc
    from services.ig_posts import match

    bat = lambda n, r, b, imp, no=False: {"name": n, "runs": r, "balls": b, "strike_rate": round(100 * r / b), "impact": imp,  # noqa: E731
                                          "not_out": no, "fours": 0, "sixes": 0}
    sc = {"match": {"teams": [{"name": "India", "accent": "#5b8def"}, {"name": "West Indies", "accent": "#f0b429"}]},
          "innings": [{"innings": 1, "batting_team": "West Indies", "bowling_team": "India",
                       "score": {"runs": 171, "wickets": 10, "overs": "19.1"},
                       "batting": [bat("Shai Hope", 52, 37, 3.6), bat("Sherfane Rutherford", 56, 34, 25.5)],
                       "bowling": [{"name": "Axar Patel", "figures": "3.1-0-26", "wickets": 2, "impact": 21.2}]},
                      {"innings": 2, "batting_team": "India", "bowling_team": "West Indies",
                       "score": {"runs": 172, "wickets": 2, "overs": "14.4"},
                       "batting": [bat("Shreyas Iyer", 102, 43, 55.0, True)],
                       "bowling": [{"name": "Akeal Hosein", "figures": "4.0-0-37", "wickets": 1, "impact": 2.3}]}]}
    monkeypatch.setattr(msc, "get_match_scorecard_service", lambda match_id, min_balls, db: sc)
    cards = match.innings_scorecards(None, "1", "1st T20I")
    assert [c["id"] for c in cards] == ["scorecard-1", "scorecard-2"]
    assert cards[0]["title"] == "West Indies 171 all out: Rutherford's 56 led, +25.5 Impact"
    assert cards[1]["title"].startswith("India 172/2: Iyer's 102 led")
    p = cards[0]["payload"]
    assert [r["name"] for r in p["batting"]] == ["Shai Hope", "Sherfane Rutherford"]  # batting order kept
    assert p["batting"][0] == {"name": "Shai Hope", "runs": 52, "balls": 37, "sr": 141, "impact": 3.6, "not_out": False}
    assert p["bowling"][0] == {"name": "Axar Patel", "figures": "3.1-0-26", "wickets": 2, "impact": 21.2}
    assert p["has_impact"] and p["accent"] == "#f0b429" and cards[1]["payload"]["batting"][0]["not_out"]
