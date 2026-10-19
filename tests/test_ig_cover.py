from services import ig_cover, social_rules


def bars(highlight_at=5):
    rows = [{"name": f"P{i}", "value": 10 - i, "highlight": i == highlight_at} for i in range(7)]
    return {"type": "card", "card": {"visual": "metric_bars", "payload": {"metric": {"format": "signed0", "label": "x"}, "rows": rows}}}


def test_hero_keeps_the_highlighted_row(monkeypatch):
    monkeypatch.setenv("COVER_HERO", "on")
    out = ig_cover.with_hero([{"type": "hook", "text": "t"}, bars()], "t")
    hero = out[0]["hero"]
    assert out[0]["cover"] == "hero" and len(hero["rows"]) == ig_cover.ROWS
    assert hero["rows"][-1]["name"] == "P5" and hero["rows"][-1]["highlight"]


def test_text_side_and_no_chart(monkeypatch):
    monkeypatch.setenv("COVER_HERO", "off")
    assert ig_cover.with_hero([{"type": "hook", "text": "t"}, bars()], "t")[0] == {"type": "hook", "text": "t", "cover": "text"}
    monkeypatch.setenv("COVER_HERO", "on")
    table = {"type": "card", "card": {"visual": "scorecard", "payload": {}}}
    assert ig_cover.with_hero([{"type": "hook", "text": "t"}, table], "t")[0]["cover"] == "text-no-chart"


def test_ab_side_is_stable_for_a_title(monkeypatch):
    monkeypatch.setenv("COVER_HERO", "ab")
    assert len({ig_cover.variant("Same title") for _ in range(5)}) == 1


def test_carousels_over_eight_slides_are_flagged():
    assert any("9 slides" in w for w in social_rules.lint_slides([{"type": "text"}] * 9))
