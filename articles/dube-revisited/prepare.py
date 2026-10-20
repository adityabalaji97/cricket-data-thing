"""
Get "Dube, revisited" ready to publish, as drafts only (nothing here posts anywhere):

  1. both carousels (article images, Instagram deck) saved to PRODUCTION as snapshots
  2. the same rows copied into the LOCAL database, rendered by the local frontend (scripts/render_ig_slides.mjs,
     which has the ScatterPlus fix before it's deployed) and the PNGs stored in production, with the Reel
  3. a draft note on the site (kind 'article', author: Aditya), its images the stored slides
  4. the Instagram pack queued for --date (default: the bench, no day) with the hand-written caption and X thread (social.md)

    python articles/dube-revisited/prepare.py                 # dry run: print the plan
    python articles/dube-revisited/prepare.py --write          # do it (local API on :8000, frontend on :3000)
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
# The voiced v2 Reel, always (no day A/B), recorded from the local frontend: it has the ScatterPlus fix before it's
# deployed, and reads the same snapshot rows (copy_to_local).
os.environ.update(REEL_V2="1", REEL_AB="0", REEL_BASE="http://localhost:3000")

LOCAL_URL = "postgresql://localhost:5432/hindsight_local"
SLUG = "dube-revisited"
KEY = "spotlight-dube-revisited"
AUTHOR_ID = 34  # note_authors: Aditya Balaji
TITLE = "Dube, revisited"
from build_cards import HOOK  # noqa: E402


def social() -> tuple[str, list[tuple[int, str]]]:
    """The caption, and the thread as (slide, text) from social.md's "n/ [slide k] ..." tweets."""
    text = (HERE / "social.md").read_text()
    thread_md, caption_md = text.split("## Instagram caption", 1)
    tweets = []
    for t in re.split(r"\n(?=\d/ )", thread_md):
        m = re.match(r"(\d+/) \[slide (\d+)\] (.*)", t.strip(), re.S)
        if m:
            tweets.append((int(m.group(2)), f"{m.group(1)} {m.group(3)}"))
    return caption_md.strip(), tweets


def note_body(article_id: str) -> tuple[str, str]:
    md = (HERE / "draft.md").read_text()
    lines = md.split("\n")
    dek = lines[2].strip().strip("*")
    body = "\n".join(lines[3:]).strip()
    body = re.sub(r"\]\(article/(\d)\.png\)", lambda m: f"](/api/snapshots/{article_id}/slides/{m.group(1)}.png)", body)
    return dek, body


def copy_to_local(snap_id: str, prod_engine, local_engine) -> None:
    from sqlalchemy import text

    with prod_engine.connect() as c:
        row = c.execute(text("SELECT id, kind, params, params_hash, data, title, created_by FROM chart_snapshots WHERE id = :i"),
                        {"i": snap_id}).mappings().first()
    import json

    with local_engine.begin() as c:
        c.execute(text("DELETE FROM chart_snapshots WHERE id = :i OR (kind = :k AND params_hash = :h)"),
                  {"i": row["id"], "k": row["kind"], "h": row["params_hash"]})
        c.execute(text("""INSERT INTO chart_snapshots (id, kind, params, params_hash, data, title, created_by)
                          VALUES (:id, :kind, CAST(:params AS jsonb), :params_hash, CAST(:data AS json), :title, :created_by)"""),
                  {**row, "params": json.dumps(row["params"]), "data": json.dumps(row["data"])})


def render_and_store(snap_id: str, count: int, prod_engine) -> int:
    from services import ig_slides

    with tempfile.TemporaryDirectory() as out:
        proc = subprocess.run(["node", str(ROOT / "scripts" / "render_ig_slides.mjs"), snap_id, str(count), out,
                               "--base", "http://localhost:3000"], capture_output=True, text=True, cwd=ROOT, timeout=600)
        files = sorted(Path(out).glob("*.png"), key=lambda f: int(f.stem))
        if len(files) != count:
            raise SystemExit(f"render of {snap_id} made {len(files)}/{count}: {proc.stdout[-300:]} {proc.stderr[-300:]}")
        with prod_engine.begin() as conn:
            for f in files:
                ig_slides.save(conn, snap_id, int(f.stem), f.read_bytes())
    return len(files)


def thread(tweets: list, slide_of: dict, link: str) -> list[dict]:
    return [{"n": i + 1, "text": t.replace("[post link]", link), "slide": k} for i, (k, t) in enumerate(tweets)]


