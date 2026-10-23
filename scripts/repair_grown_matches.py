"""
Matches that grew after they were first processed. The ball-by-ball file can hold a match cut off part-way (22 Oct
2026: NZ v India loaded at 118 balls of New Zealand's innings, no result). The loader adds the missing balls when a
later file has them (it dedupes by ball), but the steps after it only fill what's missing: stats for matches with
none, Primer metrics for matches with none, partnership stands for matches with none, and the matches row (winner)
only when the match is new. So a match that grew would keep its half-match stats, metrics and result for good.

Here: every match with more balls than Primer metrics rows. Its stats, metrics and stands are deleted, so tonight's
later steps rebuild them from all its balls, and its matches row takes the result now in the file. Runs right after
the T20 load, before the steps that rebuild (.github/workflows/refresh-delivery-details.yml).

    python scripts/repair_grown_matches.py --dry-run
    python scripts/repair_grown_matches.py
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GROWN = """
    SELECT dd.p_match, COUNT(*) AS balls, (SELECT COUNT(*) FROM ball_metrics bm WHERE bm.p_match = dd.p_match) AS metrics
    FROM delivery_details dd
    WHERE dd.p_match IN (SELECT DISTINCT p_match FROM ball_metrics)
      AND dd.match_date >= :since
    GROUP BY dd.p_match
    HAVING COUNT(*) > (SELECT COUNT(*) FROM ball_metrics bm WHERE bm.p_match = dd.p_match)
"""
RESULT_COLS = ("winner", "toss_winner", "toss_decision", "bat_first", "bowl_first", "win_toss_win_match",
               "won_batting_first", "won_fielding_first")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--since", default="2025-01-01", help="only matches played since (match_date, ISO)")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine, get_session
    from sync_from_delivery_details import DeliveryDetailsSync

    with engine.connect() as conn:
        grown = conn.execute(text(GROWN), {"since": args.since}).all()
    print(f"{len(grown)} matches grew since they were processed")
    if not grown:
        return 0
    sync = DeliveryDetailsSync()
    db = next(get_session())
    for p_match, balls, metrics in grown:
        data = sync.extract_match_data_from_dd(db, p_match) or {}
        result = {c: data.get(c) for c in RESULT_COLS}
        print(f"  {p_match}: {metrics} -> {balls} balls; winner now {result['winner']!r}")
        if args.dry_run:
            continue
        with engine.begin() as conn:
            for table, col in (("ball_metrics", "p_match"), ("batting_stats", "match_id"), ("bowling_stats", "match_id"),
                               ("partnership_stands", "p_match")):
                conn.execute(text(f"DELETE FROM {table} WHERE {col} = :m"), {"m": p_match})
            conn.execute(text(f"UPDATE matches SET {', '.join(f'{c} = :{c}' for c in RESULT_COLS)} WHERE id = :m"),
                         {**result, "m": p_match})
    print("dry run: nothing changed" if args.dry_run else "cleared for rebuild; result updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
