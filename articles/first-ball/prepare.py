"""
Get the first-ball post ready, as drafts only (nothing here posts anywhere):

  1. the Instagram deck (cards.CARDS, chart cover: player and number first) saved to PRODUCTION as a carousel
  2. a reply set (the four player cards, no slide counter) saved the same way
  3. both rendered by the live site and the PNGs stored in production
  4. the pack queued on the bench (or --date) with the caption, X thread and YouTube copy, then the voiced v2 Reel

    python articles/first-ball/prepare.py            # dry run: print the plan
    python articles/first-ball/prepare.py --write    # do it
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
# The live site renders the slides (the chart code is deployed, #168) and reads the production rows directly.
BASE = "https://hindsightcricket.com"
os.environ.update(REEL_V2="1", REEL_AB="0", REEL_BASE=BASE)

KEY = "spotlight-first-ball-boundaries"
TITLE = "First ball"
LINK = ("/query?start_date=2023-01-01&dimension_filters=batter_ball_number%3Aeq%3A1&group_by=batter&min_balls=60"
        "&metrics_perspective=batting&fmt=mens-t20")
REPLY_IDS = ["scatter", "kohli", "six-share", "attackers"]


def social() -> tuple[str, list[tuple[int, str]]]:
    text = (HERE / "social.md").read_text()
    thread_md, caption_md = text.split("## Instagram caption", 1)
    tweets = []
    for t in re.split(r"\n(?=\d/ )", thread_md):
        m = re.match(r"(\d+/) \[slide (\d+)\] (.*)", t.strip(), re.S)
        if m:
            tweets.append((int(m.group(2)), f"{m.group(1)} {m.group(3)}"))
    return caption_md.strip(), tweets


def x_len(t: str) -> int:
    return len(re.sub(r"\S*hindsightcricket\.com\S*|\[post link\]", "x" * 23, t))


def render_and_store(snap_id: str, count: int, prod_engine, keep: Path | None = None) -> int:
    """Render each slide (one at a time, retried: the dev server's first loads are slow) and store it in production."""
    from services import ig_slides

    with tempfile.TemporaryDirectory() as out:
        for n in range(1, count + 1):
            for _ in range(3):
                try:
                    proc = subprocess.run(["node", str(HERE / "render_one.mjs"), snap_id, str(n), f"{out}/{n}.png", BASE],
                                          capture_output=True, text=True, cwd=ROOT, timeout=240)
                except subprocess.TimeoutExpired:  # a hung headless page: try again
                    continue
                if proc.stdout.strip() == "ready":
                    break
            else:
                raise SystemExit(f"slide {n} of {snap_id} never rendered")
        files = sorted(Path(out).glob("*.png"), key=lambda f: int(f.stem))
        with prod_engine.begin() as conn:
            for f in files:
                ig_slides.save(conn, snap_id, int(f.stem), f.read_bytes())
                if keep:
                    keep.mkdir(parents=True, exist_ok=True)
                    (keep / f.name).write_bytes(f.read_bytes())
    return len(files)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--date", default="bench", help="the day the pack is planned for, or 'bench' (no day)")
    args = ap.parse_args()

    assert "localhost" not in os.environ.get("DATABASE_URL", ""), "this writes to production: leave DATABASE_URL unset"
    from cards import CARDS

    caption, tweets = social()
    print(f"slides: {len(CARDS)} · tweets: {len(tweets)} · date {args.date}")
    for k, t in tweets:
        print(f"  slide {k} [{x_len(t)}] {t[:70]}…")
    too_long = [k for k, t in tweets if x_len(t) > 280]
    assert not too_long, f"tweets over 280: slides {too_long}"
    assert sorted({k for k, _ in tweets}) == list(range(1, len(CARDS) + 1)), "every slide needs a tweet and every tweet a slide"
    if not args.write:
        print("dry run: nothing written")
        return 0

    from sqlalchemy import text

    from database import engine as prod, get_session
    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_links import post_link
    from services.ig_notes import youtube_copy
    from services.snapshots import create_static_snapshot

    db = next(get_session())

    # 1-2. Deck and reply set in production.
    deck = [{"type": "card", "card": c, "teams": None} for c in CARDS]
    hook = CARDS[0]["title"]
    ig = ig_carousel.save(db, deck, hook, {"article": "first-ball", "set": "instagram"}, "article")
    reply = [{"type": "card", "card": c, "teams": None} for c in CARDS if c["id"] in REPLY_IDS]
    rep = create_static_snapshot(db, "carousel", {"slides": reply, "title": f"{TITLE} (reply)", "counter": False},
                                 f"{TITLE} (reply)", {"article": "first-ball", "set": "reply", "slides": reply}, created_by="reply")
    print(f"carousels: instagram {ig['id']} ({len(deck)}), reply {rep['id']} ({len(reply)})")

    # 3. Render on the live site, store in production.
    for sid, n, keep in ((ig["id"], len(deck), None), (rep["id"], len(reply), HERE / "reply")):
        print(f"rendered {sid}: {render_and_store(sid, n, prod, keep)}/{n}")

    # 4. The pack on the bench, then the Reel (it finds its post through the pack).
    fact = {"kind": "spotlight", "title": hook, "hook": hook, "subject": "Vaibhav Sooryavanshi", "subject_role": "stat",
            "carousel_id": ig["id"], "slides": len(deck), "link": LINK, "render": False,
            "reply_carousel_id": rep["id"]}
    link = post_link(fact)
    fact["x"] = [{"n": i + 1, "text": t.replace("[post link]", link), "slide": k} for i, (k, t) in enumerate(tweets)]
    fact["youtube"] = youtube_copy(fact, caption, hook)
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": ig["id"], "warnings": [],
            "players": ["Vaibhav Sooryavanshi", "Abhishek Sharma", "Sanju Samson", "Virat Kohli"], "caption": caption}
    with prod.begin() as conn:
        ig_backlog.upsert_pack(conn, post, None if args.date == "bench" else date.fromisoformat(args.date), source="article")
        warns = conn.execute(text("SELECT rule_warnings FROM content_packs WHERE angle_key = :k"), {"k": f"ig:{KEY}"}).scalar()
    print(f"queued ig:{KEY} for {args.date} · slide-check warnings: {warns or 'none'}")
    print(f"reel: {ig_slides.reel_from_stored(ig['id'], len(deck))}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
