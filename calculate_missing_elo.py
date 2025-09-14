#!/usr/bin/env python3
"""
Calculate Missing ELO Ratings

Standalone script to calculate ELO ratings for matches that don't have them yet.
Perfect for existing matches in your database that were loaded before ELO integration.

Usage Examples:
    # Calculate ELO for all missing matches
    python calculate_missing_elo.py
    
    # Test with limited matches first
    python calculate_missing_elo.py --max-matches 100
    
    # Verify current ELO status
    python calculate_missing_elo.py --verify-only
    
    # Show what would be done (dry run)
    python calculate_missing_elo.py --dry-run
"""

import sys
import logging
from datetime import datetime
from elo_update_service import ELOUpdateService
from database import get_session
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_elo_status():
    """Check and display current ELO status in the database"""
    session = next(get_session())
    
    try:
        logger.info("📊 Checking current ELO status...")
        
        # Get basic statistics
        total_matches = session.execute(text("SELECT COUNT(*) FROM matches")).scalar()
        
        matches_with_elo = session.execute(text("""
            SELECT COUNT(*) FROM matches 
            WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
        """)).scalar()
        
        matches_partial_elo = session.execute(text("""
            SELECT COUNT(*) FROM matches 
            WHERE (team1_elo IS NOT NULL AND team2_elo IS NULL) 
            OR (team1_elo IS NULL AND team2_elo IS NOT NULL)
        """)).scalar()
        
        matches_no_elo = total_matches - matches_with_elo - matches_partial_elo
        completion_pct = (matches_with_elo / total_matches * 100) if total_matches > 0 else 0
        
        # Get date ranges
        earliest_match = session.execute(text("""
            SELECT MIN(date) FROM matches
        """)).scalar()
        
        latest_match = session.execute(text("""
            SELECT MAX(date) FROM matches
        """)).scalar()
        
        earliest_elo = session.execute(text("""
            SELECT MIN(date) FROM matches 
            WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
        """)).scalar()
        
        latest_elo = session.execute(text("""
            SELECT MAX(date) FROM matches 
            WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
        """)).scalar()
        
        print(f"\n📊 ELO STATUS REPORT")
        print(f"=" * 50)
        print(f"Total matches in database: {total_matches:,}")
        print(f"Matches with complete ELO: {matches_with_elo:,} ({completion_pct:.1f}%)")
        print(f"Matches with partial ELO: {matches_partial_elo:,}")
        print(f"Matches without ELO: {matches_no_elo:,}")
        print(f"")
        print(f"📅 DATE RANGES:")
        print(f"All matches: {earliest_match} to {latest_match}")
        if earliest_elo and latest_elo:
            print(f"ELO coverage: {earliest_elo} to {latest_elo}")
        else:
            print(f"ELO coverage: No ELO data found")
        
        # Show sample missing matches
        if matches_no_elo > 0:
            print(f"\n📋 SAMPLE MATCHES WITHOUT ELO:")
            sample_missing = session.execute(text("""
                SELECT id, date, team1, team2, winner
                FROM matches 
                WHERE team1_elo IS NULL AND team2_elo IS NULL
                ORDER BY date ASC
                LIMIT 5
            """)).fetchall()
            
            print(f"{'Date':<12} {'Match ID':<15} {'Team1':<15} {'Team2':<15} {'Winner':<15}")
            print("-" * 80)
            for match in sample_missing:
                winner = match.winner or 'Tie/NR'
                print(f"{match.date.strftime('%Y-%m-%d'):<12} {match.id:<15} {match.team1:<15} {match.team2:<15} {winner:<15}")
        
        return {
            'total_matches': total_matches,
            'matches_with_elo': matches_with_elo,
            'matches_no_elo': matches_no_elo,
            'completion_percentage': completion_pct,
            'needs_calculation': matches_no_elo > 0
        }
        
    except Exception as e:
        logger.error(f"Error checking ELO status: {e}")
        raise
    finally:
        session.close()


