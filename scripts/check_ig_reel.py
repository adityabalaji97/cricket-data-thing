"""Check a motion Reel against the Reel rules (MOTION_REEL_PLAN.md M7; services/social_rules).

    python scripts/check_ig_reel.py reel.json [--video out.mp4]

Prints each problem, one a line, and exits 1 if there are any: the spec's length, scene times, dwell, captions,
kicker and send-line sizes, the frame against Instagram's overlays and rings on below-par marks; with --video, also the
longest still stretch in the recorded content zone (record it with scripts/record_ig_reel.mjs --mp4 --nodrift,
so the visuals' slow bob doesn't hide a still picture).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.social_rules import reel_problems, reel_still_problems  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--video")
    a = ap.parse_args()
    probs = reel_problems(json.loads(Path(a.spec).read_text()))
    if a.video:
        probs += reel_still_problems(a.video)
    for p in probs:
        print(p)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
