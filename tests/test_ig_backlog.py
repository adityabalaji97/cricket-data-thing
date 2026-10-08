"""Instagram backlog (services/ig_backlog.py) and the headline phrases it relies on (services/snapshots.py)."""
from datetime import date, timedelta

from services import ig_backlog
from services.snapshots import _filter_phrase


def _post(key, pillar, players):
    return {"key": key, "pillar": pillar, "players": players, "fact": {"title": key}, "warnings": []}


def test_calendar_follows_the_week_and_keeps_players_apart():
    made = ([_post(f"d{i}", "debate", ["Virat Kohli"] if i < 3 else [f"B{i}"]) for i in range(10)]
            + [_post(f"m{i}", "myth", [f"M{i}"]) for i in range(5)]
            + [_post(f"w{i}", "weird", ["Virat Kohli"] if i == 0 else [f"W{i}"]) for i in range(5)])
    start = date(2026, 10, 12)  # a Monday
    calendar, bench = ig_backlog.schedule(made, start, days=14)
    assert [e["pillar"] for e in calendar[:7]] == ig_backlog.WEEK
    assert all(e["post"] is None for e in calendar if e["pillar"] in ("play", "reactive"))
    posts = [e["post"] for e in calendar if e["post"]]
    # No player twice within any SPREAD consecutive scheduled posts.
    for i in range(len(posts)):
        window = posts[i:i + ig_backlog.SPREAD]
        names = [p for post in window for p in post["players"]]
        assert len(names) == len(set(names)), [post["key"] for post in window]
    assert {p["key"] for p in posts} | {b["key"] for b in bench} == {m["key"] for m in made}
    assert calendar[0]["date"] == start and calendar[-1]["date"] == start + timedelta(days=13)


def test_every_curated_idea_has_a_pillar_and_a_unique_key():
    keys = [i["key"] for i in ig_backlog.IDEAS]
    assert len(keys) == len(set(keys))
    assert {i["pillar"] for i in ig_backlog.IDEAS} <= set(ig_backlog.EVERGREEN)
    for item in ig_backlog.IDEAS:
        assert item.get("planned") or item.get("idea") or item.get("note_id"), item["key"]


def test_headlines_say_which_innings_and_matches():
    assert _filter_phrase({"is_chase": True}) == " while chasing"
    assert _filter_phrase({"innings": 1}) == " batting first"
    assert _filter_phrase({"top_teams": 10, "include_international": True}) == " in matches between the top 10 teams"
    # top_teams does nothing without include_international (query_builder_v2), so the headline must not claim it.
    assert _filter_phrase({"top_teams": 10}) == ""


def test_an_empty_pillar_borrows_from_another():
    made = [_post(f"d{i}", "debate", [f"B{i}"]) for i in range(6)] + [_post(f"w{i}", "weird", [f"W{i}"]) for i in range(3)]
    calendar, _ = ig_backlog.schedule(made, date(2026, 10, 12), days=7)  # Mon..Sun, no myth posts at all
    wednesday = calendar[2]
    assert wednesday["pillar"] == "myth" and wednesday["post"] is not None


def test_reorder_leads_with_the_format_on_and_alternates_between_series(monkeypatch):
    from datetime import date

    from services import ig_backlog, ig_season

    rows = [
        {"id": 1, "angle_key": "ig:debate-odiwc-batter-all", "pillar": "debate", "planned_for": date(2026, 10, 12), "facts": {}, "kind": "debate"},
        {"id": 2, "angle_key": "ig:debate-ipl23-batter-death", "pillar": "debate", "planned_for": date(2026, 10, 14), "facts": {}, "kind": "debate"},
        {"id": 3, "angle_key": "ig:odi-fastest-5000", "pillar": "weird", "planned_for": date(2026, 10, 18), "facts": {}, "kind": "weird"},
        {"id": 4, "angle_key": "ig:ipl-fastest-1000-balls", "pillar": "weird", "planned_for": date(2026, 10, 19), "facts": {}, "kind": "weird"},
    ]
    monkeypatch.setattr(ig_backlog, "_rows", lambda db, where, params: [dict(r) for r in rows])
    monkeypatch.setattr(ig_season, "major_series", lambda db, day: [])
    moves = {k: new for k, _old, new in ig_backlog.reorder(None, date(2026, 10, 9), 30, dry_run=True)}
    # T20 week (India v WI): both T20 posts take 12 and 14 Oct, format before pillar. 18 Oct has no series, so the
    # formats take turns (ODI after T20): the ODI record, its pillar. 19 Oct gets what's left.
    assert moves["ig:debate-ipl23-batter-death"] == date(2026, 10, 12)
    assert moves["ig:ipl-fastest-1000-balls"] == date(2026, 10, 14)
    assert "ig:odi-fastest-5000" not in moves  # already on 18 Oct
    assert moves["ig:debate-odiwc-batter-all"] == date(2026, 10, 19)
