"""
The same Reel v2 in several voices, to choose the brand voice (services/ig_reel_v2.py). Saves nothing to the queue.

    python scripts/reel_voices.py --key ig:spotlight-captains-call-1529231 --voices ash,onyx,coral --out /tmp/voices \\
        [--base http://localhost:3000]

Writes <out>/<voice>.mp4 and <out>/script.json (one script for all of them, so only the voice differs).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True)
    parser.add_argument("--voices", default="ash,onyx,coral")
    parser.add_argument("--out", required=True)
    parser.add_argument("--base", default=None)
    args = parser.parse_args()

    from sqlalchemy import text

    from database import get_session
    from services import ig_reel_v2 as R

    db = next(get_session())
    fact = db.execute(text("SELECT facts FROM content_packs WHERE angle_key = :k"), {"k": args.key}).scalar()
    if not fact:
        print("no such post")
        return 1
    cid = fact["carousel_id"]
    slides = db.execute(text("SELECT data FROM chart_snapshots WHERE id = :c"), {"c": cid}).scalar()["slides"]
    hook = next((s.get("text") for s in slides if s.get("type") == "hook"), "")
    bs = R.beats(slides)
    sc, source = R.script(hook, bs)
    plan = {"script": sc, "source": source, "beats": [n for n, _ in bs]}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "script.json").write_text(json.dumps(plan, indent=2))
    print(json.dumps(plan, indent=2))
    for v in args.voices.split(","):
        made = R.make(cid, slides, voice=v, base=args.base or R.SITE, store=False, out=out / f"{v}.mp4", plan=plan)
        print(v, made and made["seconds"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
