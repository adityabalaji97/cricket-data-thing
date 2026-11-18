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


# ---- motion length and the retention preset (motion-reels-2) ---------------------------------------------------------

V2_SHORT = {"hook": "Bumrah added 1.98 wins since the auction.",
            "lines": ["Arshdeep, traded in, sits right behind him at 1.89, and Boult adds 0.36.",
                      "Rickelton leads the batting by role, 17 runs above par.",
                      "Two calls: Rohit at 16.30 crore, Chahar at 9.25 crore. Rohit Sharma: keep or release?"]}
MOTION_LEN = {"hook": "Bumrah added 1.98 wins since the auction. Nobody did more.",
              "lines": ["Arshdeep, traded in, sits right behind him at 1.89. After those two the board thins out, and "
                        "Boult is next with 0.36.",
                        "Rickelton leads the batting by role, 17 runs above par, the clearest "
                        "gain.",
                        "Two calls on price. Rohit costs 16.30 crore and Chahar 9.25 crore. Rohit Sharma: "
                        "keep or release?"]}


def fake_writer(monkeypatch, replies):
    """A faked script model: the writer answers from `replies` in turn (the last one again after that), the checker
    finds nothing. Records the writer's prompts."""
    import json as _json
    sent = {"script": [], "check": 0}
    queue = list(replies)

    def reply(content):
        msg = type("M", (), {"content": content})()
        return type("R", (), {"choices": [type("C", (), {"message": msg})()]})()

    class Fake:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    msg = kw["messages"][0]["content"]
                    if msg.startswith("You check"):
                        sent["check"] += 1
                        return reply('{"problems": []}')
                    sent["script"].append(msg)
                    return reply(_json.dumps(queue.pop(0) if len(queue) > 1 else queue[0]))
    monkeypatch.setattr(R, "_client", lambda: Fake)
    return sent


def spoken_voice(monkeypatch, rate=2.8):
    """A faked voice at `rate` spoken words a second (the live voice: 2.75-2.95), so the length follows the script."""
    from services.reel_timing import spoken_count
    got = {}

    def voice(lines, v, out):
        got["lines"] = list(lines)
        got["lengths"] = [spoken_count(x) / rate for x in lines]
        Path(out).write_bytes(b"voice")
        return got["lengths"]
    monkeypatch.setattr(R, "voice_lines", voice)
    monkeypatch.setattr(R, "duration", lambda p: sum(got["lengths"]) + R.GAP * (len(got["lengths"]) - 1))
    return got


def test_motion_on_the_writer_aims_for_the_motion_length_and_the_close(monkeypatch, tmp_path):
    import services.reel_timing as T
    from services.reel_timing import spoken_count
    sent = fake_writer(monkeypatch, [V2_SHORT, MOTION_LEN])   # a v2-length script first: rejected as too short
    got = spoken_voice(monkeypatch)
    monkeypatch.setattr(T, "transcribe_words", no_words)
    monkeypatch.setattr(R.shutil, "which", lambda name: "/usr/bin/" + name)
    recorded = {}

    def recorder(spec, audio, out, base, tmp):
        recorded["spec"] = spec
        Path(out).write_bytes(b"mp4")
        return {}
    monkeypatch.setattr(R, "record_motion", recorder)
    made = R.make("cid", SLIDES, plan={"beats": [2, 3, 4], "close": "Rohit Sharma: keep or release?"}, store=False,
                  out=tmp_path / "r.mp4", motion=True)
    assert made["motion"] is True and 28 <= made["seconds"] <= 33
    assert "70 to 78 spoken words" in sent["script"][0] and "about 30 seconds" in sent["script"][0]
    assert "1.98 is four words" in sent["script"][0]
    assert "spoken words (too short" in sent["script"][1]                     # the retry says why
    assert 76 <= sum(spoken_count(x) for x in got["lines"]) <= 84             # with the close's send line
    close = recorded["spec"]["scenes"][-1]
    assert close["kind"] == "pick_one" and close["data"]["options"] == ["Keep", "Release"]
    assert got["lines"][-1].startswith("Rohit Sharma: keep or release? Send this")


def test_motion_off_keeps_the_v2_length(monkeypatch):
    sent = fake_writer(monkeypatch, [V2_SHORT])
    bs = [(n, R.slide_card(SLIDES[n - 1])) for n in PLAN["beats"]]
    sc, source = R.script("Bumrah added 1.98 wins since the auction.", bs, length="short")
    assert sc == V2_SHORT and source == R.SCRIPT_MODEL
    assert "55 to 72 words" in sent["script"][0] and "spoken words" not in sent["script"][0]


