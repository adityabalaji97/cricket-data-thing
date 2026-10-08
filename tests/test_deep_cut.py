from services.ig_posts import deep_cut as D


def bucket(label, balls, runs):
    return {"batter_balls_faced_bucket": label, "balls": balls, "runs": runs}


FIELD_BUCKETS = [bucket("1-9", 10000, 10500), bucket("10-19", 8000, 10000), bucket("20-29", 6000, 8400)]


def test_slow_start_finds_a_slow_starter_and_writes_the_numbers():
    rows = [bucket("1-9", 100, 66), bucket("10-19", 80, 100), bucket("20-29", 120, 198)]
    c = D.slow_start("Sherfane Rutherford", "batter", rows, FIELD_BUCKETS, "T20s since 2023")
    assert c and c.probe == "slow-start"
    assert c.sentence == ("Sherfane Rutherford strikes at 66 in the first 10 balls of an innings and 165 after 20. "
                          "The average batter: 105, then 140.")
    assert [r["label"] for r in c.rows] == ["Balls 1-9", "Balls 10-19", "Balls 20+"]


def test_slow_start_needs_a_sample_and_a_real_difference():
    small = [bucket("1-9", 20, 13), bucket("20-29", 120, 198)]
    assert D.slow_start("A", "batter", small, FIELD_BUCKETS, "s") is None  # 20 early balls: too few
    like_field = [bucket("1-9", 100, 105), bucket("20-29", 120, 168)]
    assert D.slow_start("A", "batter", like_field, FIELD_BUCKETS, "s") is None  # same shape as the field


def test_false_shots_needs_tagged_balls():
    field = [{"control": 1, "bowl_kind": "spin bowler", "balls": 7600}, {"control": 0, "bowl_kind": "spin bowler", "balls": 2400}]
    rows = [{"control": 1, "bowl_kind": "spin bowler", "balls": 180}, {"control": 0, "bowl_kind": "spin bowler", "balls": 20}]
    c = D.false_shots("Shreyas Iyer", "batter", rows, field, "s")
    assert c and c.sentence == "Shreyas Iyer is in control of 90% of balls against spin. The average batter: 76%."
    assert c.metric["label"] == "% of balls in control" and c.rows[0]["subject"] == 90  # chart matches the sentence
    untagged = rows + [{"control": None, "bowl_kind": "spin bowler", "balls": 100}]  # a third untagged: below the floor
    assert D.false_shots("Shreyas Iyer", "batter", untagged, field, "s") is None


def test_zones_and_lengths_read_as_sentences():
    field = [{"wagon_zone": z, "runs": 1000, "balls": 800} for z in range(1, 9)]
    rows = [{"wagon_zone": 3, "runs": 150, "balls": 80}] + [{"wagon_zone": z, "runs": 30, "balls": 30} for z in (1, 2, 4, 5, 6, 7)]
    c = D.zones("Sherfane Rutherford", "batter", rows, field, "s")
    assert c and c.sentence.startswith("45% of Sherfane Rutherford's runs come through midwicket.")
    lrows = [{"length": "YORKER", "balls": 50, "runs": 60}, {"length": "FULL", "balls": 100, "runs": 150}]
    lfield = [{"length": "YORKER", "balls": 5000, "runs": 4000}, {"length": "FULL", "balls": 9000, "runs": 13500}]
    c = D.length("Shreyas Iyer", "batter", lrows, lfield, "s")
    assert c and c.sentence == "Shreyas Iyer strikes at 120 against yorkers. The average batter: 80."


def test_phase_value_for_a_bowler():
    rows = [{"phase": "death", "balls": 300, "raa": 130}, {"phase": "powerplay", "balls": 200, "raa": 10}]
    c = D.phase_value("Jasprit Bumrah", "bowler", rows, [], "T20s since 2023")
    assert c and c.sentence == ("At the death, Jasprit Bumrah saves 2.6 runs an over against an average bowler "
                                "in the same situations.")
    assert c.sample.endswith("300 balls at the death")
    assert D.phase_value("A", "bowler", [{"phase": "death", "balls": 300, "raa": 10}], [], "s") is None  # 0.2 an over


