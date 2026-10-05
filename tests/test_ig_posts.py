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
