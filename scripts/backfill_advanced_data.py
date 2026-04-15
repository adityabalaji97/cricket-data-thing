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
    """Backfill advanced columns from CSV into DB rows that have NULLs."""

    print("Finding deliveries with NULL advanced data...")
    null_keys = get_null_advanced_keys(engine)
    if not null_keys:
        print("  Nothing to backfill — all advanced columns are populated.")
        return 0

    # Get the set of match IDs to filter CSV efficiently
    match_ids_needed = {k[0] for k in null_keys}
    null_key_set = set(null_keys)

    print(f"  Matches with NULL advanced data: {len(match_ids_needed):,}")
    print(f"Loading CSV and filtering to relevant matches...")

    # Read CSV, filter to needed matches
    df = pd.read_csv(csv_path, low_memory=False)
    df = df.rename(columns=COL_MAP)

    # Keep only columns we need
    key_cols = ['p_match', 'inns', 'over', 'ball']
    cols_to_keep = key_cols + [c for c in ADVANCED_COLS if c in df.columns]
    df = df[[c for c in cols_to_keep if c in df.columns]].copy()

    df['p_match'] = df['p_match'].astype(str)
    df['over'] = df['over'] - 1  # Same 1->0 index adjustment as loader

    # Filter to only matches we need
    df = df[df['p_match'].isin(match_ids_needed)]
    print(f"  CSV rows for relevant matches: {len(df):,}")

    # Replace "-" with None and handle NaN (same as loader)
    df = df.replace('-', None)
    df = df.where(pd.notnull(df), None)

    # Normalize control to int (same as loader)
    if 'control' in df.columns:
        control_numeric = pd.to_numeric(df['control'], errors='coerce')
        df['control'] = control_numeric.apply(lambda v: int(v) if pd.notna(v) else None)

    # Build lookup: (p_match, inns, over, ball) -> {col: value}
    csv_lookup = {}
    for _, row in df.iterrows():
        key = (str(row['p_match']), int(row['inns']), int(row['over']), int(row['ball']))
        if key in null_key_set:
            vals = {}
            for col in ADVANCED_COLS:
                if col in row.index and row[col] is not None:
                    vals[col] = row[col]
            if vals:
                csv_lookup[key] = vals

    print(f"  CSV rows with data to backfill: {len(csv_lookup):,}")

    if not csv_lookup:
        print("  Nothing to backfill — CSV has no new data for these rows.")
        return 0

    # Now fetch current DB values for these keys so we only update NULL->non-NULL
    # Build batch updates
    updates = []
    for key, csv_vals in csv_lookup.items():
        p_match, inns, over, ball = key
        set_clauses = []
        params = {'p_match': p_match, 'inns': inns, 'over': over, 'ball': ball}
        for col, val in csv_vals.items():
            # Use COALESCE-style: only set if DB value is NULL
            set_clauses.append(f"{col} = CASE WHEN {col} IS NULL THEN :{col}_val ELSE {col} END")
            params[f'{col}_val'] = val

        if set_clauses:
            updates.append((set_clauses, params))

    total_to_update = len(updates)
    print(f"\n  Rows to update: {total_to_update:,}")

    if dry_run:
        print(f"  [DRY RUN] Would update {total_to_update:,} rows")
        return total_to_update

    # Execute in batches
    batch_size = 500
    updated = 0
    with engine.connect() as conn:
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            for set_clauses, params in batch:
                sql = f"""
                    UPDATE delivery_details
                    SET {', '.join(set_clauses)}
                    WHERE p_match = :p_match AND inns = :inns AND over = :over AND ball = :ball
                """
                conn.execute(text(sql), params)
                updated += 1

            print(f"  Updated {updated:,}/{total_to_update:,} rows...", end='\r')

        conn.commit()

    print(f"\n  Backfill complete: {updated:,} rows updated")
    return updated


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
