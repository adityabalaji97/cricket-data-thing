"""Pre-queue check for a motion Reel: is every voiced line on screen? (owner, 19 Nov 2026: SMAT round 3's last line,
"Yash Dhull, 125 off 59", was voiced over the captions-off close and never appeared.)

    python scripts/reel_frame_check.py --placed placed.json [--mp4 reel.mp4 --out DIR]

1. The automatic part (no video needed): every number voiced must be readable while it is said, either in a caption
   (the scene has captions on) or in the scene's own text (kicker, payload, data). Misses print as MISS rows and the
   script exits 1.
2. With --mp4: a frame at each line's start (+0.25s) and middle, saved to DIR, and a contact sheet (sheet.png) for the
   reviewer to compare against the script, line by line (lines.txt). Grab them again after any re-record.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.ig_reel_v2 import _flatten, _short, numbers  # noqa: E402


def _scene_at(scenes: List[Dict[str, Any]], t: float) -> int:
    for i, s in enumerate(scenes):
        if s.get("start", 0) - 1e-3 <= t < s.get("end", float("inf")):
            return i
    return len(scenes) - 1


def _scene_text(s: Dict[str, Any]) -> set:
    shown = numbers(" ".join(_flatten({k: s.get(k) for k in ("kicker", "payload", "data", "title", "sample")})))
    return shown | {_short(n) for n in shown}


def uncovered(placed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Each voiced number not on screen while it is said: [{line, word, at, scene, kind}]."""
    timing = placed.get("timing") or {}
    scenes = placed.get("scenes") or []
    out = []
    for li, line in enumerate(timing.get("lines") or []):
        for w, at in zip(line.split(" "), timing["words"][li]):
            said = numbers(w)
            if not said:
                continue
            i = _scene_at(scenes, at)
            s = scenes[i]
            if s.get("captions") is not False:
                continue  # the caption shows the word as it is said
            shown = _scene_text(s)
            for n in said:
                if n not in shown and _short(n) not in shown:
                    out.append({"line": li, "word": w, "number": n, "at": round(at, 2), "scene": i + 1, "kind": s.get("kind")})
    return out


def grab(placed: Dict[str, Any], mp4: Path, out: Path) -> Path:
    """Frames at each line's start (+0.25s) and middle, and a contact sheet of them, two a row."""
    out.mkdir(parents=True, exist_ok=True)
    t = placed["timing"]
    frames, notes = [], []
    for li, line in enumerate(t["lines"]):
        a, n = t["starts"][li], t["lengths"][li]
        for tag, at in (("a", a + 0.25), ("b", a + n / 2)):
            f = out / f"line{li}{tag}.png"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", str(mp4), "-frames:v", "1",
                            "-vf", "scale=540:-1", str(f)], check=True)
            frames.append(f)
        notes.append(f"line {li} ({a:.1f}s, {a + n:.1f}s): {line}")
    (out / "lines.txt").write_text("\n".join(notes) + "\n")
    sheet = out / "sheet.png"
    # two frames a line, side by side; one line a row
    inputs = sum((["-i", str(f)] for f in frames), [])
    n = len(frames)
    rows = "".join(f"[{2 * r}:v][{2 * r + 1}:v]hstack=inputs=2[r{r}];" for r in range(n // 2))
    stack = "".join(f"[r{r}]" for r in range(n // 2)) + (f"vstack=inputs={n // 2}[o]" if n // 2 > 1 else "copy[o]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", rows + stack, "-map", "[o]",
                    "-frames:v", "1", str(sheet)], check=True)
    return sheet


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--placed", required=True, type=Path)
    ap.add_argument("--mp4", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    placed = json.loads(a.placed.read_text())
    misses = uncovered(placed)
    for m in misses:
        print(f"MISS line {m['line']} at {m['at']}s: '{m['number']}' ('{m['word']}') is voiced over scene {m['scene']} "
              f"({m['kind']}, captions off) and is not on screen")
    if a.mp4:
        print("frames:", grab(placed, a.mp4, a.out or a.mp4.parent / "frames"))
    print("numbers on screen:", "ok" if not misses else f"{len(misses)} missing")
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
