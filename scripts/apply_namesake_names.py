"""
Write each namesake's display name onto his own rows (PLAYER_IDS_PLAN.md chunk 3, decided 23 Oct 2026): the balls,
stats rows and playing XIs of a player who shares his name with a better-known one carry "Rohit Sharma (Indonesia)"
instead of "Rohit Sharma". Every name-based page, search and API then tells them apart without being changed itself.

By player id (player_identity): a namesake's rows take his display name; a main player's rows that carry a side
suffix (the main player of a name changed) go back to the plain name. Rows are matched by id, so nothing without an
id is touched (pre-2015 legacy balls stay with the main player). Partnership stands of the matches touched are rebuilt.
Re-applied nightly after the load (the feed keeps sending plain names). Reversible: strip the suffix.

    python scripts/apply_namesake_names.py --dry-run
    python scripts/apply_namesake_names.py
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (table, name column, id column, match column). The target name: a namesake's display name, or a main player's plain
# name where his row carries a suffix.
TARGETS = (
    ("delivery_details", "bat", "p_bat", "p_match"),
    ("delivery_details", "bowl", "p_bowl", "p_match"),
    ("batting_stats", "striker", "pid", "match_id"),
    ("bowling_stats", "bowler", "pid", "match_id"),
    ("match_players", "player", "pid", "match_id"),
)
WHERE = """pi.pid = t.{pid} AND t.{col} IS DISTINCT FROM pi.display_name
           AND (pi.display_name <> pi.name OR t.{col} ~ '\\s+\\([A-Za-z](?:[^()]|\\([^()]*\\))*\\)$')"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine

    touched = set()
    for table, col, pid, match_col in TARGETS:
        where = WHERE.format(pid=pid, col=col)
        with engine.begin() as conn:
            matches = conn.execute(text(f"SELECT DISTINCT t.{match_col} FROM {table} t, player_identity pi WHERE {where}")).scalars().all()
            if args.dry_run:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {table} t, player_identity pi WHERE {where}")).scalar()
                print(f"{table}.{col}: {n} rows would be renamed ({len(matches)} matches)")
                continue
            n = conn.execute(text(f"UPDATE {table} t SET {col} = pi.display_name FROM player_identity pi WHERE {where}")).rowcount
            print(f"{table}.{col}: {n} rows renamed ({len(matches)} matches)")
        if table == "delivery_details":
            touched.update(str(m) for m in matches)
    if touched and not args.dry_run:
        from build_partnership_stands import build

        with engine.begin() as conn:
            build(conn, match_ids=sorted(touched))
        print(f"partnership stands rebuilt for {len(touched)} matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
