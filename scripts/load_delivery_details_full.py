"""
Load ALL columns from t20_bbb.csv into delivery_details table.
Handles duplicates by only inserting new rows based on (p_match, inns, over, ball).

Usage:
    python scripts/load_delivery_details_full.py --csv /path/to/t20_bbb.csv --db-url "$DATABASE_URL"
    python scripts/load_delivery_details_full.py --csv /path/to/t20_bbb.csv --dry-run
    
    # Using environment variable:
    python scripts/load_delivery_details_full.py --csv /path/to/t20_bbb.csv
"""

import os
import sys
import argparse
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Column mapping from CSV names to DB names
COL_MAP = {
    'p_match': 'p_match',
    'inns': 'inns',
    'bat': 'bat',
    'p_bat': 'p_bat',
    'team_bat': 'team_bat',
    'bowl': 'bowl',
    'p_bowl': 'p_bowl',
    'team_bowl': 'team_bowl',
    'ball': 'ball',
    'ball_id': 'ball_id',
    'outcome': 'outcome',
    'score': 'score',
    'out': 'out',
    'dismissal': 'dismissal',
    'p_out': 'p_out',
    'over': 'over',
    'noball': 'noball',
    'wide': 'wide',
    'byes': 'byes',
    'legbyes': 'legbyes',
    'cur_bat_runs': 'cur_bat_runs',
    'cur_bat_bf': 'cur_bat_bf',
    'cur_bowl_ovr': 'cur_bowl_ovr',
    'cur_bowl_wkts': 'cur_bowl_wkts',
    'cur_bowl_runs': 'cur_bowl_runs',
    'inns_runs': 'inns_runs',
    'inns_wkts': 'inns_wkts',
    'inns_balls': 'inns_balls',
    'inns_runs_rem': 'inns_runs_rem',
    'inns_balls_rem': 'inns_balls_rem',
    'inns_rr': 'inns_rr',
    'inns_rrr': 'inns_rrr',
    'target': 'target',
    'max_balls': 'max_balls',
    'date': 'match_date',
    'year': 'year',
    'ground': 'ground',
    'country': 'country',
    'winner': 'winner',
    'toss': 'toss',
    'competition': 'competition',
    'bat_hand': 'bat_hand',
    'bowl_style': 'bowl_style',
    'bowl_kind': 'bowl_kind',
    'batruns': 'batruns',
    'ballfaced': 'ballfaced',
    'bowlruns': 'bowlruns',
    'bat_out': 'bat_out',
    'wagonX': 'wagon_x',
    'wagonY': 'wagon_y',
    'wagonZone': 'wagon_zone',
    'line': 'line',
    'length': 'length',
    'shot': 'shot',
    'control': 'control',
    'predscore': 'pred_score',
    'wprob': 'win_prob'
}


def get_engine(db_url):
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)


def get_existing_keys(engine):
    """Fetch existing (p_match, inns, over, ball) combinations."""
    print("Fetching existing delivery keys from database...")
    
    query = text("SELECT p_match, inns, over, ball FROM delivery_details")
    
    with engine.connect() as conn:
        result = conn.execute(query)
        existing = set()
        count = 0
        for row in result:
            # Create tuple key: (p_match as string, inns, over, ball)
            existing.add((str(row[0]), int(row[1]), int(row[2]), int(row[3])))
            count += 1
            if count % 500000 == 0:
                print(f"  Loaded {count:,} existing keys...", end='\r')
        
        print(f"  Found {len(existing):,} existing deliveries in database")
        return existing


def load_csv(csv_path, engine, chunk_size=50000, dry_run=False, existing_keys=None):
    """Load CSV into delivery_details, skipping duplicates."""
    
    print(f"\nLoading from {csv_path}...")
    total_in_csv = 0
    total_skipped = 0
    total_inserted = 0
    
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False)):
        total_in_csv += len(chunk)
        
        # Rename columns
        chunk = chunk.rename(columns=COL_MAP)
        
        # Keep only mapped columns that exist
        cols_to_keep = [c for c in COL_MAP.values() if c in chunk.columns]
        df = chunk[cols_to_keep].copy()
        
        # Convert p_match to string
        df['p_match'] = df['p_match'].astype(str)
        
        # Fix over numbering: new dataset is 1-indexed, existing is 0-indexed
        df['over'] = df['over'] - 1
        
        # Filter out existing records if we have existing keys
        if existing_keys:
            # Create key column for filtering
            df['_key'] = list(zip(
                df['p_match'].astype(str),
                df['inns'].astype(int),
                df['over'].astype(int),
                df['ball'].astype(int)
            ))
            
            before_filter = len(df)
            df = df[~df['_key'].isin(existing_keys)]
            df = df.drop(columns=['_key'])
            
            skipped = before_filter - len(df)
            total_skipped += skipped
        
        if len(df) == 0:
            print(f"  Chunk {i+1}: All {chunk_size} rows already exist, skipping...", end='\r')
            continue
        
        # Handle NaN
        df = df.where(pd.notnull(df), None)
        
        if dry_run:
            total_inserted += len(df)
            print(f"  [DRY RUN] Chunk {i+1}: Would insert {len(df):,} new rows", end='\r')
        else:
            # Insert
            df.to_sql('delivery_details', engine, if_exists='append', index=False, method='multi')
            total_inserted += len(df)
            print(f"  Chunk {i+1}: Inserted {len(df):,} new rows (total: {total_inserted:,})", end='\r')
    
    print(f"\n")
    return {
        'total_in_csv': total_in_csv,
        'total_skipped': total_skipped,
        'total_inserted': total_inserted
    }


def main():
    parser = argparse.ArgumentParser(description='Load full CSV to delivery_details')
    parser.add_argument('--csv', required=True, help='Path to t20_bbb.csv')
    parser.add_argument('--db-url', help='Database URL (or set DATABASE_URL env var)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be inserted without making changes')
    parser.add_argument('--force', action='store_true', help='Skip duplicate checking (faster but may create duplicates)')
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: Database URL required. Use --db-url or set DATABASE_URL environment variable.")
        sys.exit(1)
    
    engine = get_engine(db_url)
    db_display = db_url.split('@')[1] if '@' in db_url else 'localhost'
    print(f"Connecting to: {db_display}")
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    
    # Get existing keys unless --force is used
    existing_keys = None
    if not args.force:
        existing_keys = get_existing_keys(engine)
    else:
        print("WARNING: --force mode - skipping duplicate check!")
    
    # Load CSV
    results = load_csv(args.csv, engine, dry_run=args.dry_run, existing_keys=existing_keys)
    
    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total rows in CSV:  {results['total_in_csv']:,}")
    print(f"  Rows skipped (dupe): {results['total_skipped']:,}")
    print(f"  Rows {'would insert' if args.dry_run else 'inserted'}:  {results['total_inserted']:,}")
    
    if args.dry_run:
        print("\n*** DRY RUN COMPLETE - No changes were made ***")


if __name__ == "__main__":
    main()
