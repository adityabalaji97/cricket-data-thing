"""Voice timing for motion Reels (MOTION_REEL_PLAN.md M4): tested on the two finished Reels' timing files, no voice
and no transcription calls (the live call is replaced by a fake)."""
import json
from pathlib import Path

import pytest

from services import reel_timing as T

ROOT = Path(__file__).resolve().parents[1]
R2 = json.loads((ROOT / "tests/fixtures/reel_timing/smat_round2.json").read_text())
DHONI = json.loads((ROOT / "tests/fixtures/reel_timing/dhoni.json").read_text())
R2_SPEC = json.loads((ROOT / "src/components/ig/reel/__fixtures__/smat_round2.reel.json").read_text())


def test_spoken_count_counts_digits_and_point():
    assert T.spoken_count("Bumrah added 1.98 wins.") == 3 + 4  # "one point nine eight"
    assert T.spoken_count("135* off 48") == 4 + 2 + 1 + 2       # "one hundred thirty five not out off forty eight"
    assert T.spoken_count("−0.56 wins") == 1 + 1 + 1 + 2 + 1    # "minus zero point five six wins"
    assert T.spoken_count("2,950 runs") == 5 + 1                # "two thousand nine hundred fifty"
    assert T.spoken_count("54%") == 3


def test_the_budget_matches_the_voices_measured_rate():
    # The budget is what fits 33s at the live voice's rate (2.8 spoken words a second; MI's retention takes 18 Nov ran
    # 2.65-2.9). The Dhoni Reel (79 words) fits; the round-2 Reel's 91 words fit only because that older voice ran
    # 2.96 a second: today it would be flagged, as MI's 95- and 89-word takes (33.7s, 33.0s) should have been.
    assert T.budget_problems(DHONI["lines"]) == []
    assert T.budget_problems(R2["lines"])
    assert T.BUDGET / T.RATE + T.GAP * 6 + 0.6 <= 33.0   # the budget, voiced at RATE with 7 lines and the hold
    assert T.budget_problems(R2["lines"] * 2)  # twice as long: over budget


def test_estimate_is_about_three_spoken_words_a_second():
    est = T.estimate(R2["lines"])
    words = sum(T.spoken_count(x) for x in R2["lines"])
    assert abs(est["audio"] - (words / T.RATE + T.GAP * (len(R2["lines"]) - 1))) < 0.01
    # the voiced Reel is within 25% of the estimate (it was spoken a little faster)
    assert 0.75 < R2["audio"] / est["audio"] < 1.25
    assert all(a <= b for line in est["words"] for a, b in zip(line, line[1:]))


def test_word_at_by_text_and_by_index():
    assert T.word_at(R2, "Suryakumar") == R2["words"][2][0]
    assert T.word_at(R2, {"line": 5, "word": 9}) == R2["words"][5][9]
    assert T.word_at(R2, "the most") == R2["words"][1][14]   # a run of words, the first time it's said
    with pytest.raises(KeyError):
        T.word_at(R2, "Kohli")


def _anchored_round2():
    """The posted round-2 Reel's spec with every time replaced by the word it was cut on."""
    spec = json.loads(json.dumps(R2_SPEC))
    for s in spec["scenes"]:
        s.pop("start"), s.pop("end")
    hero, best, pool, pick = spec["scenes"]
    hero["data"]["sub"]["anchor"] = {"line": 1}
    hero["data"]["badge"]["anchor"] = "the most"
    best["anchor"] = "Suryakumar"
    best["beats"] = [{"anchor": "Suryakumar", "key": "Suryakumar Yadav"}, {"anchor": "Sanju", "key": "Sanju Samson"},
                     {"anchor": "Mayank", "key": "Mayank Yadav"}]
    pool["anchor"] = "But the best"
    pool["data"]["card"]["anchor"] = {"line": 5, "word": 9}  # cut on "team.", just before the name (as posted)
    pick["anchor"] = "Bid or pass"
    pick["data"]["send"]["anchor"] = "Send"
    for k, s in enumerate(spec["scenes"]):
        s["chapter"] = k
    return spec


def test_place_reproduces_the_hand_cut_round_two_reel():
    placed = T.place(_anchored_round2(), R2)
    for got, want in zip(placed["scenes"], R2_SPEC["scenes"]):
        assert got["start"] == pytest.approx(want["start"], abs=1e-3)
        assert got["end"] == pytest.approx(want["end"], abs=1e-3)
    hero, best, pool, pick = placed["scenes"]
    assert hero["data"]["badge"]["at"] == pytest.approx(R2_SPEC["scenes"][0]["data"]["badge"]["at"], abs=1e-3)
    assert [b["at"] for b in best["beats"]] == pytest.approx([b["at"] for b in R2_SPEC["scenes"][1]["beats"]], abs=1e-3)
    assert pool["data"]["card"]["at"] == pytest.approx(R2_SPEC["scenes"][2]["data"]["card"]["at"], abs=1e-3)
    assert pick["data"]["send"]["at"] == pytest.approx(R2_SPEC["scenes"][3]["data"]["send"]["at"], abs=1e-3)
    assert placed["duration"] == pytest.approx(R2_SPEC["duration"], abs=1e-3)
    assert [c["start"] for c in placed["chapters"]] == pytest.approx([c["start"] for c in R2_SPEC["chapters"]], abs=1e-3)


def test_placed_reel_passes_the_reel_checks():
    from services.social_rules import reel_problems
    assert reel_problems(T.place(_anchored_round2(), R2)) == []


def test_time_voice_uses_the_transcription_and_survives_its_failure():
    lines = DHONI["lines"][:2]
    lengths = DHONI["lengths"][:2]

    def fake(audio, start, length):
        # every word said 0.25s apart from the line's start (a stand-in for whisper)
        n = len(lines[0].split()) if start == 0 else len(lines[1].split())
        return [{"word": w, "start": 0.25 * i} for i, w in enumerate((lines[0] if start == 0 else lines[1]).split())][:n]

    t = T.time_voice(lines, "voice.mp3", lengths, transcribe=fake)
    assert t["starts"][0] == 0 and t["starts"][1] == pytest.approx(lengths[0] + T.GAP, abs=1e-3)
    assert t["words"][0][:3] == pytest.approx([0, 0.25, 0.5])

    def broken(audio, start, length):
        raise RuntimeError("no network")
    t2 = T.time_voice(lines, "voice.mp3", lengths, transcribe=broken)
    assert len(t2["words"][0]) == len(lines[0].split())  # placed by characters instead
