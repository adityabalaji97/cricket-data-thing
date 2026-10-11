#!/usr/bin/env python3
"""
Weekly adoption check-in (growth plan G0): prints the same numbers as GET /admin/usage.

    python scripts/usage_report.py            # last 8 weeks
    python scripts/usage_report.py --weeks 12 --json

Reads the production database via DATABASE_URL (.env), read-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Rolling targets from the growth plan; the report flags the current stage's gap.
TARGETS = [
    ("Next 4 weeks", {"users": 100}),
    ("BBL / SA20 / ILT20 (Dec-Jan)", {"users": 500, "distinct_callers": 10}),
    ("IPL 2027 (Mar-May)", {"users": 3000}),
]

COLUMNS = [
    ("users", "WAU"), ("returning_users", "return"), ("sessions", "sess"), ("page_views", "views"),
    ("query_runs", "queries"), ("nl_searches", "NL"), ("game_players", "gamers"), ("shares", "shares"),
    ("calls", "MCP calls"), ("distinct_callers", "MCP users"),
]
# Notes reach: posts and views, embeds on other sites (and visits they send), packs posted (and visits).
NOTES_COLUMNS = [
    ("notes_published", "notes"), ("note_views", "note views"), ("embeds_created", "embeds made"),
    ("embed_views", "embed views"), ("embed_hosts", "embed sites"), ("embed_visitors", "from embeds"),
    ("packs_posted", "packs posted"), ("pack_visitors", "from packs"), ("instagram_visitors", "from Instagram"),
    ("youtube_visitors", "from YouTube"),
    ("x_visitors", "from X"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weeks", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from sqlalchemy.sql import text

    from database import get_session
    from services.usage_report import build_usage_report

    db = next(get_session())
    db.execute(text("SET TRANSACTION READ ONLY"))
    report = build_usage_report(db, args.weeks)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return

    for columns, width in ((COLUMNS, 10), (NOTES_COLUMNS, 13)):
        header = f"{'week':<11}" + "".join(f"{label:>{width}}" for _, label in columns)
        print(header)
        print("-" * len(header))
        for week in report["weeks"]:
            print(f"{week['week']:<11}" + "".join(f"{week.get(key, 0) or 0:>{width}}" for key, _ in columns))
        print()

    latest = report["weeks"][0] if report["weeks"] else {}
    stage, goals = TARGETS[0]
    gaps = ", ".join(f"{k} {latest.get(k, 0) or 0}/{v}" for k, v in goals.items())
    print(f"\nTarget ({stage}): {gaps}")

    last7 = report["last_7_days"]
    for title, key, label in (("Top pages", "top_pages", "path"), ("Sources", "referrers", "source"),
                              ("Countries", "countries", "country")):
        items = ", ".join(f"{row[label]} ({row.get('users') or row.get('views')})" for row in last7[key][:8])
        print(f"{title} (7d): {items or '-'}")

    reels(db)


def reels(db) -> None:
    """Reel v1 (the slideshow) against v2 (voiced, captioned, payoff-first): the stats typed into admin per post."""
    from sqlalchemy.sql import text

    rows = db.execute(text("""
        SELECT COALESCE(facts->'reel'->>'variant', 'v1') AS variant, COUNT(*) AS posts,
               AVG((facts->'reel_stats'->>'views')::float) AS views,
               AVG((facts->'reel_stats'->>'avg_watch_s')::float) AS watch,
               AVG((facts->'reel_stats'->>'hold_3s_pct')::float) AS hold,
               AVG((facts->'reel_stats'->>'shares')::float) AS shares,
               AVG((facts->'reel_stats'->>'saves')::float) AS saves
        FROM content_packs WHERE channel = 'instagram' AND facts ? 'reel_stats'
        GROUP BY 1 ORDER BY 1
    """)).mappings().all()
    if not rows:
        return
    print("\nReels (stats from admin): variant, posts, avg views, avg watch (s), 3s hold %, shares, saves")
    fmt = lambda v, p=1: "-" if v is None else f"{v:.{p}f}"  # noqa: E731
    for r in rows:
        print(f"  {r['variant']:<3} {r['posts']:>3} {fmt(r['views'], 0):>8} {fmt(r['watch']):>6} {fmt(r['hold']):>6} "
              f"{fmt(r['shares']):>5} {fmt(r['saves']):>5}")


if __name__ == "__main__":
    main()
