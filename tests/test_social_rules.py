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


def test_caption_problems():
    from services.social_rules import caption_problems

    good = "Suryakumar Yadav, 60* off 21: worth 33 more runs than an average batter.\n\nMore.\n.\n#SMAT #IPL2027"
    assert caption_problems(good) == []
    assert any("news" in w.lower() for w in caption_problems("News first: Delhi traded 3 players.\n\n#a"))
    assert any("No number" in w for w in caption_problems("Who owns the pull shot in ODIs?\n\n#a"))
    assert any("2200" in w for w in caption_problems("Kohli 38. " + "x" * 2300))
    assert any("hashtags" in w for w in caption_problems("Kohli 38.\n.\n#a #b #c #d #e #f"))
    assert any("first sentence" in w for w in caption_problems("Kohli " + "word " * 40 + "38."))


def test_house_terms_are_jargon_in_a_hook():
    from services.social_rules import hook_problem

    assert hook_problem("Noor Ahmad saved 41 runs against par since the mega auction.")
    assert hook_problem("Suryakumar Yadav: 60 not out off 21 balls.") is None


def test_reference_decks_may_run_long():
    from services.social_rules import findings

    deck = [{"type": "image"} for _ in range(12)]
    assert any(f["rule"] == "slide_count" for f in findings(deck, "spotlight"))
    assert not any(f["rule"] == "slide_count" for f in findings(deck, "reference"))


def test_a_thread_must_group_its_slides():
    """One tweet per slide is the carousel retyped (18 Nov scorecard thread): up to four slides a tweet."""
    from services.social_rules import thread_problems

    per_slide = [{"n": i, "text": f"Tweet {i}", "slides": [i]} for i in range(1, 9)]
    assert any("group the slides" in p for p in thread_problems(per_slide))
    grouped = [{"n": 1, "text": "Hook #IPL2027", "slides": [1]}, {"n": 2, "text": "Four", "slides": [2, 3, 4, 5]},
               {"n": 3, "text": "Three and the link", "slides": [6, 7, 8]}]
    assert thread_problems(grouped) == []
    assert any("tweet 1: 2 images" in p for p in thread_problems([{"n": 1, "text": "Hook", "slides": [1, 2]}]))


def test_a_short_title_is_never_cut_mid_thought():
    from services.ig_notes import yt_title
    from services.social_rules import youtube_problems

    hook = "Dhoni's gone. Chennai's squad has 4 of 7 roles at playoff level. Only RCB has more."
    assert yt_title(hook) == ""  # no whole clause fits: no title, not "...4 of 7 roles at playoff"
    assert youtube_problems({"title": ""})[0].startswith("The Short has no title")
    assert youtube_problems({"title": "IPL 2027 retentions: every squad graded like a playoff side"}) == []
    assert youtube_problems({"title": "x" * 61})


def test_a_hand_post_breaking_the_copy_rules_is_not_queued():
    import pytest
    from services import ig_backlog

    post = {"key": "t", "pillar": "reactive", "snapshot_id": None, "warnings": [], "caption": "c",
            "fact": {"title": "t", "x": [{"n": i, "text": "x", "slides": [i]} for i in range(1, 9)]}}

    class Conn:
        def execute(self, *a, **k):
            raise AssertionError("queued")

    with pytest.raises(ig_backlog.RuleBroken):
        ig_backlog.upsert_pack(Conn(), post, None, source="hand")
