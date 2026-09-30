"""Content rules (services/content_rules.py) and pack selection (services/content_packs.py)."""
from datetime import date, datetime, timezone

from services import content_rules
from services.content_packs import choose
from services.records import ordinal

FACTS = [{"runs": 121, "balls": 43}, {"n": 5210, "since": 2015, "rank": 3}]
GOOD = "Dasun Shanaka's 121 off 43 v St Lucia Kings is the 3rd-highest CPL score since 2015"


def test_good_title_passes():
    errors, warnings = content_rules.check_title(GOOD, FACTS, "Dasun Shanaka")
    assert errors == [] and warnings == []


def test_question_title_is_refused():
    errors, _ = content_rules.check_title("Is Dasun Shanaka's 121 off 43 the best CPL knock since 2015?", FACTS)
    assert any("question" in e for e in errors)


def test_title_without_a_number_is_refused():
    errors, _ = content_rules.check_title("Dasun Shanaka played one of the great CPL innings against St Lucia Kings", FACTS)
    assert any("no number" in e for e in errors)


def test_number_not_in_facts_is_refused():
    errors, _ = content_rules.check_title(GOOD.replace("121", "131"), FACTS)
    assert any("131" in e for e in errors)


def test_thousands_separator_is_one_number():
    errors, _ = content_rules.check_title("Dasun Shanaka's 121 off 43 ranks 3rd of 5,210 CPL innings since 2015", FACTS)
    assert errors == []


def test_warnings_for_short_shouty_clickbait_and_wrong_lead():
    _, warnings = content_rules.check_title("INSANE 121 off 43!!", FACTS, "Dasun Shanaka")
    text = " ".join(warnings)
    assert "Short title" in text and "ALL CAPS" in text and "Clickbait" in text and "lead with" in text


def test_scope_top_internationals_and_main_leagues_only():
    base = {"gender": "male", "match_type": "international", "competition": "ODI"}
    assert content_rules.in_scope({**base, "team1": "India", "team2": "West Indies"})
    assert not content_rules.in_scope({**base, "team1": "India", "team2": "Nepal"})
    assert content_rules.in_scope({"gender": "male", "match_type": "league", "competition": "Indian Premier League"})
    assert not content_rules.in_scope({"gender": "male", "match_type": "league", "competition": "Major Clubs T20"})
    assert not content_rules.in_scope({**base, "gender": "female", "team1": "India", "team2": "Australia"})


def test_post_by_gives_three_days_but_never_less_than_a_day():
    now = datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc)
    assert content_rules.post_by(date(2026, 9, 29), now) == datetime(2026, 10, 2, 18, 0, tzinfo=timezone.utc)
    assert content_rules.post_by(date(2026, 9, 1), now) == datetime(2026, 10, 1, 18, 0, tzinfo=timezone.utc)


def test_ordinals():
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101)] == \
        ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "101st"]


def test_choose_keeps_series_posts_and_ranks_the_rest_without_jev(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    match = {"team1": "India", "team2": "Afghanistan", "competition": "T20I", "date": date(2026, 9, 17)}
    facts = [
        {"id": "a", "text": "a", "title": "a", "weight": 5.0, "series": True},
        {"id": "b", "text": "b", "title": "b", "weight": 9.0},
        {"id": "c", "text": "c", "title": "c", "weight": 2.0},   # below the fallback floor
        {"id": "d", "text": "d", "title": "d", "weight": 6.0},
        {"id": "e", "text": "e", "title": "e", "weight": 4.5},
    ]
    assert [f["id"] for f in choose(facts, match, per_match=2)] == ["a", "b", "d"]
