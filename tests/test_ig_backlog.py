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
