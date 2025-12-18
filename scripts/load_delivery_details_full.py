"""
Load ALL columns from t20_bbb.csv into delivery_details table.

Usage:
    python scripts/load_delivery_details_full.py --csv /path/to/t20_bbb.csv --db-url "postgres://..."
"""

import os
import sys
import argparse
import pandas as pd
from sqlalchemy import create_engine

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


def load_csv(csv_path, engine, chunk_size=50000):
    """Load full CSV into delivery_details."""
    
    print(f"Loading from {csv_path}...")
    total_inserted = 0
    
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False)):
        # Rename columns
        chunk = chunk.rename(columns=COL_MAP)
        
        # Keep only mapped columns that exist
        cols_to_keep = [c for c in COL_MAP.values() if c in chunk.columns]
        df = chunk[cols_to_keep]
        
        # Convert p_match to string
        df['p_match'] = df['p_match'].astype(str)
        
        # Fix over numbering: new dataset is 1-indexed, existing is 0-indexed
        df['over'] = df['over'] - 1
        
        # Handle NaN
        df = df.where(pd.notnull(df), None)
        
        # Insert
        df.to_sql('delivery_details', engine, if_exists='append', index=False, method='multi')
        total_inserted += len(df)
        
        print(f"  Chunk {i+1}: {total_inserted:,} rows inserted", end='\r')
    
    print(f"\n\nDone! Total rows: {total_inserted:,}")
    return total_inserted


def main():
    parser = argparse.ArgumentParser(description='Load full CSV to delivery_details')
    parser.add_argument('--csv', required=True, help='Path to t20_bbb.csv')
    parser.add_argument('--db-url', required=True, help='Database URL')
    args = parser.parse_args()
    
    engine = get_engine(args.db_url)
    print(f"Connecting to: {args.db_url.split('@')[1] if '@' in args.db_url else 'localhost'}")
    
    load_csv(args.csv, engine)


if __name__ == "__main__":
    main()
