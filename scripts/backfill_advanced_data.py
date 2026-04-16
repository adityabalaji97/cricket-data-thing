"""
Backfill advanced data columns in delivery_details from CSV.

When deliveries were loaded before advanced data (line, length, shot, control, etc.)
was available in the CSV, those fields stay NULL. This script updates those rows
from the latest CSV.

Columns backfilled: wagon_zone, wagon_x, wagon_y, line, length, shot, control,
                     pred_score, win_prob

Usage:
    python scripts/backfill_advanced_data.py --csv /path/to/t20_bbb.csv --db-url "$DATABASE_URL"
    python scripts/backfill_advanced_data.py --csv /path/to/t20_bbb.csv --dry-run
"""

import os
import sys
import argparse
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.load_delivery_details_full import COL_MAP, get_engine

ADVANCED_COLS = [
    'wagon_zone', 'wagon_x', 'wagon_y', 'line', 'length', 'shot',
    'control', 'pred_score', 'win_prob'
]

# Reverse map: DB col -> CSV col
DB_TO_CSV = {v: k for k, v in COL_MAP.items()}


def get_null_advanced_keys(engine):
    """Fetch (p_match, inns, over, ball) where any advanced column is NULL."""
    conditions = " OR ".join(f"{col} IS NULL" for col in ADVANCED_COLS)
    query = text(f"""
        SELECT p_match, inns, over, ball
        FROM delivery_details
        WHERE {conditions}
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [(str(r[0]), int(r[1]), int(r[2]), int(r[3])) for r in result]

    print(f"  Found {len(rows):,} deliveries with NULL advanced data in DB")
    return rows


def backfill(csv_path, engine, dry_run=False):
    """Backfill advanced columns from CSV into DB rows that have NULLs.

    Uses a temp table + single bulk UPDATE with COALESCE to preserve existing
    non-NULL values. Much faster than row-by-row updates.
    """

    print("Finding deliveries with NULL advanced data...")
    null_keys = get_null_advanced_keys(engine)
    if not null_keys:
        print("  Nothing to backfill — all advanced columns are populated.")
        return 0

    match_ids_needed = {k[0] for k in null_keys}

    print(f"  Matches with NULL advanced data: {len(match_ids_needed):,}")
    print(f"Loading CSV and filtering to relevant matches...")

    # Read CSV, filter to needed matches
    df = pd.read_csv(csv_path, low_memory=False)
    df = df.rename(columns=COL_MAP)

    # Keep only columns we need
    key_cols = ['p_match', 'inns', 'over', 'ball']
    advanced_in_csv = [c for c in ADVANCED_COLS if c in df.columns]
    df = df[key_cols + advanced_in_csv].copy()

    df['p_match'] = df['p_match'].astype(str)
    df['over'] = df['over'] - 1  # Same 1->0 index adjustment as loader

    # Filter to only matches we need
    df = df[df['p_match'].isin(match_ids_needed)]
    print(f"  CSV rows for relevant matches: {len(df):,}")

    # Replace "-" with NaN (treat as missing)
    df = df.replace('-', pd.NA)

    # Normalize control to nullable int
    if 'control' in df.columns:
        df['control'] = pd.to_numeric(df['control'], errors='coerce').astype('Int64')

    # Convert NaN in string-typed cols to None (so to_sql inserts NULL, not 'NaN')
    for col in ('line', 'length', 'shot'):
        if col in df.columns:
            df[col] = df[col].astype(object).where(pd.notna(df[col]), None)

    # Drop rows where ALL advanced cols are null (nothing to backfill for them)
    if advanced_in_csv:
        df = df.dropna(subset=advanced_in_csv, how='all')
    print(f"  CSV rows with data to backfill: {len(df):,}")

    if df.empty:
        print("  Nothing to backfill — CSV has no data for these rows.")
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would update up to {len(df):,} rows")
        return len(df)

    # Upload to a temp table once
    with engine.begin() as conn:
        print("  Creating temp table...")
        conn.execute(text("DROP TABLE IF EXISTS temp_backfill_advanced"))

        print(f"  Uploading {len(df):,} rows to temp table...")
        df.to_sql(
            "temp_backfill_advanced",
            conn,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=5000,
        )

        print("  Indexing temp table...")
        conn.execute(text(
            "CREATE INDEX ix_temp_backfill_advanced_key "
            "ON temp_backfill_advanced (p_match, inns, over, ball)"
        ))

    # Run the UPDATE in batches of matches to keep each statement small enough
    # that Postgres doesn't run out of memory / get killed.
    set_clauses = ", ".join(
        f"{col} = COALESCE(dd.{col}, t.{col})" for col in advanced_in_csv
    )
    null_filter = " OR ".join(f"dd.{col} IS NULL" for col in advanced_in_csv)

    match_list = sorted(match_ids_needed)
    BATCH_SIZE = 500
    total_batches = (len(match_list) + BATCH_SIZE - 1) // BATCH_SIZE
    total_updated = 0

    print(f"  Running bulk UPDATE in {total_batches} batches of {BATCH_SIZE} matches...")
    for i in range(0, len(match_list), BATCH_SIZE):
        batch = match_list[i:i + BATCH_SIZE]
        with engine.begin() as conn:
            result = conn.execute(
                text(f"""
                    UPDATE delivery_details dd
                    SET {set_clauses}
                    FROM temp_backfill_advanced t
                    WHERE dd.p_match::text = t.p_match::text
                      AND dd.inns = t.inns
                      AND dd.over = t.over
                      AND dd.ball = t.ball
                      AND dd.p_match::text = ANY(:batch)
                      AND ({null_filter})
                """),
                {"batch": batch},
            )
            total_updated += result.rowcount
        print(
            f"    Batch {i // BATCH_SIZE + 1}/{total_batches}: "
            f"updated {result.rowcount:,} rows (total: {total_updated:,})"
        )

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS temp_backfill_advanced"))

    print(f"  Backfill complete: {total_updated:,} rows updated")
    return total_updated


def main():
    parser = argparse.ArgumentParser(description='Backfill advanced data columns in delivery_details')
    parser.add_argument('--csv', required=True, help='Path to t20_bbb.csv')
    parser.add_argument('--db-url', help='Database URL (or set DATABASE_URL env var)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    args = parser.parse_args()

    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: Database URL required. Use --db-url or set DATABASE_URL environment variable.")
        sys.exit(1)

    engine = get_engine(db_url)
    db_display = db_url.split('@')[1] if '@' in db_url else 'localhost'
    print(f"Connecting to: {db_display}")

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    updated = backfill(args.csv, engine, dry_run=args.dry_run)

    print(f"\nSUMMARY: {'Would update' if args.dry_run else 'Updated'} {updated:,} rows")

    if args.dry_run:
        print("\n*** DRY RUN COMPLETE - No changes were made ***")


if __name__ == "__main__":
    main()
