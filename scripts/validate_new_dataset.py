"""
Validation script for new ball-by-ball dataset integration.

This script validates the new t20_bbb.csv dataset against the existing
database to identify:
1. Match ID overlap/gaps
2. Ball-level data integrity
3. Player name consistency
4. Coverage analysis

Usage:
    python scripts/validate_new_dataset.py --csv /path/to/t20_bbb.csv
    python scripts/validate_new_dataset.py --csv /path/to/t20_bbb.csv --sample 100000
"""

import os
import sys
import argparse
from datetime import datetime
from collections import defaultdict

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DB_URL_OVERRIDE = None

def get_database_url():
    """Get database URL from environment or CLI override."""
    global DB_URL_OVERRIDE
    if DB_URL_OVERRIDE:
        db_url = DB_URL_OVERRIDE
    else:
        load_dotenv()
        db_url = os.getenv("DATABASE_URL", "postgresql://aditya:aditya123@localhost:5432/cricket_db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def connect_to_database():
    """Create database connection."""
    db_url = get_database_url()
    print(f"Connecting to: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")
    engine = create_engine(db_url)
    return engine


def get_existing_match_ids(engine):
    """Fetch all existing match IDs from the database."""
    print("\nFetching existing match IDs from database...")
    query = text("SELECT DISTINCT id FROM matches")
    with engine.connect() as conn:
        result = conn.execute(query)
        match_ids = set()
        for row in result:
            # Handle both string and numeric IDs
            match_id = row[0]
            try:
                match_ids.add(int(match_id))
            except (ValueError, TypeError):
                match_ids.add(str(match_id))
        print(f"Found {len(match_ids)} existing matches in database")
        return match_ids


def get_existing_deliveries_sample(engine, limit=1000):
    """Fetch sample of existing deliveries for comparison."""
    print(f"\nFetching sample of {limit} existing deliveries...")
    query = text("""
        SELECT match_id, innings, over, ball, batter, bowler 
        FROM deliveries 
        LIMIT :limit
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"limit": limit})
        deliveries = []
        for row in result:
            deliveries.append({
                'match_id': row[0],
                'innings': row[1],
                'over': row[2],
                'ball': row[3],
                'batter': row[4],
                'bowler': row[5]
            })
        return deliveries


def get_existing_player_names(engine):
    """Fetch all player names from existing deliveries."""
    print("\nFetching existing player names...")
    query = text("""
        SELECT DISTINCT batter FROM deliveries
        UNION
        SELECT DISTINCT bowler FROM deliveries
    """)
    with engine.connect() as conn:
        result = conn.execute(query)
        players = set(row[0] for row in result if row[0])
        print(f"Found {len(players)} unique player names in existing data")
        return players


def load_new_dataset(csv_path, sample_size=None, chunk_size=100000):
    """
    Load new dataset from CSV, optionally sampling.
    
    Args:
        csv_path: Path to the CSV file
        sample_size: If provided, only load this many rows
        chunk_size: Size of chunks for reading large files
    
    Returns:
        DataFrame with the new dataset
    """
    print(f"\nLoading new dataset from: {csv_path}")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    print(f"File size: {file_size_mb:.1f} MB")
    
    if sample_size:
        print(f"Loading sample of {sample_size:,} rows...")
        df = pd.read_csv(csv_path, nrows=sample_size)
    else:
        print(f"Loading full file in chunks of {chunk_size:,} rows...")
        chunks = []
        total_rows = 0
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
            chunks.append(chunk)
            total_rows += len(chunk)
            print(f"  Loaded {total_rows:,} rows...", end='\r')
        df = pd.concat(chunks, ignore_index=True)
        print(f"\nTotal rows loaded: {len(df):,}")
    
    return df


def analyze_match_overlap(new_df, existing_match_ids):
    """Analyze overlap between new dataset and existing matches."""
    print("\n" + "="*60)
    print("MATCH ID ANALYSIS")
    print("="*60)
    
    # Get unique match IDs from new dataset
    new_match_ids = set(new_df['p_match'].unique())
    print(f"\nUnique matches in new dataset: {len(new_match_ids):,}")
    
    # Convert to comparable types
    new_match_ids_int = set()
    for mid in new_match_ids:
        try:
            new_match_ids_int.add(int(mid))
        except (ValueError, TypeError):
            new_match_ids_int.add(mid)
    
    existing_match_ids_int = set()
    for mid in existing_match_ids:
        try:
            existing_match_ids_int.add(int(mid))
        except (ValueError, TypeError):
            existing_match_ids_int.add(mid)
    
    # Calculate overlaps
    overlap = new_match_ids_int & existing_match_ids_int
    new_only = new_match_ids_int - existing_match_ids_int
    existing_only = existing_match_ids_int - new_match_ids_int
    
    print(f"Matches in BOTH datasets: {len(overlap):,}")
    print(f"Matches in NEW only (not in current DB): {len(new_only):,}")
    print(f"Matches in EXISTING only (no enhanced data): {len(existing_only):,}")
    
    # Sample of new-only matches
    if new_only:
        sample_new = list(new_only)[:10]
        print(f"\nSample of NEW-ONLY match IDs: {sample_new}")
        
        # Try to get info about these matches from new dataset
        sample_matches = new_df[new_df['p_match'].isin(sample_new)].drop_duplicates('p_match')
        if 'competition' in sample_matches.columns:
            print("Competitions for new-only matches:")
            print(sample_matches['competition'].value_counts().head(10))
    
    return {
        'overlap': overlap,
        'new_only': new_only,
        'existing_only': existing_only,
        'new_match_ids': new_match_ids_int,
        'existing_match_ids': existing_match_ids_int
    }


def analyze_player_names(new_df, existing_players):
    """Analyze player name consistency between datasets."""
    print("\n" + "="*60)
    print("PLAYER NAME ANALYSIS")
    print("="*60)
    
    # Get unique player names from new dataset
    new_batters = set(new_df['bat'].dropna().unique())
    new_bowlers = set(new_df['bowl'].dropna().unique())
    new_players = new_batters | new_bowlers
    
    print(f"\nUnique players in new dataset: {len(new_players):,}")
    print(f"  - Batters: {len(new_batters):,}")
    print(f"  - Bowlers: {len(new_bowlers):,}")
    
    # Check for exact matches
    exact_matches = new_players & existing_players
    new_only_players = new_players - existing_players
    existing_only_players = existing_players - new_players
    
    print(f"\nExact name matches: {len(exact_matches):,}")
    print(f"Players in NEW only: {len(new_only_players):,}")
    print(f"Players in EXISTING only: {len(existing_only_players):,}")
    
    # Sample mismatches for investigation
    if new_only_players:
        print(f"\nSample of NEW-ONLY player names (first 20):")
        for name in sorted(list(new_only_players))[:20]:
            print(f"  - {name}")
    
    return {
        'exact_matches': exact_matches,
        'new_only': new_only_players,
        'existing_only': existing_only_players
    }


def analyze_data_quality(new_df):
    """Analyze data quality of the new dataset."""
    print("\n" + "="*60)
    print("DATA QUALITY ANALYSIS")
    print("="*60)
    
    print(f"\nTotal rows: {len(new_df):,}")
    print(f"\nColumn list ({len(new_df.columns)} columns):")
    for col in new_df.columns:
        null_count = new_df[col].isna().sum()
        null_pct = (null_count / len(new_df)) * 100
        print(f"  - {col}: {null_pct:.1f}% null")
    
    # Check key columns for the wagon wheel / shot data
    key_columns = ['wagonX', 'wagonY', 'wagonZone', 'line', 'length', 'shot', 'control', 'predscore', 'wprob']
    print("\nKey enhanced columns analysis:")
    for col in key_columns:
        if col in new_df.columns:
            non_null = new_df[col].notna().sum()
            non_null_pct = (non_null / len(new_df)) * 100
            
            # Check for sentinel values (-1)
            if col in ['predscore', 'wprob']:
                valid = new_df[(new_df[col].notna()) & (new_df[col] != -1)]
                valid_pct = (len(valid) / len(new_df)) * 100
                print(f"  - {col}: {non_null_pct:.1f}% non-null, {valid_pct:.1f}% valid (excluding -1)")
            else:
                print(f"  - {col}: {non_null_pct:.1f}% non-null")
                
            # Show unique values for categorical columns
            if col in ['line', 'length', 'shot', 'wagonZone']:
                unique_vals = new_df[col].dropna().unique()
                print(f"    Unique values ({len(unique_vals)}): {list(unique_vals)[:10]}...")
    
    # Competition breakdown
    if 'competition' in new_df.columns:
        print("\nCompetition breakdown:")
        comp_counts = new_df.groupby('competition')['p_match'].nunique()
        for comp, count in comp_counts.sort_values(ascending=False).items():
            print(f"  - {comp}: {count:,} matches")
    
    # Year breakdown
    if 'year' in new_df.columns:
        print("\nYear range:", new_df['year'].min(), "-", new_df['year'].max())


def analyze_ball_integrity(new_df, overlap_matches, engine):
    """Check ball-level data integrity for overlapping matches."""
    print("\n" + "="*60)
    print("BALL-LEVEL INTEGRITY CHECK")
    print("="*60)
    
    if not overlap_matches:
        print("No overlapping matches to check.")
        return {}
    
    # Sample a few overlapping matches for detailed comparison
    sample_matches = list(overlap_matches)[:5]
    print(f"\nChecking {len(sample_matches)} sample matches: {sample_matches}")
    
    results = {}
    
    for match_id in sample_matches:
        # Get deliveries from new dataset
        new_deliveries = new_df[new_df['p_match'] == match_id]
        new_ball_count = len(new_deliveries)
        
        # Get deliveries from existing database
        query = text("SELECT COUNT(*) FROM deliveries WHERE match_id = :match_id")
        with engine.connect() as conn:
            result = conn.execute(query, {"match_id": str(match_id)})
            existing_ball_count = result.scalar()
        
        match_status = "✓" if new_ball_count == existing_ball_count else "⚠"
        print(f"  Match {match_id}: New={new_ball_count}, Existing={existing_ball_count} {match_status}")
        
        results[match_id] = {
            'new_count': new_ball_count,
            'existing_count': existing_ball_count,
            'match': new_ball_count == existing_ball_count
        }
    
    return results


def generate_report(results, output_path):
    """Generate a markdown report of validation results."""
    print(f"\nGenerating report: {output_path}")
    
    with open(output_path, 'w') as f:
        f.write("# New Dataset Validation Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Match Analysis
        f.write("## Match ID Analysis\n\n")
        match_results = results.get('match_analysis', {})
        f.write(f"- **Matches in new dataset**: {len(match_results.get('new_match_ids', set())):,}\n")
        f.write(f"- **Matches in existing DB**: {len(match_results.get('existing_match_ids', set())):,}\n")
        f.write(f"- **Overlapping matches**: {len(match_results.get('overlap', set())):,}\n")
        f.write(f"- **New matches only** (not in DB): {len(match_results.get('new_only', set())):,}\n")
        f.write(f"- **Existing matches only** (no enhanced data): {len(match_results.get('existing_only', set())):,}\n\n")
        
        # Player Analysis
        f.write("## Player Name Analysis\n\n")
        player_results = results.get('player_analysis', {})
        f.write(f"- **Exact name matches**: {len(player_results.get('exact_matches', set())):,}\n")
        f.write(f"- **Players in new only**: {len(player_results.get('new_only', set())):,}\n")
        f.write(f"- **Players in existing only**: {len(player_results.get('existing_only', set())):,}\n\n")
        
        # New-only players list
        new_only_players = player_results.get('new_only', set())
        if new_only_players:
            f.write("### Sample New-Only Players (first 50)\n\n")
            for name in sorted(list(new_only_players))[:50]:
                f.write(f"- {name}\n")
            f.write("\n")
        
        # Ball Integrity
        f.write("## Ball-Level Integrity\n\n")
        ball_results = results.get('ball_integrity', {})
        if ball_results:
            f.write("| Match ID | New Count | Existing Count | Match |\n")
            f.write("|----------|-----------|----------------|-------|\n")
            for match_id, data in ball_results.items():
                status = "✓" if data['match'] else "⚠"
                f.write(f"| {match_id} | {data['new_count']} | {data['existing_count']} | {status} |\n")
        else:
            f.write("No overlapping matches to check.\n")
        f.write("\n")
        
        # Recommendations
        f.write("## Recommendations\n\n")
        overlap_count = len(match_results.get('overlap', set()))
        new_only_count = len(match_results.get('new_only', set()))
        
        if overlap_count > 0:
            f.write(f"1. **{overlap_count:,} matches can be enhanced** with wagon wheel and shot data\n")
        if new_only_count > 0:
            f.write(f"2. **{new_only_count:,} new matches** available - consider adding to main database\n")
        
        f.write("\n### Next Steps\n\n")
        f.write("1. Create `delivery_details` table for enhanced ball data\n")
        f.write("2. Load overlapping match data first\n")
        f.write("3. Evaluate whether to add new-only matches to main tables\n")
        f.write("4. Build player ID mapping table for cleaner references\n")
    
    print(f"Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Validate new ball-by-ball dataset')
    parser.add_argument('--csv', type=str, required=True, help='Path to t20_bbb.csv')
    parser.add_argument('--sample', type=int, default=None, help='Sample size (rows) to load')
    parser.add_argument('--output', type=str, default='validation_report.md', help='Output report path')
    parser.add_argument('--db-url', type=str, default=None, help='Database URL (overrides env)')
    
    args = parser.parse_args()
    
    if args.db_url:
        global DB_URL_OVERRIDE
        DB_URL_OVERRIDE = args.db_url
    
    print("="*60)
    print("NEW DATASET VALIDATION SCRIPT")
    print("="*60)
    
    # Connect to database
    engine = connect_to_database()
    
    # Get existing data
    existing_match_ids = get_existing_match_ids(engine)
    existing_players = get_existing_player_names(engine)
    
    # Load new dataset
    new_df = load_new_dataset(args.csv, sample_size=args.sample)
    
    # Run analyses
    results = {}
    
    # Match analysis
    results['match_analysis'] = analyze_match_overlap(new_df, existing_match_ids)
    
    # Player analysis
    results['player_analysis'] = analyze_player_names(new_df, existing_players)
    
    # Data quality
    analyze_data_quality(new_df)
    
    # Ball integrity (only if there's overlap)
    overlap = results['match_analysis'].get('overlap', set())
    results['ball_integrity'] = analyze_ball_integrity(new_df, overlap, engine)
    
    # Generate report
    generate_report(results, args.output)
    
    print("\n" + "="*60)
    print("VALIDATION COMPLETE")
    print("="*60)
    
    return results


if __name__ == "__main__":
    main()
