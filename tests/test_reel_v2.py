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
        "India still had 4 pace overs left by the 17th, and spin bowled 3 of the last 4. That is the plan around it, "
        "and it matters more than the one over everyone remembers from the night.",
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
    assert R.variant("play", even) == "v1"  # not a Reel kind
    monkeypatch.setenv("REEL_AB", "0")
    assert R.variant("recap", odd) == "v2"


def test_signs_are_spoken_and_verdicts_are_material():
    assert R.spoken("falls to −0.29 from +0.35") == "falls to minus 0.29 from plus 0.35"
    assert R.spoken("Rutherford's 49* off 26") == "Rutherford's 49 not out off 26"
    assert R.spoken("2-0 up") == "2-0 up" or "minus" not in R.spoken("in 2026-27")  # hyphens between words stay
    notes = R.notes_of([{"type": "verdict", "verdict": "Partly", "body": "a. claim: Inconclusive"},
                        {"type": "text", "heading": "From elsewhere", "body": "15 wickets\nSource: ESPNcricinfo"}])
    assert "THE VERDICT" in notes and "ESPNcricinfo" not in notes


def test_align_lines_voiced_one_by_one():
    segs = ["Hook words here.", "Second part comes next.", "Third."]
    starts, caps = R.align(segs, [1.0, 2.0, 0.5], gap=0.1)
    assert starts == [0.0, 1.1, 3.2]  # each line starts when the one before ends, plus the gap
    assert caps[0][2] == "Hook words here." and caps[-1][2] == "Third."
    assert caps[-1][1] == 3.7 and all(a < b for a, b, _ in caps)

def test_guard_needs_exact_values_and_a_statement_hook():
    bs = [(2, {"title": "Averages since", "payload": {"rows": [{"name": "Prasidh", "value": 28.9}]}}),
          (3, {"title": "Cost", "payload": {"rows": [{"name": "Shami", "value": 8.2}]}})]
    ok = R.allowed("Shami", bs)
    assert "28.9" in ok and "30" not in ok and "29" not in ok
    words = " ".join(["word"] * 45)
    base = {"hook": "Shami takes one every 14 balls.", "lines": [f"Prasidh averages 28.9 {words}", "He goes for 8.2."]}
    assert "14" in R.guard(base, ok, 2)  # 14 isn't on these cards
    q = {"hook": "Should Shami return?", "lines": [f"Prasidh averages 28.9 {words}", "He goes for 8.2."]}
    assert "question" in R.guard(q, ok, 2)  # a bare question
    q2 = {"hook": "Shami goes for 8.2. Should he return?", "lines": q["lines"]}
    assert R.guard(q2, ok, 2) is None  # a question with a number is a fine hook


def test_first_line_cant_repeat_the_hooks_numbers():
    bs = [(2, {"title": "86% with him, 58% without", "payload": {}}), (3, {"title": "7.9 to 0.9", "payload": {}})]
    ok = R.allowed("", bs)
    pad = " ".join(["word"] * 45)
    rep = {"hook": "India win 86% with Bumrah.", "lines": [f"With Bumrah it's 86%, without 58%. {pad}", "Then 7.9 to 0.9."]}
    assert "repeats" in R.guard(rep, ok, 2)
    moved = {"hook": "India win 86% with Bumrah.", "lines": [f"Without him, it's 58%. {pad}", "Then 7.9 to 0.9."]}
    assert R.guard(moved, ok, 2) is None


def test_pronunciation_respells_for_the_voice_only(monkeypatch):
    monkeypatch.setattr(R, "pronunciations", lambda: {"Bumrah": {"say": "Boomrah", "hint": "BOOM-rah"}})
    assert R.spoken("Bumrah bowls; Bumrah's spell") == "Boomrah bowls; Boomrah's spell"
    assert R.hints("without Bumrah") == "BOOM-rah" and R.hints("without Siraj") == ""


def test_phrases_break_at_punctuation_and_length():
    ws = "India win 86% against top sides with Bumrah. Without him, 58%.".split()
    got = [" ".join(ws[a:b]) for a, b in R.phrases(ws)]
    assert got[0] == "India win 86% against top sides" and got[1] == "with Bumrah." and got[-1].endswith("58%.")
    assert all(len(p) <= 40 for p in got)


