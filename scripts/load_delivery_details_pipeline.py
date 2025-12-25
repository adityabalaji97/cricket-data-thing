"""
Unified pipeline for loading and enhancing delivery_details data.

This script orchestrates the full data loading pipeline:
1. Validate dataset (optional)
2. Load new rows (with duplicate detection)
3. Populate non_striker and crease_combo columns
4. Update players table with bat_hand/bowl_style
5. Refresh query builder metadata

Usage:
    # Full pipeline with dry run
    python scripts/load_delivery_details_pipeline.py --csv /path/to/t20_bbb.csv --db-url "postgres://..." --dry-run
    
    # Full pipeline (actual execution)
    python scripts/load_delivery_details_pipeline.py --csv /path/to/t20_bbb.csv --db-url "postgres://..."
    
    # Skip validation step
    python scripts/load_delivery_details_pipeline.py --csv /path/to/t20_bbb.csv --db-url "postgres://..." --skip-validation
    
    # Using environment variable
    DATABASE_URL="postgres://..." python scripts/load_delivery_details_pipeline.py --csv /path/to/t20_bbb.csv
"""

import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_url(args):
    """Get database URL from args or environment."""
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: Database URL required. Use --db-url or set DATABASE_URL environment variable.")
        sys.exit(1)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def print_header(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def step_validate(csv_path, db_url, dry_run=False):
    """Step 1: Validate the dataset."""
    print_header("STEP 1: VALIDATION")
    
    from validate_new_dataset import (
        connect_to_database, get_existing_match_ids, get_existing_player_names,
        load_new_dataset, analyze_match_overlap, analyze_data_quality
    )
    
    # Temporarily set the DB URL override
    import validate_new_dataset
    validate_new_dataset.DB_URL_OVERRIDE = db_url
    
    engine = connect_to_database()
    existing_match_ids = get_existing_match_ids(engine)
    
    # Load sample for quick validation
    new_df = load_new_dataset(csv_path, sample_size=100000)
    
    match_analysis = analyze_match_overlap(new_df, existing_match_ids)
    analyze_data_quality(new_df)
    
    overlap_count = len(match_analysis.get('overlap', set()))
    new_only_count = len(match_analysis.get('new_only', set()))
    
    print(f"\n✓ Validation complete")
    print(f"  - Overlapping matches: {overlap_count:,}")
    print(f"  - New matches: {new_only_count:,}")
    
    return True


def step_load(csv_path, db_url, dry_run=False):
    """Step 2: Load new rows with duplicate detection."""
    print_header("STEP 2: LOAD DATA")
    
    from sqlalchemy import create_engine
    from load_delivery_details_full import get_existing_keys, load_csv, get_engine
    
    engine = get_engine(db_url)
    
    # Get existing keys for duplicate detection
    existing_keys = get_existing_keys(engine)
    
    # Load new data
    results = load_csv(csv_path, engine, dry_run=dry_run, existing_keys=existing_keys)
    
    print(f"\n✓ Load complete")
    print(f"  - CSV rows: {results['total_in_csv']:,}")
    print(f"  - Skipped (existing): {results['total_skipped']:,}")
    print(f"  - {'Would insert' if dry_run else 'Inserted'}: {results['total_inserted']:,}")
    
    return results


def step_populate_columns(db_url, dry_run=False):
    """Step 3: Populate non_striker and crease_combo columns."""
    print_header("STEP 3: POPULATE COLUMNS (non_striker, crease_combo)")
    
    from sqlalchemy import create_engine, text
    
    engine = create_engine(db_url)
    
    if dry_run:
        # Just show current state
        with engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM delivery_details")).scalar()
            with_ns = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE non_striker IS NOT NULL")).scalar()
            with_cc = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE crease_combo IS NOT NULL")).scalar()
        
        print(f"[DRY RUN] Current state:")
        print(f"  - Total records: {total:,}")
        print(f"  - With non_striker: {with_ns:,} ({100*with_ns/total:.1f}%)" if total > 0 else "  - With non_striker: 0")
        print(f"  - With crease_combo: {with_cc:,} ({100*with_cc/total:.1f}%)" if total > 0 else "  - With crease_combo: 0")
        return
    
    # Import and run the column population functions
    from add_left_right_columns import (
        add_columns, populate_non_striker, infer_non_striker,
        populate_striker_batter_type, populate_non_striker_batter_type,
        generate_crease_combo, print_summary
    )
    
    add_columns(engine)
    populate_non_striker(engine)
    infer_non_striker(engine)
    populate_striker_batter_type(engine)
    populate_non_striker_batter_type(engine)
    generate_crease_combo(engine)
    print_summary(engine)
    
    print(f"\n✓ Column population complete")


def step_update_players(db_url, dry_run=False):
    """Step 4: Update players table with bat_hand/bowl_style."""
    print_header("STEP 4: UPDATE PLAYERS TABLE")
    
    from sqlalchemy import create_engine
    from update_players_from_new_data import (
        create_aliases_table, build_player_mapping, update_players, print_summary
    )
    
    engine = create_engine(db_url)
    
    create_aliases_table(engine)
    batters, bowlers = build_player_mapping(engine)
    update_players(engine, batters, bowlers, dry_run=dry_run)
    
    if not dry_run:
        print_summary(engine)
    
    print(f"\n✓ Players update complete")


def step_refresh_metadata(db_url, dry_run=False):
    """Step 5: Refresh query builder metadata."""
    print_header("STEP 5: REFRESH METADATA")
    
    if dry_run:
        print("[DRY RUN] Would refresh query_builder_metadata table")
        return
    
    from sqlalchemy import create_engine
    from refresh_query_builder_metadata import refresh_metadata, show_metadata
    
    engine = create_engine(db_url)
    refresh_metadata(engine)
    show_metadata(engine)
    
    print(f"\n✓ Metadata refresh complete")


def main():
    parser = argparse.ArgumentParser(
        description='Unified pipeline for loading and enhancing delivery_details data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps:
  1. Validate dataset (sample check)
  2. Load new rows (with duplicate detection)
  3. Populate non_striker and crease_combo columns
  4. Update players table with bat_hand/bowl_style
  5. Refresh query builder metadata

Examples:
  # Dry run (no changes)
  python scripts/load_delivery_details_pipeline.py --csv data.csv --db-url "postgres://..." --dry-run

  # Full execution
  python scripts/load_delivery_details_pipeline.py --csv data.csv --db-url "postgres://..."
        """
    )
    parser.add_argument('--csv', required=True, help='Path to t20_bbb.csv')
    parser.add_argument('--db-url', help='Database URL (or set DATABASE_URL env var)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen without making changes')
    parser.add_argument('--skip-validation', action='store_true', help='Skip the validation step')
    parser.add_argument('--skip-load', action='store_true', help='Skip the data loading step')
    parser.add_argument('--skip-columns', action='store_true', help='Skip the column population step')
    parser.add_argument('--skip-players', action='store_true', help='Skip the players update step')
    parser.add_argument('--skip-metadata', action='store_true', help='Skip the metadata refresh step')
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.csv):
        print(f"ERROR: CSV file not found: {args.csv}")
        sys.exit(1)
    
    db_url = get_db_url(args)
    db_display = db_url.split('@')[1] if '@' in db_url else 'localhost'
    
    # Print banner
    print("\n" + "=" * 70)
    print("  DELIVERY DETAILS DATA PIPELINE")
    print("=" * 70)
    print(f"  CSV: {args.csv}")
    print(f"  Database: {db_display}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE EXECUTION'}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Validate
        if not args.skip_validation:
            step_validate(args.csv, db_url, dry_run=args.dry_run)
        else:
            print("\n[SKIPPED] Step 1: Validation")
        
        # Step 2: Load
        if not args.skip_load:
            step_load(args.csv, db_url, dry_run=args.dry_run)
        else:
            print("\n[SKIPPED] Step 2: Load Data")
        
        # Step 3: Populate columns
        if not args.skip_columns:
            step_populate_columns(db_url, dry_run=args.dry_run)
        else:
            print("\n[SKIPPED] Step 3: Populate Columns")
        
        # Step 4: Update players
        if not args.skip_players:
            step_update_players(db_url, dry_run=args.dry_run)
        else:
            print("\n[SKIPPED] Step 4: Update Players")
        
        # Step 5: Refresh metadata
        if not args.skip_metadata:
            step_refresh_metadata(db_url, dry_run=args.dry_run)
        else:
            print("\n[SKIPPED] Step 5: Refresh Metadata")
        
        # Final summary
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("  PIPELINE COMPLETE")
        print("=" * 70)
        print(f"  Elapsed time: {elapsed:.1f} seconds")
        print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if args.dry_run:
            print("\n*** DRY RUN COMPLETE - No changes were made ***")
        
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n\nERROR: Pipeline failed!")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