def test_pick_avoids_recent_probes_and_to_card_is_branded():
    a = D.Candidate("phase-value", "A", "a", 1.0, {"label": "x", "format": "int"}, [], "s")
    b = D.Candidate("zones", "A", "b", 0.5, {"label": "x", "format": "int"}, [], "s")
    assert D.pick([a, b], avoid=["phase-value"]) is b
    assert D.pick([a], avoid=["phase-value"]) is a  # nothing fresh: the best one anyway
    assert D.pick([], avoid=[]) is None
    card = D.to_card(b)
    assert card["visual"] == "deep_compare" and card["kicker"] == "The deeper cut" and card["title"] == "b"


def test_caption_and_x_carry_the_deeper_cut():
    from services.ig_captions import LINK_LINE, with_deep_cut
    from services.ig_x import slide_text

    cap = f"Hook\n\nWho are you backing?\n\n{LINK_LINE}\n.\n#cricket"
    out = with_deep_cut(cap, "Abhishek Sharma strikes at 255 against leg-spin.")
    assert out.index("The deeper cut: Abhishek Sharma") < out.index(LINK_LINE)
    assert with_deep_cut(out, "Abhishek Sharma strikes at 255 against leg-spin.") == out  # once only
    slide = {"type": "card", "card": {"title": "Abhishek Sharma strikes at 255", "kicker": "The deeper cut"}}
    assert slide_text(slide, {}) == "The deeper cut: Abhishek Sharma strikes at 255"


def test_add_deep_cut_is_slide_three_or_after_the_answer(monkeypatch):
    from services import ig_backlog, ig_carousel
    from services.ig_posts import deep_cut

    slides = [{"type": "hook", "text": "h"}, {"type": "card", "card": {"title": "t"}}, {"type": "card", "card": {"title": "u"}},
              {"type": "end", "heading": "e"}]

    class DB:
        def execute(self, sql, params=None):
            class R:
                def scalar(self_inner):
                    return {"slides": slides, "title": "T"}

                def all(self_inner):
                    return [("zones",)]
            return R()

    saved = {}
    monkeypatch.setattr(ig_carousel, "save", lambda db, s, title, key, by: saved.update(slides=s) or {"id": "NEW"})
    monkeypatch.setattr(deep_cut, "choose", lambda db, fact, avoid, used: saved.update(avoid=list(avoid)) or {
        "card": {"id": "deep-zones", "kicker": deep_cut.KICKER, "title": "x"},
        "deep_cut": {"probe": "zones", "sentence": "x", "subject": "A", "by": "surprise", "jev": None, "surprise": 1}})
    post = {"key": "k", "fact": {"kind": "debate", "title": "T", "carousel_id": "OLD", "slides": 3}, "snapshot_id": "OLD",
            "caption": "c"}
    got = ig_backlog.add_deep_cut(DB(), post, None, recent=["slow-start"], used=set())
    assert got["probe"] == "zones" and saved["avoid"] == ["slow-start"]
    assert saved["slides"][2]["card"]["kicker"] == deep_cut.KICKER  # slide 3
    assert [s["type"] for s in saved["slides"]] == ["hook", "card", "card", "card", "end"]
    assert post["fact"]["carousel_id"] == "NEW" and post["snapshot_id"] == "NEW" and post["fact"]["slides"] == 5
    assert ig_backlog.add_deep_cut(DB(), post, None) is None  # already has one
    play = {"key": "p", "fact": {"kind": "play", "title": "T", "carousel_id": "OLD", "slides": 4}, "snapshot_id": "OLD"}
    ig_backlog.add_deep_cut(DB(), play, None, recent=[], used=set())
    assert saved["slides"][3]["card"]["kicker"] == deep_cut.KICKER  # after the answer, just before the end


def test_card_keeps_at_most_four_rows_and_the_highlight():
    rows = [{"label": str(i), "subject": i, "field": i, "highlight": i == 4} for i in range(5)]
    card = D.to_card(D.Candidate("length", "A", "a", 1.0, {"label": "x", "format": "int"}, rows, "s"))
    assert [r["label"] for r in card["payload"]["rows"]] == ["0", "1", "2", "4"]


def test_no_repeat_of_a_players_stat_and_debates_stay_on_topic():
    a = D.Candidate("style", "Ishan Kishan", "a", 1.0, {"label": "x", "format": "int"}, [], "s")
    b = D.Candidate("zones", "Ishan Kishan", "b", 0.5, {"label": "x", "format": "int"}, [], "s")
    assert D.pick([a, b], used={("Ishan Kishan", "style")}) is b
    assert D.pick([a], used={("Ishan Kishan", "style")}) is None  # nothing new: no slide
    zones = D.Candidate("zones", "Cameron Green", "z", 0.65, {"label": "x", "format": "int"}, [], "s")
    death = D.Candidate("phase-value", "Cameron Green", "d", 0.5, {"label": "x", "format": "int"}, [], "s")
    D.on_topic({"title": "Who is the best finisher in the IPL since 2023?"}, [zones, death])
    assert death.surprise > zones.surprise