def test_a_voice_a_touch_short_holds_the_close_to_28s():
    assert R.close_hold(29.0) == 0.6          # long enough: the usual hold
    assert R.close_hold(26.5) == 1.6          # 26.5 + 1.6 = 28.1
    assert R.close_hold(24.0) == R.HOLD_MAX   # far too short: the check still fails it


def test_overseas_from_the_retained_csv(tmp_path):
    f = tmp_path / "retained.csv"
    f.write_text("team,player,overseas,traded_in,name_2026\nMI,Trent Boult,1,0,Trent Boult\n"
                 "MI,Jasprit Bumrah,0,0,Jasprit Bumrah\nCSK,Noor Ahmad,1,0,Noor Ahmad\n")
    assert R.overseas_of("mi", f) == ["Trent Boult"]


def _retention_slides():
    import importlib
    return importlib.import_module("tests.test_reel_plan")._retention_slides()


def test_retention_preset_voiced_timed_placed_and_recorded(monkeypatch, tmp_path):
    got = spoken_voice(monkeypatch)
    recorded = {}

    def recorder(spec, audio, out, base, tmp, nodrift=False):
        recorded.update(spec=spec, nodrift=nodrift, base=base)
        Path(out).write_bytes(b"mp4")
        return {"frames": 900}
    made = R.make_retention(_retention_slides(), "MI", base="http://x", out=tmp_path / "mi.mp4",
                            overseas=["Trent Boult"], nodrift=True, keep=tmp_path / "keep", transcribe=no_words,
                            recorder=recorder)
    assert recorded["nodrift"] is True and recorded["base"] == "http://x"
    assert got["lines"] == made["lines"] and made["lines"][-1].endswith("Send this to a Mumbai fan.")
    spec = recorded["spec"]
    assert spec["scenes"][0]["kind"] == "hero" and spec["scenes"][-1]["kind"] == "pick_one"
    from services.social_rules import reel_problems
    assert reel_problems(spec) == [] and 28 <= made["seconds"] <= 33
    assert (tmp_path / "keep" / "reel.json").exists() and (tmp_path / "keep" / "voice.mp3").exists()


def test_retention_preset_keeps_the_voice_when_it_fails(monkeypatch, tmp_path):
    spoken_voice(monkeypatch)

    def bad(spec, audio, out, base, tmp, nodrift=False):
        Path(out).write_bytes(b"partial")
        raise RuntimeError("chrome died")
    with pytest.raises(R.MotionFailed):
        R.make_retention(_retention_slides(), "MI", out=tmp_path / "mi.mp4", keep=tmp_path / "keep",
                         transcribe=no_words, recorder=bad)
    assert (tmp_path / "keep" / "voice.mp3").read_bytes() == b"voice" and not (tmp_path / "mi.mp4").exists()
    assert (tmp_path / "keep" / "reel.json").exists()          # the placed spec: re-record with no new paid call


def test_the_preset_command_is_preview_only(monkeypatch, tmp_path, capsys):
    import json as _json
    import sys as _sys
    sys_path = str(Path(__file__).resolve().parents[1] / "scripts")
    monkeypatch.syspath_prepend(sys_path)
    import make_reel_v2 as CLI
    slides = tmp_path / "slides.json"
    slides.write_text(_json.dumps(_retention_slides()))
    retained = tmp_path / "retained.csv"
    retained.write_text("team,player,overseas,traded_in,name_2026\nMI,Trent Boult,1,0,Trent Boult\n")
    seen = {}

    def fake(slides_, team, **kw):
        seen.update(team=team, **kw)
        return {"seconds": 30.1, "spec": {}, "lines": ["One two.", "Three."], "recorded": {}, "mp4": None}
    monkeypatch.setattr(R, "make_retention", fake)
    monkeypatch.setattr(_sys, "argv", ["x", "--preset", "retention", "--team", "mi", "--slides", str(slides),
                                       "--retained", str(retained), "--nodrift", "--base", "http://x"])
    assert CLI.main() == 0
    assert seen["team"] == "MI" and seen["overseas"] == ["Trent Boult"] and seen["nodrift"] is True
    assert _json.loads(capsys.readouterr().out)["spoken_words"] == 3
    monkeypatch.setattr(_sys, "argv", ["x", "--preset", "retention", "--team", "MI", "--store"])
    assert CLI.main() == 1                     # never stored
