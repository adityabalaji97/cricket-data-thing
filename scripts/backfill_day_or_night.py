#!/usr/bin/env python3
"""
Backfill the matches.day_or_night column for existing IPL matches.

Idempotent: only updates rows where day_or_night IS NULL.

Run AFTER:
  1. The add_day_or_night_column.sql migration is applied.
  2. classify_day_night_crosscheck.py has been reviewed and any
     divergences manually resolved (or accepted).

Usage:
    python scripts/backfill_day_or_night.py [--method event_match_number|match_id] [--dry-run]
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from tqdm import tqdm
from database import get_database_connection
from services.day_night_classifier import classify_day_night, SUPPORTED_COMPETITIONS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--method",
        default="auto",
        choices=["auto", "event_match_number", "match_id"],
        help="Classification heuristic. 'auto' uses event_match_number when "
             "available and falls back to match_id sort. Default: auto.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to the DB.",
    )
    parser.add_argument(
        "--competition",
        default=None,
        help="Restrict backfill to one competition string (e.g. 'IPL' or "
             "'Indian Premier League'). Default: backfill all supported.",
    )
    args = parser.parse_args()

    if args.competition and args.competition not in SUPPORTED_COMPETITIONS:
        print(f"ERROR: competition '{args.competition}' is not supported.")
        print(f"Supported: {sorted(SUPPORTED_COMPETITIONS)}")
        return 1

    target_competitions = (
        [args.competition] if args.competition else sorted(SUPPORTED_COMPETITIONS)
    )

    _, SessionLocal = get_database_connection()
    session = SessionLocal()
    try:
        # Fetch all matches in scope (NULL day_or_night, target competitions)
        rows = session.execute(
            text(
                """
                SELECT id, date, competition, event_match_number
                FROM matches
                WHERE competition = ANY(:competitions) AND day_or_night IS NULL
                ORDER BY date, event_match_number NULLS LAST, id
                """
            ),
            {"competitions": target_competitions},
        ).fetchall()

        cols = ["id", "date", "competition", "event_match_number"]
        all_matches = [dict(zip(cols, r)) for r in rows]
        print(
            f"Found {len(all_matches)} matches without day_or_night across "
            f"competitions: {target_competitions}"
        )

        if not all_matches:
            print("Nothing to backfill.")
            return 0

        # Group by (date, competition) — same date but different competition
        # strings count as different groups.
        groups = defaultdict(list)
        for m in all_matches:
            groups[(m["date"], m["competition"])].append(m)

        # Build full label set
        labels = {}
        for (date, competition), peers in groups.items():
            group_labels = classify_day_night(
                competition=competition,
                peer_matches=peers,
                method=args.method,
            )
            labels.update(group_labels)

        day_count = sum(1 for v in labels.values() if v == "day")
        night_count = sum(1 for v in labels.values() if v == "night")
        print(f"Computed labels: {day_count} day, {night_count} night")

        if args.dry_run:
            print("\nDRY RUN — not writing. Sample labels:")
            for mid, lbl in list(labels.items())[:20]:
                print(f"  {mid}: {lbl}")
            return 0

        # Bulk update: group by label and run one IN-list UPDATE per label.
        # 2 queries beats 1212 round-trips against a remote DB.
        by_label = defaultdict(list)
        for match_id, label in labels.items():
            by_label[label].append(match_id)

        for label, ids in by_label.items():
            print(f"Updating {len(ids)} matches to '{label}'...")
            session.execute(
                text("UPDATE matches SET day_or_night = :label WHERE id = ANY(:ids)"),
                {"label": label, "ids": ids},
            )
        session.commit()
        print(f"\nBackfill complete: {len(labels)} matches updated.")

        # Sanity check: distribution
        result = session.execute(
            text(
                """
                SELECT competition, day_or_night, COUNT(*)
                FROM matches
                WHERE competition = ANY(:competitions)
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
            ),
            {"competitions": target_competitions},
        ).fetchall()
        print("\nDistribution after backfill:")
        for comp, lbl, cnt in result:
            print(f"  {comp:>6} | {lbl or 'NULL':>5} | {cnt}")

        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
