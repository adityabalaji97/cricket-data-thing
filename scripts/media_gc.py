"""
Delete rendered media (slide PNGs in ig_slide_images, Reels in ig_reels) nothing needs any more. The carousels
themselves (chart_snapshots) are never touched, so anything deleted can be rendered again; /img/<id>.png (share images,
the /links page) draws from the snapshot, not from these files.

Kept:
  - a carousel a ready post uses (the queue and the bench), anywhere in its pack (snapshot_id or any id in its facts)
  - a carousel a site note shows (its images are /api/snapshots/<id>/slides/<n>.png)
  - an article / reply / storylines set from the last HAND_DAYS days (sets made by hand, downloaded by hand)
  - anything made in the last GRACE_DAYS days (a post being built has its carousel before its pack)
Deleted:
  - media of posts that are posted (GRACE_DAYS after their day: the YouTube Short may go up later), expired or skipped
  - media no post or note uses (versions a rebuild replaced)

    python scripts/media_gc.py              # dry run: what would go, and how much
    python scripts/media_gc.py --write      # delete
    python scripts/media_gc.py --write --vacuum   # and give the space back (VACUUM FULL: locks the two tables briefly)
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GRACE_DAYS = 2
HAND_DAYS = 14

DOOMED = f"""
    WITH media AS (
        SELECT DISTINCT carousel_id FROM ig_slide_images UNION SELECT carousel_id FROM ig_reels
    ),
    uses AS (
        SELECT m.carousel_id, p.status, p.planned_for FROM media m
        JOIN content_packs p ON p.snapshot_id = m.carousel_id OR p.facts::text LIKE '%' || m.carousel_id || '%'
    )
    SELECT m.carousel_id FROM media m
    LEFT JOIN chart_snapshots s ON s.id = m.carousel_id
    WHERE NOT EXISTS (SELECT 1 FROM uses u WHERE u.carousel_id = m.carousel_id
                      AND (u.status = 'ready'
                           OR (u.status = 'posted' AND u.planned_for >= CURRENT_DATE - {GRACE_DAYS})))
      AND NOT EXISTS (SELECT 1 FROM notes n WHERE n.body_md LIKE '%' || m.carousel_id || '%')
      AND NOT (s.created_by IN ('article', 'reply', 'storylines') AND s.created_at >= now() - interval '{HAND_DAYS} days')
      AND COALESCE(s.created_at, now() - interval '1 year') < now() - interval '{GRACE_DAYS} days'
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--vacuum", action="store_true", help="VACUUM FULL the two media tables afterwards")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine

    with engine.begin() as conn:
        ids = conn.execute(text(DOOMED)).scalars().all()
        size = conn.execute(text("""
            SELECT COALESCE((SELECT SUM(octet_length(png)) FROM ig_slide_images WHERE carousel_id = ANY(:i)), 0)
                 + COALESCE((SELECT SUM(octet_length(mp4) + COALESCE(octet_length(short_mp4), 0)) FROM ig_reels
                             WHERE carousel_id = ANY(:i)), 0)
        """), {"i": ids}).scalar()
        print(f"{len(ids)} carousels' media, {size / 1e6:.0f} MB" + ("" if args.write else " (dry run: nothing deleted)"))
        if args.write and ids:
            s = conn.execute(text("DELETE FROM ig_slide_images WHERE carousel_id = ANY(:i)"), {"i": ids}).rowcount
            r = conn.execute(text("DELETE FROM ig_reels WHERE carousel_id = ANY(:i)"), {"i": ids}).rowcount
            print(f"deleted {s} slide images, {r} Reels")
    if args.write and args.vacuum:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for t in ("ig_reels", "ig_slide_images"):
                conn.execute(text(f"VACUUM FULL {t}"))
            print("vacuumed: " + ", ".join(f"{t} {conn.execute(text(f'SELECT pg_size_pretty(pg_total_relation_size(:t))'), {'t': t}).scalar()}"
                                         for t in ("ig_reels", "ig_slide_images")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
