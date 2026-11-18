"""The motion Reel path in ig_reel_v2 (MOTION_REEL_PLAN.md M6): the v2 script and beats planned into a reel spec,
voiced and timed, checked, recorded. The voice, the word timestamps and the recorder are fakes: no paid call, no
browser, no database."""
from pathlib import Path

import pytest

from services import ig_reel_v2 as R

ROWS = [{"name": "Jasprit Bumrah", "value": 1.98, "highlight": True, "detail": "22 wkts"},
        {"name": "Arshdeep Singh", "value": 1.89}, {"name": "Trent Boult", "value": 0.36}]
SLIDES = [
    {"type": "hook", "text": "Bumrah added 1.98 wins since the auction."},
    {"type": "card", "card": {"id": "carried", "visual": "metric_bars", "title": "Bumrah +1.98", "sample": "IPL 2025-26",
                              "payload": {"metric": {"label": "Wins added", "format": "signed2"}, "rows": ROWS}}},
    {"type": "card", "card": {"id": "batting", "visual": "metric_bars", "kicker": "Batting by role", "title": "Rickelton +17",
                              "sample": "60+ balls", "payload": {"metric": {"label": "Runs above par", "format": "signed1"},
                                                                 "rows": [{"name": "R Rickelton", "value": 17.0, "highlight": True}]}}},
    {"type": "card", "card": {"id": "cases", "visual": "case_board", "title": "Two calls", "sample": "prices: 2026",
                              "payload": {"cases": [{"name": "Rohit Sharma", "price": "₹16.30 crore", "for": "+18", "against": "−0.09"},
                                                    {"name": "Deepak Chahar", "price": "₹9.25 crore", "for": "32", "against": "−0.56"}]}}},
]
PLAN = {
    "beats": [2, 3, 4], "source": "test",
    "script": {"hook": "Bumrah added 1.98 wins since the auction. Arshdeep, traded in, 1.89.",
               "lines": ["Only Boult and Jacks clearly added wins after those two, on the whole squad board.",
                         "Rickelton leads the batting, seventeen runs above par every hundred balls.",
                         "Two calls: Rohit at 16.3 crore, about level, and Chahar at 9.25 crore."]},
    "close": {"line": "Rohit Sharma, keep or release? Send this to a Mumbai fan.", "question": "Rohit Sharma, ₹16.30 crore:",
              "lit": "keep or release?", "send": "Send this to a Mumbai fan"},
}


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    lengths = [6.5, 6.0, 6.0, 5.5, 4.5]   # 28.5s of voice: about 29.6s with the gaps and the hold
    monkeypatch.setattr(R, "voice_lines", lambda lines, voice, out: lengths[:len(lines)])
    monkeypatch.setattr(R, "duration", lambda path: sum(lengths) + R.GAP * (len(lengths) - 1))
    recorded = {}

    def recorder(spec, audio, out, base, tmp):
        recorded["spec"] = spec
        Path(out).write_bytes(b"mp4")
        return {"frames": int(spec["duration"] * 30)}
    return {"tmp": tmp_path, "recorded": recorded, "recorder": recorder}


def no_words(audio, start, length):
    return []  # words placed by characters


def test_motion_spec_is_one_scene_a_line():
    bs = [(n, R.slide_card(SLIDES[n - 1])) for n in PLAN["beats"]]
    spec, lines = R.motion_spec(SLIDES, bs, PLAN["script"], PLAN["close"])
    assert [s["kind"] for s in spec["scenes"]] == ["hero", "metric_bars", "metric_bars", "case_board", "pick_one"]
    assert len(lines) == len(spec["scenes"])


def test_make_motion_voices_times_checks_and_records(fakes):
    made = R.make_motion("cid", SLIDES, PLAN, "marin", "http://localhost:3100", fakes["tmp"] / "reel.mp4", fakes["tmp"],
                         transcribe=no_words, recorder=fakes["recorder"])
    spec = fakes["recorded"]["spec"]
    assert 28 <= made["seconds"] <= 33
    assert spec["scenes"][0]["start"] == 0 and spec["scenes"][-1]["captions"] is False
    assert [s["start"] for s in spec["scenes"]] == sorted(s["start"] for s in spec["scenes"])
    assert spec["timing"]["lines"][0].startswith("Bumrah")


def test_a_spec_that_breaks_the_rules_is_not_recorded(fakes, monkeypatch):
    monkeypatch.setattr(R, "duration", lambda path: 50.0)   # far too long
    with pytest.raises(RuntimeError, match="28-33s"):
        R.make_motion("cid", SLIDES, PLAN, "marin", "x", fakes["tmp"] / "r.mp4", fakes["tmp"], transcribe=no_words,
                      recorder=fakes["recorder"])
    assert "spec" not in fakes["recorded"]


