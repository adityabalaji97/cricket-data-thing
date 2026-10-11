"""Reel v2 (services/ig_reel_v2.py): beats, the script guard, captions, the A/B. No database, no network."""
from datetime import date

from services import ig_reel_v2 as R

SLIDES = [
    {"type": "hook", "text": "Kuldeep's 17th went for 24 and swung the chase."},
    {"type": "card", "card": {"id": "bowling-plan", "visual": "bowling_plan", "title": "By the 17th, India had 4 pace overs left",
                              "help": "Spin bowled 3 of the last 4 overs", "payload": {"rows": [{"left": 1}]}}},
    {"type": "card", "card": {"id": "set-v-new", "visual": "deep_compare", "kicker": "The deeper cut",
                              "title": "At the death, spin costs 11.1 an over to set batters and pace 11.8",
                              "payload": {"rows": [{"subject": 11.1, "field": 11.8}]}}},
    {"type": "card", "card": {"id": "scorecard-1", "visual": "innings_scorecard", "title": "India 249/5", "payload": {}}},
    {"type": "card", "card": {"id": "mix", "visual": "deep_compare", "title": "Teams defending 200 bowl spin in 21% of death overs",
                              "payload": {"rows": [{"subject": 75, "field": 21}]}}},
    {"type": "end", "heading": "Every ball"},
]


def test_beats_open_on_the_payoff_and_skip_scorecards():
    bs = R.beats(SLIDES)
    assert [n for n, _ in bs] == [2, 3, 5]  # the bowling plan first, the deeper cut, then the next card
    assert all(c["visual"] != "innings_scorecard" for _, c in bs)


def test_guard_rejects_numbers_not_on_the_cards():
    bs = R.beats(SLIDES)
    ok = R.allowed(SLIDES[0]["text"], bs)
    good = {"hook": "Kuldeep's 17th went for 24.", "lines": [
        "India still had 4 pace overs left by the 17th, and spin bowled 3 of the last 4.",
        "At the death, spin costs 11.1 an over to set batters, pace 11.8.",
        "Teams defending 200 bowl spin in 21% of death overs. India: 75%. Your call?"]}
    assert R.guard(good, ok, 3) is None
    bad = {**good, "lines": [*good["lines"][:2], "Teams defending 200 bowl spin in 30% of death overs."]}
    assert "30" in R.guard(bad, ok, 3)
    assert R.guard({**good, "lines": good["lines"][:2]}, ok, 3) == "shape"


def test_template_is_built_from_the_titles():
    t = R.template(SLIDES[0]["text"], R.beats(SLIDES))
    assert t["hook"].startswith("Kuldeep's 17th") and len(t["lines"]) == 3


def test_captions_cover_the_line_in_order():
    chunks = R.caption_chunks("one two three four five six seven", 2.0, 3.5)
    assert chunks[0][0] == 2.0 and abs(chunks[-1][1] - 5.5) < 0.01
    assert [c[2] for c in chunks] == ["one two three", "four five six", "seven"]
    assert all(a < b for a, b, _ in chunks)


def test_variant_ab_and_eligibility(monkeypatch):
    monkeypatch.delenv("REEL_V2", raising=False)
    assert R.variant("recap", date(2026, 10, 12)) == "v1"  # off unless switched on
    monkeypatch.setenv("REEL_V2", "1")
    even, odd = date(2026, 10, 12), date(2026, 10, 13)
    assert {R.variant("recap", even), R.variant("recap", odd)} == {"v1", "v2"}
    assert R.variant("preview", even) == "v1"
    monkeypatch.setenv("REEL_AB", "0")
    assert R.variant("recap", odd) == "v2"
