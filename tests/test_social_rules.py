from services import ig_reel_v2, social_rules


def test_sections_come_from_the_doc():
    for name in ("Numbers", "Carousels", "Reels", "X", "Appeal"):
        assert social_rules.section(name).startswith("- ")
    assert "one plain number" in social_rules.section("Reels")
    assert social_rules.section("Nope") == ""


def card(title, **kw):
    return {"title": title, "visual": "metric_bars", "payload": {}, **kw}


def test_title_length_and_lists():
    assert social_rules.lint_card(card("x" * 81))[0].startswith("Title over 80")
    assert social_rules.lint_card(card("Kishan, Iyer, Tilak, Dube and Rinku all scored")) == [
        "A list of more than three in the title"]
    # commas in brackets or numbers aren't list items, clauses aren't a list, and three items are fine
    assert social_rules.lint_card(card("A peak in 2022 (+9.8, his best), a slump in 2025, back up in 2026")) == []
    assert social_rules.lint_card(card("Abhishek Sharma got to 2,000 T20I runs in 1,024 balls, 140 fewer than Suryakumar")) == []
    assert social_rules.lint_card(card("At no. 4, SKY's spot, Iyer has matched him: +11.2 since, SKY +11.7 before")) == []


def test_ring_where_only_one_row_has_a_value():
    payload = {"metrics": [{"key": "T20Is 2025"}, {"key": "IPL 2025"}],
               "rows": [{"values": {"T20Is 2025": -0.84, "IPL 2025": 0.87}, "leader": ["T20Is 2025"]},
                        {"values": {"T20Is 2025": None, "IPL 2025": 1.19}, "leader": ["IPL 2025"]}]}
    got = social_rules.lint_card({"title": "t", "visual": "scorecard", "payload": payload})
    assert got == ["A 'best' ring on 'T20Is 2025', where only one row has a value"]


def test_deeper_cut_belongs_on_slide_3():
    slides = [{"type": "hook"}, {"type": "card", "card": card("a", kicker="The deeper cut")},
              {"type": "card", "card": card("b")}]
    assert social_rules.lint_slides(slides) == ["Slide 2: the deeper cut belongs on slide 3"]
    assert social_rules.lint_slides(slides, kind="play") == []  # a play-along keeps it after the answer
    slides[1], slides[2] = slides[2], slides[1]
    assert social_rules.lint_slides(slides) == []


def test_hook_rules():
    assert social_rules.hook_problem("Bhuvneshwar Kumar concedes 8.6 an over at the Chinnaswamy.") is None
    assert "no number" in social_rules.hook_problem("Fans want SKY back. Is there a case?")
    assert "metric name" in social_rules.hook_problem("SKY's T20I impact went from minus 5.7 to plus 7.7.")
    assert "metric name" in social_rules.hook_problem("Iyer added 1.19 WPA in IPL 2025.")


def test_reel_guard_applies_the_hook_rules():
    lines = ["one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen"] * 3
    ok = {"8.6"}
    good = {"hook": "Bhuvneshwar Kumar concedes 8.6 an over at the Chinnaswamy.", "lines": lines}
    assert ig_reel_v2.guard(good, ok, 3) is None
    bad = {"hook": "SKY is back in form, so is he coming back to the India side now.", "lines": lines}
    assert "no number" in ig_reel_v2.guard(bad, ok, 3)


def test_card_anatomy_and_vocabulary():
    from services.social_rules import lint_card

    ok = {"title": "Down leg, Finn Allen's SR drops to 70 and 92", "visual": "pitch_map", "payload": {"metric": {"label": "SR"}}}
    assert lint_card(ok) == []
    long_title = dict(ok, title="x " * 45)
    assert any("Title over 80" in w for w in lint_card(long_title))
    off = dict(ok, title="Allen scores at 213 against new-ball pace", payload={"metric": {"label": "runs added"}})
    got = " ".join(lint_card(off))
    assert "'new-ball'" in got and "'runs added'" in got
    defined = dict(ok, help="Impact: runs added to the batting side's projected total")  # defines Impact: fine
    assert not any("runs added" in w for w in lint_card(defined))
    # A help line is drawn on the card only with help_on_card; otherwise it's in the info sheet and its length is fine.
    assert not any("help line" in w for w in lint_card(dict(ok, help="h" * 100)))
    assert any("help line" in w for w in lint_card(dict(ok, help="h" * 100, help_on_card=True)))