def show_elo_calculation_preview(max_preview: int = 20):
    """Show preview of what ELO calculation would do"""
    session = next(get_session())
    
    try:
        logger.info(f"🔍 Generating ELO calculation preview...")
        
        # Get first few matches without ELO
        matches_to_preview = session.execute(text("""
            SELECT id, date, team1, team2, winner, match_type
            FROM matches 
            WHERE team1_elo IS NULL AND team2_elo IS NULL
            ORDER BY date ASC, id ASC
            LIMIT :limit
        """), {'limit': max_preview}).fetchall()
        
        if not matches_to_preview:
            print("\n✅ No matches need ELO calculation!")
            return
        
        print(f"\n🔮 ELO CALCULATION PREVIEW (First {len(matches_to_preview)} matches)")
        print(f"=" * 90)
        print(f"{'Date':<12} {'Match ID':<15} {'Team1':<15} {'Team2':<15} {'Winner':<15} {'Type':<8}")
        print("-" * 90)
        
        for match in matches_to_preview:
            winner = match.winner or 'Tie/NR'
            match_type = match.match_type or 'league'
            print(f"{match.date.strftime('%Y-%m-%d'):<12} {match.id:<15} {match.team1:<15} {match.team2:<15} {winner:<15} {match_type:<8}")
        
        print(f"\nℹ️  These matches will be processed in chronological order")
        print(f"ℹ️  ELO ratings will be calculated based on team performance history")
        print(f"ℹ️  Starting ratings depend on team tier (international teams have tiered starting values)")
        
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise
    finally:
        session.close()


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Calculate ELO ratings for existing matches without ratings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calculate_missing_elo.py                    # Calculate all missing ELO ratings
  python calculate_missing_elo.py --verify-only      # Just check current status
  python calculate_missing_elo.py --max-matches 100  # Test with limited matches
  python calculate_missing_elo.py --preview          # Show what would be calculated
  python calculate_missing_elo.py --dry-run          # Show preview + what would be done
        """
    )
    
    parser.add_argument('--verify-only', action='store_true',
                       help='Only check and display current ELO status')
    parser.add_argument('--preview', action='store_true',
                       help='Show preview of matches that would be calculated')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--max-matches', type=int,
                       help='Maximum number of matches to process (for testing)')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for processing (default: 1000)')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    print("🎯 MISSING ELO CALCULATOR")
    print("=" * 50)
    
    try:
        # Step 1: Check current status
        status = check_elo_status()
        
        if args.verify_only:
            print(f"\n✅ Verification complete!")
            return
        
        if not status['needs_calculation']:
            print(f"\n🎉 All matches already have ELO ratings!")
            return
        
        # Step 2: Show preview if requested
        if args.preview or args.dry_run:
            show_elo_calculation_preview()
            
            if args.preview and not args.dry_run:
                return
        
        # Step 3: Confirm calculation
        if not args.confirm and not args.dry_run:
            print(f"\n⚠️  Ready to calculate ELO ratings for {status['matches_no_elo']:,} matches")
            if args.max_matches:
                print(f"⚠️  Limited to {args.max_matches:,} matches for this run")
            print(f"⚠️  This will process matches chronologically and update the database")
            
            response = input(f"\nProceed with ELO calculation? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ Cancelled")
                return
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN - Would calculate ELO for {status['matches_no_elo']:,} matches")
            print(f"ℹ️  Use --confirm to actually run the calculation")
            return
        
        # Step 4: Run ELO calculation
        print(f"\n🚀 Starting ELO calculation...")
        start_time = datetime.now()
        
        service = ELOUpdateService()
        stats = service.calculate_missing_elo_ratings(
            batch_size=args.batch_size,
            max_matches=args.max_matches
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Step 5: Show results
        print(f"\n✅ ELO CALCULATION COMPLETE!")
        print(f"=" * 50)
        print(f"Matches processed: {stats['processed']:,}")
        print(f"Database records updated: {stats['updated']:,}")
        print(f"Errors encountered: {stats['errors']:,}")
        print(f"Execution time: {duration}")
        
        if stats['errors'] > 0:
            print(f"\n⚠️  {stats['errors']} errors occurred during processing")
            print(f"Check the logs above for details")
        
        # Step 6: Verify results
        print(f"\n🔍 Verifying results...")
        service.verify_elo_data(sample_size=10)
        
        print(f"\n🎉 ELO calculation completed successfully!")
        print(f"Your matches now have ELO ratings for analysis!")
        
    except KeyboardInterrupt:
        print(f"\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