def test_word_times_follow_the_transcription():
    ours = "falls to −0.29 from +0.35 a game".split()
    timed = [{"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, w in
             enumerate(["falls", "to", "minus", "zero", "point", "two", "nine", "from", "plus", "0.35", "a", "game"])]
    t = R.word_times(ours, timed, 5.0)
    assert t[0] == 0.0 and t[3] == timed[7]["start"]  # "from" lands on the spoken "from", not a guess
    assert t == sorted(t)
    srt = R.srt([(0.0, 1.5, "falls to −0.29"), (1.5, 3.0, "from +0.35")])
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,500\nfalls to −0.29")


def test_long_captions_split_near_the_middle():
    assert R.balance("In the powerplay,") == ["In the powerplay,"]
    assert R.balance("it's 0.31 versus minus 0.02.") == ["it's 0.31 versus", "minus 0.02."]


def test_one_word_phrases_join_the_one_before():
    ws = "Against top sides, India win 86% with Bumrah and 58% without. So what changes?".split()
    got = [" ".join(ws[a:b]) for a, b in R.phrases(ws)]
    assert "without." not in got and any(p.endswith("58% without.") for p in got)


def _preview_slides(ids):
    return [{"type": "hook", "text": "7 things the data says before India v West Indies"}] + [
        {"type": "card", "card": {"id": i, "visual": "player_bars", "title": i, "payload": {}}} for i in ids]


def test_preview_beats_follow_the_story_and_close_on_a_milestone():
    slides = _preview_slides(["key-battles", "totals", "milestones", "form-strips", "suits-ground", "ground-records",
                              "where-won"])
    bs = R.beats(slides, k=5)
    assert [c["id"] for _, c in bs] == ["totals", "form-strips", "suits-ground", "ground-records", "milestones"]
    assert [c["id"] for _, c in R.beats(slides, k=3)] == ["totals", "form-strips", "milestones"]
    assert R.by_card_id(slides, ["milestones", "totals"]) == [4, 3]


def test_preview_beats_need_two_of_their_cards():
    slides = _preview_slides(["totals", "where-won", "projected-points"])
    assert [c["id"] for _, c in R.beats(slides, k=3)][0] != "milestones"
    assert R.preview_beats([(2, {"id": "totals"})], 3) == []


class _FakeRealtime:
    """A Realtime connection that speaks each line as `takes` says: its transcript, and 0.5s of audio."""

    def __init__(self, takes):
        self.takes, self.sent, self.session_cfg = list(takes), [], None
        outer = self

        class Session:
            def update(self, session):
                outer.session_cfg = session

        class Items:
            def create(self, item):
                outer.sent.append(item["content"][0]["text"])

        class Conversation:
            item = Items()

        class Response:
            def create(self):
                pass

        self.session, self.conversation, self.response = Session(), Conversation(), Response()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        import base64
        from types import SimpleNamespace as E

        said = self.takes.pop(0)
        yield E(type="response.output_audio.delta", delta=base64.b64encode(b"\x01\x00" * 12000).decode())
        yield E(type="response.output_audio_transcript.delta", delta=said)
        yield E(type="response.done")


def _fake_client(monkeypatch, conn):
    from types import SimpleNamespace as NS

    monkeypatch.setattr(R, "_client", lambda: NS(realtime=NS(connect=lambda model: conn)))
    monkeypatch.setattr(R, "TEMPO", 1.0)


def test_voice_lines_times_each_line_and_retakes_a_paraphrase(monkeypatch, tmp_path):
    import shutil

    import pytest

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg")
    conn = _FakeRealtime(["Rajat Patidar leads.", "He strikes at 283.", "He strikes at 238!"])
    _fake_client(monkeypatch, conn)
    lengths = R.voice_lines(["Rajat Patidar leads.", "He strikes at 238."], "marin", tmp_path / "v.mp3")
    assert lengths == [0.5, 0.5]                    # each line's length, from its own audio
    assert conn.sent[1:] == ["He strikes at 238.", "He strikes at 238."]  # the wrong number was asked for again
    assert conn.session_cfg["audio"]["output"]["voice"] == "marin"
    assert (tmp_path / "v.mp3").exists()


def test_voice_lines_gives_up_rather_than_voice_a_wrong_number(monkeypatch, tmp_path):
    import pytest

    _fake_client(monkeypatch, _FakeRealtime(["He strikes at 283."] * R.LINE_TRIES))
    with pytest.raises(RuntimeError):
        R.voice_lines(["He strikes at 238."], "marin", tmp_path / "v.mp3")