def test_make_falls_back_to_v2_when_motion_fails(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.setattr(R.shutil, "which", lambda name: "/usr/bin/" + name)

    def boom(*a, **k):
        raise RuntimeError("no browser")
    monkeypatch.setattr(R, "make_motion", boom)

    def v2_record(cid, beats, out, base):
        calls["v2"] = beats
        raise RuntimeError("stop after v2 started")  # the v2 path was taken
    monkeypatch.setattr(R, "record", v2_record)
    with pytest.raises(RuntimeError, match="stop after v2"):
        R.make("cid", SLIDES, plan=dict(PLAN), store=False, out=tmp_path / "r.mp4", motion=True)
    assert calls["v2"] == [2, 3, 4]


def test_motion_is_off_unless_switched_on():
    assert R.MOTION is False or R.os.getenv("REEL_MOTION") == "1"


# ---- review round 9: the close, a late failure, a partial file ------------------------------------------------------

def test_close_from_the_legacy_string_and_from_the_script():
    sc = {"hook": "h", "lines": ["One.", "Rohit costs 16.3 crore. Rohit Sharma: keep or release?"]}
    sc2, close = R.motion_close(sc, "Rohit Sharma: keep or release?", "Mumbai")
    assert close["options"] == ["Keep", "Release"] and close["lit"] == "keep or release?"
    assert close["question"] == "Rohit Sharma:" and close["line"].startswith("Rohit Sharma: keep or release? Send")
    assert sc2["lines"][-1] == "Rohit costs 16.3 crore."   # said once, in the close
    _, from_script = R.motion_close(sc)                     # no string: the last line's own question
    assert from_script["options"] == ["Keep", "Release"]
    _, none = R.motion_close({"hook": "h", "lines": ["Who would you pick for the final over?"]})
    assert none is None                                     # not two choices: no motion Reel


def test_make_motion_takes_the_legacy_close_string(fakes):
    plan = {**PLAN, "close": "Rohit Sharma: keep or release?",
            "script": {**PLAN["script"], "lines": [*PLAN["script"]["lines"][:-1],
                                                   PLAN["script"]["lines"][-1] + " Rohit Sharma: keep or release?"]}}
    made = R.make_motion("cid", SLIDES, plan, "marin", "x", fakes["tmp"] / "r.mp4", fakes["tmp"], transcribe=no_words,
                         recorder=fakes["recorder"])
    assert made["spec"]["scenes"][-1]["data"]["options"] == ["Keep", "Release"]


def test_a_late_motion_failure_reuses_the_voice_and_cleans_the_file(monkeypatch, tmp_path):
    calls = {"voice": 0}

    def voice(lines, v, out):
        calls["voice"] += 1
        Path(out).write_bytes(b"voice")
        return [6.5, 6.0, 6.0, 5.5, 4.5][:len(lines)]
    monkeypatch.setattr(R, "voice_lines", voice)
    monkeypatch.setattr(R, "duration", lambda p: 29.0)
    monkeypatch.setattr(R.shutil, "which", lambda name: "/usr/bin/" + name)
    out = tmp_path / "reel.mp4"

    def bad_recorder(spec, audio, o, base, tmp):
        Path(o).write_bytes(b"partial")
        raise RuntimeError("chrome died")
    monkeypatch.setattr(R, "record_motion", bad_recorder)
    import services.reel_timing as T
    monkeypatch.setattr(T, "transcribe_words", no_words)
    seen = {}

    def v2(carousel_id, plan, sc, voice_, base, store, out_, length, voiced=None):
        seen["voiced"] = voiced
        seen["partial_gone"] = not Path(out_).exists()
        raise RuntimeError("v2 stops here")
    monkeypatch.setattr(R, "_make_v2", v2)
    with pytest.raises(RuntimeError, match="v2 stops here"):
        R.make("cid", SLIDES, plan=dict(PLAN), store=False, out=out, motion=True)
    assert calls["voice"] == 1                       # voiced once, not again for v2
    assert seen["voiced"]["audio"] == b"voice" and len(seen["voiced"]["lines"]) == 5
    assert seen["partial_gone"] and not out.exists()  # the partial motion file never stands in, nor after v2 fails


def test_auth_errors_from_the_transcription_are_not_swallowed():
    import services.reel_timing as T

    class AuthenticationError(Exception):
        status_code = 401

    def refused(audio, start, length):
        raise AuthenticationError("bad key")
    with pytest.raises(AuthenticationError):
        T.time_voice(["One two three."], "v.mp3", [1.0], transcribe=refused)


def test_the_script_writer_is_asked_for_a_two_choice_close(monkeypatch):
    sent = {}

    class Fake:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    sent["msg"] = kw["messages"][0]["content"]
                    raise RuntimeError("no network in tests")
    monkeypatch.setattr(R, "_client", lambda: Fake)
    bs = [(n, R.slide_card(SLIDES[n - 1])) for n in PLAN["beats"]]
    sc, source = R.script("hook", bs, close=R.PICK_ONE)
    assert source == "template"                       # the model failed: the template, as before
    assert "exactly two short choices" in sent["msg"]