def test_first_over_needs_a_clear_story():
    def rows(bad, good):
        return [{"bowler_first_over_runs_bucket": "10+", "balls": 60, "runs": bad * 10},
                {"bowler_first_over_runs_bucket": "0-6", "balls": 60, "runs": good * 10}]
    field = rows(9.0, 7.6)
    assert D.first_over("Matheesha Pathirana", "bowler", rows(9.0, 8.7), field, "s") is None  # no story
    c = D.first_over("Piyush Chawla", "bowler", rows(7.6, 8.5), field, "s")
    assert c and c.probe == "first-over"  # recovers


def test_conversion_finds_a_bowler_who_turns_false_shots_into_wickets():
    rows = [{"control": 0, "balls": 231, "wickets": 42}, {"control": 1, "balls": 600, "wickets": 0}]
    field = [{"control": 0, "balls": 36000, "wickets": 5200}, {"control": 1, "balls": 90000, "wickets": 400}]
    c = D.conversion("Bhuvneshwar Kumar", "bowler", rows, field, "T20s since 2023")
    assert c and c.sentence == "Bhuvneshwar Kumar takes a wicket for every 5.5 false shots. The average bowler needs 6.9."
    assert c.sample.endswith("42 wickets from 231 false shots")
    assert [r["label"] for r in c.rows] == ["False shots per wicket", "Balls per wicket"]
    assert round(c.rows[1]["subject"], 1) == round(831 / 42, 1)
    few = [{"control": 0, "balls": 40, "wickets": 10}, {"control": 1, "balls": 300, "wickets": 0}]
    assert D.conversion("A", "bowler", few, field, "s") is None  # too few beaten balls


def test_a_post_can_exclude_probes_its_slides_already_show(monkeypatch):
    a = D.Candidate("phase-value", "A", "a", 1.0, {"label": "x", "format": "int"}, [], "s")
    b = D.Candidate("conversion", "A", "b", 0.3, {"label": "x", "format": "int"}, [], "s")
    monkeypatch.setattr(D, "subjects_for", lambda db, fact: ([("bowler", "A", "A")], {}, "s"))
    monkeypatch.setattr(D, "candidates", lambda *args, **kw: [a, b])
    monkeypatch.setattr(D, "rank", lambda cands: (cands, "surprise"))
    got = D.choose(None, {"subject": "A", "deep_cut_exclude": ["phase-value"]})
    assert got["deep_cut"]["probe"] == "conversion"


def test_conversion_is_retired_from_posts():
    assert "conversion" not in {p.id for p in D.PROBES}


def test_bowlers_are_compared_with_their_own_kind(monkeypatch):
    calls = []

    def q(db, **args):
        calls.append(args)
        if args["group_by"] == ["bowl_kind"]:
            return {"data": [{"bowl_kind": "spin bowler", "balls": 900}, {"bowl_kind": "pace bowler", "balls": 6}]}
        if args.get("bowlers"):
            return {"data": [{"length": "FULL", "wickets": 11, "balls": 300}, {"length": "GOOD_LENGTH", "wickets": 20, "balls": 600}]}
        return {"data": [{"length": "FULL", "wickets": 200, "balls": 30000}, {"length": "GOOD_LENGTH", "wickets": 800, "balls": 90000}]}
    import services.query_builder_v2 as qb
    monkeypatch.setattr(qb, "run_deliveries_query", q)
    D._FIELD.clear()
    probe = [p for p in D.PROBES if p.id == "wicket-length"]
    cands = D.candidates(None, "bowler", "M Theekshana", {"fmt": "ODI"}, "ODIs", probes=probe, display="Maheesh Theekshana")
    field_calls = [c for c in calls if c["group_by"] == ["length"] and not c.get("bowlers")]
    assert field_calls and field_calls[0]["bowl_kind"] == ["spin bowler"]  # the field is spinners only
    assert cands and "The average spinner: 20%." in cands[0].sentence and cands[0].series[1] == "Average spinner"
