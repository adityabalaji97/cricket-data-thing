#!/usr/bin/env python3
"""
Full Delivery Details Sync Pipeline - One-click sync.

Usage:
    python run_full_dd_sync.py --dry-run      # Preview
    python run_full_dd_sync.py --confirm      # Run all steps
    python run_full_dd_sync.py --limit 100    # Test with limit
    python run_full_dd_sync.py --skip-elo     # Skip ELO step
"""

import argparse
import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_sync_pipeline(confirm=False, limit=None, skip_elo=False, dry_run=False):
    start_time = datetime.now()
    total_steps = 5 if skip_elo else 6
    results = {}
    
    print("\n" + "=" * 60)
    print("  DELIVERY DETAILS FULL SYNC PIPELINE")
    print("=" * 60)
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    if limit:
        print(f"⚠️  Limited to {limit} matches")
    if dry_run:
        print("⚠️  DRY RUN - No changes")
    
    # Step 1: Check status
    print(f"\n[1/{total_steps}] Checking sync status...")
    from sync_from_delivery_details import DeliveryDetailsSync
    syncer = DeliveryDetailsSync()
    status = syncer.check_sync_status()
    
    print(f"  delivery_details matches: {status['delivery_details_matches']:,}")
    print(f"  matches table: {status['matches_table_count']:,}")
    print(f"  Missing matches: {status['missing_in_matches']:,}")
    print(f"  Missing stats: {status['missing_batting_stats']:,}")
    results['status'] = status
    
    if dry_run:
        print(f"\n🔍 Would sync {status['missing_in_matches']} matches + stats")
        return results
    
    if not confirm and status['missing_in_matches'] > 0:
        response = input(f"\nSync {status['missing_in_matches']} matches? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled.")
            sys.exit(0)
    
    # Step 2: Create matches
    print(f"\n[2/{total_steps}] Creating matches...")
    if status['missing_in_matches'] > 0:
        result = syncer.create_matches_from_dd(limit=limit)
        results['matches'] = result
        print(f"  ✅ Created: {result['created']}, Errors: {result['errors']}")
    else:
        print("  ⏭️  No missing matches")
    
    # Step 3: Create stats
    print(f"\n[3/{total_steps}] Creating batting/bowling stats...")
    from sync_stats_from_dd import create_stats_from_delivery_details
    stats_result = create_stats_from_delivery_details(limit=limit)
    results['stats'] = stats_result
    print(f"  ✅ Batting: {stats_result['batting_created']}, Bowling: {stats_result['bowling_created']}")
    
    # Step 4: Venue standardization
    print(f"\n[4/{total_steps}] Standardizing venues...")
    try:
        from venue_standardization import standardize_venues
        standardize_venues()
        print("  ✅ Done")
    except Exception as e:
        print(f"  ⚠️  {e}")
    
    # Step 5: League names
    print(f"\n[5/{total_steps}] Fixing league names...")
    try:
        from fix_league_names import fix_league_names
        fix_league_names()
        print("  ✅ Done")
    except Exception as e:
        print(f"  ⚠️  {e}")
    
    # Step 6: ELO
    if not skip_elo:
        print(f"\n[6/{total_steps}] Calculating ELO...")
        try:
            from elo_update_service import ELOUpdateService
            elo_service = ELOUpdateService()
            elo_result = elo_service.calculate_missing_elo_ratings()
            print(f"  ✅ Updated: {elo_result.get('updated', 0)}")
        except Exception as e:
            print(f"  ⚠️  {e}")
    
    duration = datetime.now() - start_time
    print("\n" + "=" * 60)
    print(f"  COMPLETE - Duration: {duration}")
    print("=" * 60)
    return results


def main():
    parser = argparse.ArgumentParser(description='Full sync pipeline')
    parser.add_argument('--confirm', action='store_true', help='Skip prompts')
    parser.add_argument('--limit', type=int, help='Limit matches')
    parser.add_argument('--skip-elo', action='store_true', help='Skip ELO')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    args = parser.parse_args()
    
    try:
        run_sync_pipeline(confirm=args.confirm, limit=args.limit, 
                         skip_elo=args.skip_elo, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n❌ Interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