def instagram_only(db, prod, local, tweets: list[str]) -> int:
    import json

    from sqlalchemy import text

    from build_cards import INSTAGRAM
    from services import ig_carousel, ig_slides
    from services.ig_links import post_link

    deck = [dict(s) for s in INSTAGRAM]
    ig = ig_carousel.save(db, deck, HOOK, {"article": SLUG, "set": "instagram", "cover": "hero"}, "article")
    copy_to_local(ig["id"], prod, local)
    print(f"instagram {ig['id']}: cover {deck[0].get('cover')}, rendered {render_and_store(ig['id'], len(deck), prod)}/{len(deck)}")
    with prod.begin() as conn:
        fact = conn.execute(text("SELECT facts FROM content_packs WHERE angle_key = :k"), {"k": f"ig:{KEY}"}).scalar()
        slide_of = {s.get("card", {}).get("id"): i + 1 for i, s in enumerate(deck) if s.get("card")}
        fact = {**fact, "carousel_id": ig["id"], "slides": len(deck), "cover": deck[0].get("cover")}
        fact["x"] = thread(tweets, slide_of, post_link(fact))
        conn.execute(text("UPDATE content_packs SET snapshot_id = :s, facts = CAST(:f AS jsonb) WHERE angle_key = :k"),
                     {"s": ig["id"], "f": json.dumps(fact, default=str), "k": f"ig:{KEY}"})
    print(f"reel: {ig_slides.reel_from_stored(ig['id'], len(deck))}s")  # after the pack points at this deck
    for t in fact["x"]:
        print(f"  tweet {t['n']} -> slide {t['slide']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--date", default="bench", help="the day the Instagram pack is planned for, or 'bench' (no day)")
    ap.add_argument("--instagram-only", action="store_true",
                    help="rebuild just the Instagram deck, its slides, Reel and thread, and point the queued pack at it")
    args = ap.parse_args()

    assert "localhost" not in os.environ.get("DATABASE_URL", ""), "this writes to production: leave DATABASE_URL unset"
    from sqlalchemy import create_engine

    from build_cards import ARTICLE, INSTAGRAM
    from database import engine as prod, get_session

    caption, tweets = social()
    print(f"article cards: {len(ARTICLE)} · instagram slides: {len(INSTAGRAM)} · tweets: {len(tweets)} · date {args.date}")
    for k, t in tweets:
        print(f"  slide {k} [{len(t)}] {t[:60]}…")
    if not args.write:
        print("dry run: nothing written")
        return 0

    from services import ig_backlog, ig_carousel, ig_slides
    from services.ig_links import post_link
    from services.notes import create_note
    from services.snapshots import create_static_snapshot

    db = next(get_session())
    local = create_engine(LOCAL_URL)

    if args.instagram_only:
        return instagram_only(db, prod, local, tweets)

    # 1. Carousels in production.
    article_slides = [{"type": "card", "card": c, "teams": None} for c in ARTICLE]
    art = create_static_snapshot(db, "carousel", {"slides": article_slides, "title": f"{TITLE} (article)"}, f"{TITLE} (article)",
                                 {"article": SLUG, "set": "article", "slides": article_slides}, created_by="article")
    deck = [dict(s) for s in INSTAGRAM]
    ig = ig_carousel.save(db, deck, HOOK, {"article": SLUG, "set": "instagram"}, "article")
    print(f"carousels: article {art['id']} ({len(article_slides)}), instagram {ig['id']} ({len(deck)})")

    # 2. Render locally (same rows), store in production, then the Reel.
    for sid, n in ((art["id"], len(article_slides)), (ig["id"], len(deck))):
        copy_to_local(sid, prod, local)
        print(f"rendered {sid}: {render_and_store(sid, n, prod)}/{n}")

    # 3. The site note, a draft.
    dek, body = note_body(art["id"])
    note = create_note(db, title=TITLE, author_id=AUTHOR_ID, body_md=body, dek=dek, kind="article", slug=SLUG)
    print(f"note: draft {note['id']} /notes/{note['slug']}")

    # 4. The Instagram pack, with the hand-written X thread (extras_pending only fills a thread that's missing).
    ids = [s.get("card", {}).get("id") for s in deck]
    slide_of = {cid: i + 1 for i, cid in enumerate(ids) if cid}
    fact = {"kind": "article", "title": HOOK, "hook": HOOK, "subject": "Shivam Dube", "carousel_id": ig["id"],
            "slides": len(deck), "note_id": note["id"], "note_slug": note["slug"], "link": f"/notes/{note['slug']}",
            "article_carousel_id": art["id"], "render": False}
    link = post_link(fact)
    fact["x"] = thread(tweets, slide_of, link)
    post = {"key": KEY, "pillar": "reactive", "fact": fact, "snapshot_id": ig["id"], "warnings": [],
            "players": ["Shivam Dube"], "caption": caption}
    with prod.begin() as conn:
        ig_backlog.upsert_pack(conn, post, None if args.date == "bench" else date.fromisoformat(args.date), source="article")
    print(f"queued ig:{KEY} for {args.date}")
    # After the pack exists: the voiced v2 Reel finds its post through the pack (ig_reel_v2.for_carousel).
    print(f"reel: {ig_slides.reel_from_stored(ig['id'], len(deck))}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
