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


def test_hero_takes_the_lead_card_off_the_deck_and_x_shows_the_cover(monkeypatch):
    from services.ig_x import x_thread

    monkeypatch.setenv("COVER_HERO", "on")
    lead = bars()
    lead["card"]["title"] = "Lead claim"
    deck = [{"type": "hook", "text": "Hook"}, lead, {"type": "card", "card": {"id": "next", "title": "Next claim"}},
            {"type": "end", "heading": "End", "body": "b"}]
    out = ig_cover.with_hero(deck, "t")
    assert [s.get("card", {}).get("id") for s in out[1:3]] == ["next", None]  # slide 2 is new, not the cover's chart
    thread = x_thread(out, "#INDvNZ")
    assert thread[0]["slide"] == 1 and thread[0]["text"].startswith("Hook\n\nLead claim")
    assert thread[1]["slide"] == 2


def test_stacked_share_chart_makes_a_cover():
    from services.ig_cover import hero_from

    card = {"visual": "share_bars", "payload": {"groups": [{"key": "big", "label": "Big"}, {"key": "cost", "label": "Cost"}],
                                                 "rows": [{"name": "A", "segments": [{"key": "big", "value": 40}, {"key": "cost", "value": 60}]},
                                                          {"name": "B", "segments": [{"key": "big", "value": 10}, {"key": "cost", "value": 90}]}]}}
    h = hero_from(card)
    assert h["kind"] == "share" and [r["name"] for r in h["rows"]] == ["A", "B"] and len(h["groups"]) == 2


def test_a_hand_set_hero_still_leaves_the_deck():
    """A hand-built post sets the cover's hero itself; its chart must still not be repeated as slide 2."""
    from services.social_rules import lint_slides

    lead = {"id": "openers", "title": "Lead claim", "visual": "metric_bars", "payload": {"rows": []}}
    deck = [{"type": "hook", "text": "Hook", "cover": "hero", "hero": {"rows": [], "card": lead}},
            {"type": "card", "card": dict(lead)}, {"type": "card", "card": {"id": "next", "title": "Next claim"}},
            {"type": "end", "heading": "End", "body": "b"}]
    assert any("repeats the cover's chart" in w for w in lint_slides(deck))
    out = ig_cover.with_hero(deck, "t")
    assert [s.get("card", {}).get("id") for s in out[1:]] == ["next", None]
    assert not any("repeats the cover's chart" in w for w in lint_slides(out))


def test_a_win_probability_line_can_be_the_cover():
    line = {"id": "wp", "visual": "win_prob_line", "title": "t",
            "payload": {"team": "A", "start": 50, "points": [{"wp": 40}],
                        "bands": [{"over": 6, "from": 82, "to": 72}, {"over": 15, "from": 80, "to": 59},
                                  {"over": 20, "from": 96, "to": 0}]}}
    hero = ig_cover.hero_from(line)
    assert hero["kind"] == "line" and [b["over"] for b in hero["payload"]["bands"]] == [15, 20]


def test_the_rules_catch_a_bare_cover_a_text_card_and_one_overs():
    slides = [{"type": "hook", "text": "t", "cover": "text-no-chart"},
              {"type": "card", "card": {"id": "how", "visual": "recap_text", "title": "How it was won"}},
              {"type": "card", "card": {"id": "wp", "visual": "win_prob_line", "title": "SRH peaked at 98%, then 1 overs took it away"}}]
    got = " | ".join(social_rules.lint_slides(slides))
    assert "Slide 1: no chart on the cover" in got and "Slide 2: A text card" in got and "'1 overs'" in got
