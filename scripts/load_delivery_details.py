"""
Load enhanced ball-by-ball data into delivery_details table.

Usage:
    python scripts/load_delivery_details.py --csv /path/to/t20_bbb.csv --db-url "$DATABASE_URL"
    python scripts/load_delivery_details.py --csv /path/to/t20_bbb.csv --db-url "$DATABASE_URL" --only-overlap
"""

import os
import sys
import argparse
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_URL_OVERRIDE = None

def get_engine(db_url=None):
    url = db_url or DB_URL_OVERRIDE
    if not url:
        load_dotenv()
        url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/cricket_db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return create_engine(url)


def get_existing_match_ids(engine):
    """Get set of match IDs in existing database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT id FROM matches"))
        return set(str(row[0]) for row in result)


def load_and_insert(csv_path, engine, only_overlap=True, chunk_size=50000):
    """Load CSV and insert into delivery_details."""
    
    existing_ids = get_existing_match_ids(engine) if only_overlap else None
    print(f"Found {len(existing_ids) if existing_ids else 'N/A'} existing matches")
    
    # Column mapping from CSV to DB
    col_map = {
        'p_match': 'match_id',
        'inns': 'innings',
        'over': 'over',
        'ball': 'ball',
        'p_bat': 'p_bat',
        'p_bowl': 'p_bowl',
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
    
    total_inserted = 0
    total_skipped = 0
    
    print(f"Loading from {csv_path}...")
    
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False)):
        # Select and rename columns
        df = chunk[list(col_map.keys())].rename(columns=col_map)
        
        # Convert match_id to string for comparison
        df['match_id'] = df['match_id'].astype(str)
        
        # Filter to overlapping matches only
        if only_overlap and existing_ids:
            before = len(df)
            df = df[df['match_id'].isin(existing_ids)]
            total_skipped += before - len(df)
        
        if len(df) == 0:
            continue
        
        # Handle NaN values
        df = df.where(pd.notnull(df), None)
        
        # Insert to database
        df.to_sql('delivery_details', engine, if_exists='append', index=False, method='multi')
        total_inserted += len(df)
        
        print(f"  Chunk {i+1}: inserted {len(df):,} rows (total: {total_inserted:,})", end='\r')
    
    print(f"\nDone! Inserted {total_inserted:,} rows, skipped {total_skipped:,} (non-overlapping)")
    return total_inserted


def main():
    parser = argparse.ArgumentParser(description='Load delivery details from CSV')
    parser.add_argument('--csv', required=True, help='Path to t20_bbb.csv')
    parser.add_argument('--db-url', required=True, help='Database URL')
    parser.add_argument('--only-overlap', action='store_true', default=True,
                        help='Only load matches that exist in DB (default: True)')
    parser.add_argument('--all-matches', action='store_true',
                        help='Load all matches including new ones')
    args = parser.parse_args()
    
    global DB_URL_OVERRIDE
    DB_URL_OVERRIDE = args.db_url
    
    engine = get_engine(args.db_url)
    print(f"Connecting to: {args.db_url.split('@')[1] if '@' in args.db_url else 'localhost'}")
    
    only_overlap = not args.all_matches
    load_and_insert(args.csv, engine, only_overlap=only_overlap)


if __name__ == "__main__":
    main()
