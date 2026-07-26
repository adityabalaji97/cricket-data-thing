#!/usr/bin/env python3
"""Recompute batting_stats / bowling_stats for matches whose stored rows are wrong.

Why this exists
---------------
`sync_stats_from_dd.py` had two counting bugs that corrupted every row it wrote:

1. `delivery_details.out` and `bat_out` are VARCHAR holding 'true'/'false', not booleans, and
   the code tested them with plain truthiness. The string 'false' is truthy, so **every ball
   counted as a wicket**. 34% of stored T20 batting rows carry an impossible `wickets > 1`,
   rising to 93% of 2026 rows, with a maximum of 76 wickets for one batter in one innings.
2. Wides were counted as balls faced. A wide is not a ball faced, so `balls_faced`, `dots` and
   `strike_rate` are all slightly overstated.

This is user-visible, not cosmetic: the query builder's `query_mode=batting_stats` divides runs
by `wickets` to get a batting average, which currently reports figures like 2.61 for a batter
averaging around 30.

Both bugs are fixed in `sync_stats_from_dd.py`; this script repairs the data already written.

Scope
-----
Only matches whose ball-by-ball data lives in `delivery_details`, because those are the ones
the buggy path wrote. Rows derived from the legacy `deliveries` table by `statsProcessor.py`
are clean (verified: zero impossible wicket counts before 2015) and are left alone.

Usage
-----
    python scripts/backfill_recompute_stats.py --dry-run            # report only, no writes
    python scripts/backfill_recompute_stats.py --limit 50           # try a small batch first
    python scripts/backfill_recompute_stats.py --confirm            # full run

Take a database backup before running with --confirm against production.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402
from tqdm import tqdm  # noqa: E402

from database import get_database_connection  # noqa: E402
from sync_stats_from_dd import StatsFromDeliveryDetails  # noqa: E402


def affected_match_ids(session, fmt=None, limit=None):
    """Matches that have stored stats derived from delivery_details."""
    clauses = ["bs.match_id IS NOT NULL"]
    params = {}
    if fmt:
        clauses.append("dd.format = :fmt")
        params["fmt"] = fmt

    query = f"""
        SELECT DISTINCT dd.p_match
        FROM delivery_details dd
        JOIN batting_stats bs ON bs.match_id = dd.p_match
        WHERE {' AND '.join(clauses)}
        ORDER BY dd.p_match
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    return [row[0] for row in session.execute(text(query), params).fetchall()]


def report(session) -> None:
    """Show how bad the stored data is, before and after."""
    rows = session.execute(
        text(
            """
            SELECT format,
                   count(*) AS total,
                   count(*) FILTER (WHERE wickets > 1) AS impossible,
                   round(avg(wickets)::numeric, 3) AS avg_wickets,
                   max(wickets) AS max_wickets
            FROM batting_stats
            GROUP BY format ORDER BY format
            """
        )
    ).fetchall()
    print(f"  {'format':8} {'rows':>8} {'wickets>1':>10} {'avg':>8} {'max':>6}")
    for r in rows:
        print(f"  {r.format:8} {r.total:>8} {r.impossible:>10} {str(r.avg_wickets):>8} {r.max_wickets:>6}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--format", dest="fmt", default=None,
                        help="Restrict to one format (T20, ODI, TEST). Default: all.")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N matches")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing")
    parser.add_argument("--confirm", action="store_true", help="Required for a full run")
    args = parser.parse_args()

    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    service = StatsFromDeliveryDetails()

    try:
        print("BEFORE:")
        report(session)
        print()

        match_ids = affected_match_ids(session, args.fmt, args.limit)
        print(f"Matches with delivery_details-derived stats: {len(match_ids):,}")

        if args.dry_run:
            print("\n[DRY RUN] Nothing written.")
            return 0

        if not args.limit and not args.confirm:
            print("\nRefusing a full run without --confirm (or use --limit to try a batch).")
            return 1

        recomputed = 0
        for match_id in tqdm(match_ids, desc="Recomputing"):
            deliveries = service.get_match_deliveries(session, match_id)
            if not deliveries:
                continue

            # Replace rather than update: the set of (innings, player) rows can legitimately
            # change, so stale rows must not survive.
            session.execute(text("DELETE FROM batting_stats WHERE match_id = :m"), {"m": match_id})
            session.execute(text("DELETE FROM bowling_stats WHERE match_id = :m"), {"m": match_id})

            for innings in sorted({d["innings"] for d in deliveries}):
                for batter in sorted({d["batter"] for d in deliveries if d["innings"] == innings}):
                    stats = service.calculate_batting_stats(match_id, innings, batter, deliveries)
                    if stats:
                        session.add(stats)
                for bowler in sorted({d["bowler"] for d in deliveries if d["innings"] == innings}):
                    stats = service.calculate_bowling_stats(match_id, innings, bowler, deliveries)
                    if stats:
                        session.add(stats)

            recomputed += 1
            if recomputed % 200 == 0:
                session.commit()

        session.commit()
        print(f"\nRecomputed {recomputed:,} matches.\n")
        print("AFTER:")
        report(session)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
