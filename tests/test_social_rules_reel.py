"""Motion Reel checks (MOTION_REEL_PLAN.md M7, services/social_rules.reel_problems)."""
import json
from pathlib import Path

from services.social_rules import reel_captions, reel_frame, reel_problems

ROOT = Path(__file__).resolve().parents[1]
R2 = json.loads((ROOT / "src/components/ig/reel/__fixtures__/smat_round2.reel.json").read_text())


def spec(**over):
    s = {"duration": 30, "scenes": [
        {"kind": "metric_bars", "start": 0, "end": 27, "kicker": "Batting by role",
         "payload": {"rows": [{"name": "A", "value": 5.0}, {"name": "B", "value": -3.0}]},
         "beats": [{"at": 1.0, "key": "A"}]},
        {"kind": "pick_one", "start": 27, "end": 30, "captions": False, "data": {"send": {"text": "Send this to a fan"}}}],
        "captions": [{"start": 0, "words": [{"w": "One", "at": 0}, {"w": "two.", "at": 0.3}]}]}
    s.update(over)
    return s


def test_the_posted_round_two_reel_passes():
    assert reel_problems(R2) == []


def test_a_clean_spec_passes():
    assert reel_problems(spec()) == []


def test_length_is_28_to_33_seconds():
    assert any("keep it 28-33s" in p for p in reel_problems(spec(duration=40)))


def test_ring_on_a_below_par_mark_is_flagged_but_not_inside_a_both_sides_decision():
    s = spec()
    s["scenes"][0]["beats"] = [{"at": 1.0, "key": "B"}]
    assert any("below-par mark" in p for p in reel_problems(s))
    s["scenes"][0]["kind"] = "case_board"
    assert not any("below-par mark" in p for p in reel_problems(s))


def test_grid_cell_keys_are_read():
    s = spec()
    s["scenes"][0] = {"kind": "grid_heat", "start": 0, "end": 27,
                      "payload": {"cols": ["Powerplay", "Death"], "rows": [{"name": "X", "cells": [{"value": 2.0}, {"value": -4.0}]}]},
                      "beats": [{"at": 1, "key": "X · Death"}]}
    assert any("X · Death" in p for p in reel_problems(s))


def test_dwell_and_scene_time():
    s = spec()
    s["scenes"][0]["beats"] = [{"at": 1.0, "key": "A"}, {"at": 1.3, "key": "A2"}]
    assert any("hold each 0.6s" in p for p in reel_problems(s))
    s = spec()
    s["scenes"].insert(1, {"kind": "hero", "start": 26.5, "end": 27})
    assert any("needs 1.2s" in p for p in reel_problems(s))


def test_captions_one_line_and_off_at_the_close():
    s = spec(captions=[{"start": 0, "words": [{"w": w, "at": 0} for w in "one two three four five six".split()]}])
    assert any("at most 5" in p for p in reel_problems(s))
    s = spec()
    s["scenes"][1]["captions"] = True
    assert any("turn captions off" in p for p in reel_problems(s))


def test_kicker_and_send_line_fit_one_line():
    s = spec()
    s["scenes"][0]["kicker"] = "x" * 80
    s["scenes"][1]["data"]["send"]["text"] = "y" * 60
    probs = reel_problems(s)
    assert any("kicker is too long" in p for p in probs) and any("send line is too long" in p for p in probs)


def test_captions_from_timing_match_the_page():
    caps = reel_captions(R2)
    assert all(len(c["words"]) <= 5 for c in caps)
    assert " ".join(w["w"] for w in caps[0]["words"]) == "Rajat Patidar:"


def test_frame_keeps_out_of_instagrams_overlays():
    F = reel_frame()
    assert F["content"]["y"] + F["content"]["h"] <= 1500 and F["caption"]["y"] + F["caption"]["h"] <= 1600


def _video(tmp_path, src, name):
    import subprocess
    out = tmp_path / name
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src, "-t", "3", "-pix_fmt", "yuv420p", str(out)], check=True)
    return str(out)


def test_still_check_finds_a_held_frame_and_passes_a_moving_one(tmp_path):
    import shutil
    import pytest
    from services.social_rules import reel_still_problems
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    still = _video(tmp_path, "color=c=0x0a0c11:s=1080x1920:r=30", "still.mp4")
    moving = _video(tmp_path, "testsrc2=s=1080x1920:r=30", "moving.mp4")
    assert reel_still_problems(still)
    assert reel_still_problems(moving) == []
