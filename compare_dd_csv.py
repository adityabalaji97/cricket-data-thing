#!/usr/bin/env python3
"""
Compare delivery_details in database vs CSV source file.
Usage: python compare_dd_csv.py <match_id> [csv_path]
"""

import sys
import pandas as pd
from database import get_database_connection
from sqlalchemy import text

def find_csv_file():
    """Try to find the delivery_details CSV file"""
    import os
    possible_paths = [
        'data/delivery_details.csv',
        'delivery_details.csv',
        '../data/delivery_details.csv',
        'data/enhanced_bbb.csv',
        'enhanced_bbb.csv',
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def compare_match(match_id, csv_path=None):
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    print(f"=== COMPARING MATCH {match_id} ===\n")
    
    # 1. Get DB data
    print("1. DATABASE DATA:")
    db_data = session.execute(text('''
        SELECT inns, over, ball, bat, score, 
               MIN(over) OVER (PARTITION BY inns) as first_over,
               MAX(over) OVER (PARTITION BY inns) as last_over,
               COUNT(*) OVER (PARTITION BY inns) as inns_deliveries
        FROM delivery_details 
        WHERE p_match = :mid
        ORDER BY inns, over, ball
    '''), {'mid': match_id}).fetchall()
    
    if not db_data:
        print(f"  No data found in DB for match {match_id}")
        # Try alternate column
        db_data = session.execute(text('''
            SELECT innings as inns, over, ball, batter as bat, score
            FROM delivery_details 
            WHERE match_id = :mid
            ORDER BY innings, over, ball
        '''), {'mid': match_id}).fetchall()
        if db_data:
            print(f"  Found {len(db_data)} rows using match_id column")
    
    if db_data:
        df_db = pd.DataFrame(db_data)
        for inns in df_db['inns'].unique():
            inns_df = df_db[df_db['inns'] == inns]
            print(f"\n  Innings {inns}:")
            print(f"    Rows: {len(inns_df)}")
            print(f"    Over range: {inns_df['over'].min()} to {inns_df['over'].max()}")
            print(f"    First 3 balls: {list(inns_df[['over','ball','bat','score']].head(3).values)}")
            print(f"    Last 3 balls: {list(inns_df[['over','ball','bat','score']].tail(3).values)}")
    
    # 2. Get CSV data
    print("\n2. CSV DATA:")
    if not csv_path:
        csv_path = find_csv_file()
    
    if not csv_path:
        print("  CSV file not found. Please provide path as second argument.")
        print("  Looking for: data/delivery_details.csv or similar")
        
        # List what's in data directory
        import os
        if os.path.exists('data'):
            print(f"\n  Files in data/: {os.listdir('data')[:10]}")
        return
    
    print(f"  Loading from: {csv_path}")
    
    # Load CSV - try different possible column names for match_id
    try:
        df_csv = pd.read_csv(csv_path, low_memory=False)
        print(f"  Total CSV rows: {len(df_csv):,}")
        print(f"  CSV columns: {list(df_csv.columns)[:15]}...")
        
        # Find the match - try different column names
        match_col = None
        for col in ['p_match', 'match_id', 'matchId', 'match']:
            if col in df_csv.columns:
                match_col = col
                break
        
        if not match_col:
            print(f"  Could not find match ID column. Available: {list(df_csv.columns)}")
            return
        
        # Filter for this match
        match_df = df_csv[df_csv[match_col].astype(str) == str(match_id)]
        print(f"\n  Rows for match {match_id}: {len(match_df)}")
        
        if len(match_df) == 0:
            print(f"  Match not found in CSV!")
            # Show sample match IDs
            sample_ids = df_csv[match_col].dropna().unique()[:10]
            print(f"  Sample match IDs in CSV: {list(sample_ids)}")
            return
        
        # Find innings column
        inns_col = None
        for col in ['inns', 'innings', 'inning']:
            if col in match_df.columns:
                inns_col = col
                break
        
        over_col = 'over' if 'over' in match_df.columns else 'overs'
        ball_col = 'ball' if 'ball' in match_df.columns else 'ball_num'
        bat_col = next((c for c in ['bat', 'batter', 'striker'] if c in match_df.columns), None)
        
        for inns in sorted(match_df[inns_col].unique()):
            inns_df = match_df[match_df[inns_col] == inns]
            print(f"\n  Innings {inns}:")
            print(f"    Rows: {len(inns_df)}")
            if over_col in inns_df.columns:
                print(f"    Over range: {inns_df[over_col].min()} to {inns_df[over_col].max()}")
            if bat_col:
                print(f"    First 3: {list(inns_df[[over_col, ball_col, bat_col]].head(3).values)}")
                print(f"    Last 3: {list(inns_df[[over_col, ball_col, bat_col]].tail(3).values)}")
        
        # 3. Compare
        print("\n3. COMPARISON:")
        db_count = len(db_data) if db_data else 0
        csv_count = len(match_df)
        diff = csv_count - db_count
        print(f"  DB rows: {db_count}")
        print(f"  CSV rows: {csv_count}")
        print(f"  Difference: {diff} rows {'MISSING from DB' if diff > 0 else ''}")
        
    except Exception as e:
        print(f"  Error reading CSV: {e}")
    
    session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compare_dd_csv.py <match_id> [csv_path]")
        print("Example: python compare_dd_csv.py 1479580 data/delivery_details.csv")
        sys.exit(1)
    
    match_id = sys.argv[1]
    csv_path = sys.argv[2] if len(sys.argv) > 2 else None
    compare_match(match_id, csv_path)
