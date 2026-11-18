"""
Voice timing for motion Reels (MOTION_REEL_PLAN.md M4): a script's spoken length against the budget, word timestamps,
and scenes and beats placed on the words that anchor them.

    spoken_count(line)               -> spoken words, counting each digit and "point" ("1.98" is four)
    budget_problems(lines)           -> what breaks the budget: 86 spoken words, about 2.8 a second, about 31s
    estimate(lines)                  -> a timing file (lines, starts, lengths, words) at 3 spoken words a second, no voice
    time_voice(lines, audio, lengths, transcribe=...)
                                     -> the timing file for a voiced script: line starts from the line lengths (as
                                        ig_reel_v2.align), word starts from word timestamps (ig_reel_v2.word_times)
    place(spec, timing)              -> the reel spec with every scene and beat set on its anchor word

A timing file is the shape the finished Reels wrote (lines, starts, lengths, words[line][word], audio), which the Reel
page also reads (spec.timing -> captions). The live word timestamps call is transcribe_words (whisper-1, word
granularity, one call a line), kept behind that function so tests and dry runs pass their own.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Sequence

RATE = 2.8            # spoken words a second: the live voice (marin, TEMPO 1.12) measured 2.65-2.95 on 18 Nov
BUDGET = 86           # spoken words that fit 33s at RATE with the gaps and hold (spec section 5 said 95 at 3.0)
HOLD = 0.6            # seconds the last frame holds after the voice ends
DWELL = 0.6           # a lit item holds this long before the next lights (frame.json rules.dwellMin)
LEAD = 0.0            # a scene starts on its anchor word (the Reel page's lift already brings it in 0.1s before)
GAP = 0.12            # seconds between voiced lines (ig_reel_v2.GAP)

_ONES = 20


def _int_words(n: int) -> int:
    """Spoken words in a whole number: 7 one, 62 two ("sixty two"), 135 four ("one hundred thirty five"), 2,950 five."""
    if n < 0:
        return 1 + _int_words(-n)
    if n <= _ONES or (n < 100 and n % 10 == 0):
        return 1
    if n < 100:
        return 2
    if n < 1000:
        return 2 + (_int_words(n % 100) if n % 100 else 0)
    if n < 1_000_000:
        return _int_words(n // 1000) + 1 + (_int_words(n % 1000) if n % 1000 else 0)
    return _int_words(n // 1_000_000) + 1 + (_int_words(n % 1_000_000) if n % 1_000_000 else 0)


def _token_words(tok: str) -> int:
    """Spoken words in one written token: a number by its digits (decimals digit by digit after "point"), a sign as a
    word ("minus", "plus"), a percent as "percent", "49*" as "49 not out"; any other token is one word."""
    t = tok.strip(",.?!;:()\"'’")
    m = re.fullmatch(r"([+−–-])?(\d[\d,]*)(?:\.(\d+))?(%|\*)?", t)
    if not m:
        return 1 if t else 0
    sign, whole, dec, suffix = m.groups()
    n = (1 if sign else 0) + _int_words(int(whole.replace(",", "")))
    if dec:
        n += 1 + len(dec)
    if suffix == "%":
        n += 1
    elif suffix == "*":
        n += 2
    return n


def spoken_count(line: str) -> int:
    """Spoken words in a line, counting each digit after a point and the "point" itself (spec section 5)."""
    return sum(_token_words(w) for w in line.split())


def budget_problems(lines: Sequence[str], budget: int = BUDGET, rate: float = RATE) -> List[str]:
    """What a Reel script breaks: more spoken words than the budget, so the voice would run past about 31s."""
    n = sum(spoken_count(x) for x in lines)
    out = []
    if n > budget:
        out.append(f"The script is {n} spoken words: keep it to {budget} (about {budget / rate:.0f}s at {rate:g} a second)")
    return out


def estimate(lines: Sequence[str], rate: float = RATE, gap: float = GAP) -> Dict[str, Any]:
    """A timing file with no voice: each word at its share of the line by spoken words, `rate` spoken words a second,
    `gap` between lines. For previews and fixtures; a voiced Reel uses time_voice."""
    starts, lengths, words, at = [], [], [], 0.0
    for line in lines:
        ws = line.split()
        counts = [_token_words(w) for w in ws]
        length = sum(counts) / rate
        t, acc = [], 0
        for c in counts:
            t.append(round(at + acc / rate, 3))
            acc += c
        starts.append(round(at, 3))
        lengths.append(round(length, 3))
        words.append(t)
        at += length + gap
    return {"lines": list(lines), "starts": starts, "lengths": lengths, "words": words,
            "audio": round(at - gap, 3) if lines else 0.0, "estimated": True}


def transcribe_words(audio: str, start: float, length: float) -> List[Dict[str, float]]:  # pragma: no cover - live
    """Word timestamps for one voiced line (whisper-1, word granularity), cut from `audio` at start..start+length.
    A paid call: only the Reel pipeline calls it, never tests."""
    import subprocess
    import tempfile
    from pathlib import Path

    from services.ig_reel_v2 import _client

    with tempfile.TemporaryDirectory() as tmp:
        seg = Path(tmp) / "seg.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", audio,
                        str(seg)], check=True)
        with open(seg, "rb") as f:
            tr = _client().audio.transcriptions.create(model="whisper-1", file=f, response_format="verbose_json",
                                                      timestamp_granularities=["word"])
    return [{"word": w.word, "start": w.start} for w in (tr.words or [])]


def _fatal(exc: Exception) -> bool:
    """An error no retry or fallback fixes: authentication or permission (HTTP 401/403, openai's
    AuthenticationError and PermissionDeniedError)."""
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    return status in (401, 403) or type(exc).__name__ in ("AuthenticationError", "PermissionDeniedError")


def time_voice(lines: Sequence[str], audio: str, lengths: Sequence[float], audio_seconds: Optional[float] = None,
               transcribe: Optional[Callable[[str, float, float], List[Dict[str, float]]]] = None) -> Dict[str, Any]:
    """The timing file for a voiced script: line starts from the voiced line lengths (lines are voiced one per take
    with GAP between, ig_reel_v2.align), and word starts from `transcribe`'s word timestamps matched to our words
    (ig_reel_v2.word_times; a line whose transcription fails is placed by characters)."""
    from services.ig_reel_v2 import align, word_times

    starts, _ = align(list(lines), list(lengths))
    words = []
    for line, s, length in zip(lines, starts, lengths):
        try:
            timed = (transcribe or transcribe_words)(audio, s, length)  # looked up now, so a test's fake is used
        except Exception as exc:  # noqa: BLE001 - a missing timestamp places the line by characters...
            if _fatal(exc):        # ...but a bad key or a refused account fails every line: say so, don't guess
                raise
            timed = []
        words.append([round(s + x, 3) for x in word_times(line.split(), timed, length)])
    total = audio_seconds if audio_seconds is not None else (starts[-1] + lengths[-1] if lines else 0.0)
    return {"lines": list(lines), "starts": starts, "lengths": [round(x, 3) for x in lengths], "words": words,
            "audio": round(total, 3)}


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def word_at(timing: Dict[str, Any], anchor: Any, after: float = -1.0) -> float:
    """When an anchor word is spoken. anchor: {"line": i, "word": j} (j defaults to 0), or text: the first time that
    word (or run of words) is said at or after `after`. Raises KeyError when the text is never said."""
    if isinstance(anchor, dict):
        return timing["words"][anchor["line"]][anchor.get("word", 0)]
    want = [_norm(w) for w in str(anchor).split()]
    for li, line in enumerate(timing["lines"]):
        ws = [_norm(w) for w in line.split()]
        for j in range(len(ws) - len(want) + 1):
            if ws[j:j + len(want)] == want and timing["words"][li][j] >= after - 1e-6:
                return timing["words"][li][j]
    raise KeyError(f"anchor {anchor!r} is not in the script")


def place(spec: Dict[str, Any], timing: Dict[str, Any], lead: float = LEAD, hold: float = HOLD) -> Dict[str, Any]:
    """The reel spec with its times set from the voice: each scene starts `lead` (0) before its `anchor` word (the first
    scene at 0) and ends where the next starts; every dict inside a scene with an `anchor` (beats, a badge, a send line,
    a second player) gets `at` = that word's time, searched from the scene's start; chapters follow their scenes
    (scene.chapter); the Reel lasts the voice plus `hold`. The timing file goes in as spec.timing (captions)."""
    import copy

    out = copy.deepcopy(spec)
    scenes = out["scenes"]
    for i, s in enumerate(scenes):
        if i == 0:
            s["start"] = 0.0
        elif "anchor" in s:
            s["start"] = round(max(0.0, word_at(timing, s["anchor"], scenes[i - 1]["start"]) - lead), 3)
    total = round((timing.get("audio") or (timing["starts"][-1] + timing["lengths"][-1])) + hold, 3)
    for i, s in enumerate(scenes):
        s["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else total

        def walk(o: Any, floor: float) -> None:
            if isinstance(o, dict):
                if "anchor" in o and o is not s:
                    o["at"] = round(word_at(timing, o["anchor"], floor), 3)
                for v in o.values():
                    walk(v, floor)
            elif isinstance(o, list):
                for v in o:
                    walk(v, floor)
        walk(s, s["start"])
        # a lit item holds DWELL before the next lights (names said in a quick list): the next ring waits, or, if it
        # can't light before the scene ends, is dropped (the voice still says the name; the check's 0.6s holds)
        held, last = [], None
        for b in sorted((b for b in s.get("beats") or [] if "at" in b), key=lambda b: b["at"]):
            if last is not None and b["at"] < last + DWELL:
                b["at"] = round(last + DWELL, 3)
            if b["at"] < s["end"] - 0.2:
                held.append(b)
                last = b["at"]
        if s.get("beats"):
            s["beats"] = held + [b for b in s["beats"] if "at" not in b]
        # a board dealt in while its first line is said: the chips keep landing until the voice reaches the first name,
        # so the board is never a still picture before it (M7)
        if s.get("kind") == "squad_board" and held:
            n = sum(len(g.get("players") or []) for g in (s.get("payload") or {}).get("groups") or [])
            if n:
                s.setdefault("plan", {})["stagger"] = round(min(0.25, max(0.03, (held[0]["at"] - s["start"] - 0.5) / n)), 3)
    if out.get("chapters"):
        for k, ch in enumerate(out["chapters"]):
            mine = [s for s in scenes if s.get("chapter") == k]
            if mine:
                ch["start"], ch["end"] = mine[0]["start"], mine[-1]["end"]
    out["duration"] = total
    out["timing"] = {k: timing[k] for k in ("lines", "starts", "lengths", "words")}
    return out
