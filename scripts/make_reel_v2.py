"""
A Reel v2 (services/ig_reel_v2.py) for one queued post, out of the A/B: the post's Reel becomes the voiced one.

    python scripts/make_reel_v2.py --key ig:myth-note-34 [--beats 4,5,7] --out /tmp/varun.mp4          # preview only
    python scripts/make_reel_v2.py --key ig:myth-note-34 [--beats 4,5,7] --store                        # the post's Reel
    python scripts/make_reel_v2.py --key ig:preview-... --cards totals,form-strips,milestones --long --out /tmp/p.mp4

--cards: the same by card id (a preview's cards: services/ig_reel_v2.PREVIEW_BEATS is the default).
--beats: slide numbers to use (the first opens the Reel); default: services/ig_reel_v2.beats. With --store the Reel
replaces the post's in ig_reels, facts.reel records the script, and the caption gets the AI-voice line.
Voice and style: REEL_VOICE / REEL_TONE.
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
    parser.add_argument("--beats")
    parser.add_argument("--cards", help="card ids instead of slide numbers, e.g. totals,form-strips,milestones")
    parser.add_argument("--out")
    parser.add_argument("--store", action="store_true")
    parser.add_argument("--long", action="store_true", help="45-60 seconds, up to 5 charts")
    parser.add_argument("--close", default="", help="the closing question, word for word")
    parser.add_argument("--base", default=None)
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine, get_session
    from services import ig_reel_v2 as R
    from services.ig_captions import with_ai_voice

    db = next(get_session())
    row = db.execute(text("SELECT id, facts, caption FROM content_packs WHERE angle_key = :k"), {"k": args.key}).mappings().first()
    if not row:
        print("no such post")
        return 1
    cid = row["facts"]["carousel_id"]
    slides = db.execute(text("SELECT data FROM chart_snapshots WHERE id = :c"), {"c": cid}).scalar()["slides"]
    plan = {"beats": [int(n) for n in args.beats.split(",")]} if args.beats else None
    if args.cards:
        plan = {"beats": R.by_card_id(slides, [c.strip() for c in args.cards.split(",") if c.strip()])}
    if args.close:
        plan = {**(plan or {}), "close": args.close}
    out = Path(args.out) if args.out else None
    made = R.make(cid, slides, base=args.base or R.SITE, store=args.store, out=out, plan=plan,
                  length="long" if args.long else "short")
    if not made:
        print("no Reel: not enough beats, or no ffmpeg")
        return 1
    print(json.dumps({k: made[k] for k in ("seconds", "source", "voice", "beats", "length", "script")}, indent=2))
    if args.store:
        info = {"variant": "v2", **{k: made[k] for k in ("script", "source", "voice", "beats", "seconds", "length", "srt")}}
        with engine.begin() as conn:
            conn.execute(text("UPDATE content_packs SET caption = :c, facts = jsonb_set(COALESCE(facts, '{}'::jsonb), "
                              "'{reel}', CAST(:r AS jsonb)) WHERE id = :i"),
                         {"c": with_ai_voice(row["caption"] or ""), "r": json.dumps(info), "i": row["id"]})
        print("stored as the post's Reel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
