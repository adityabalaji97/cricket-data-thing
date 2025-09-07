#!/usr/bin/env python3
"""
Complete ELO Rating System Setup Script

This script:
1. Runs database migration to add ELO columns
2. Calculates historical ELO ratings for all matches
3. Provides verification of the results

Usage:
    python setup_elo_system.py                 # Full setup (only calculates missing ELOs)
    python setup_elo_system.py --dry-run       # Test run without database updates
    python setup_elo_system.py --recalculate   # Clear existing ELO data and recalculate all
    python setup_elo_system.py --recalculate --dry-run  # Test recalculation
    python setup_elo_system.py --verify-only   # Just verify existing ELO data
"""

import sys
import logging
from datetime import datetime
from run_elo_migration import run_elo_migration
from elo_calculator import calculate_historical_elos, verify_elo_calculation
from database import get_session
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_status():
    """Check current status of ELO implementation"""
    session = next(get_session())
    
    try:
        logger.info("=== DATABASE STATUS CHECK ===")
        
        # Check if ELO columns exist
        result = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'matches' 
            AND column_name IN ('team1_elo', 'team2_elo')
        """)).fetchall()
        
        elo_columns_exist = len(result) == 2
        logger.info(f"ELO columns exist: {elo_columns_exist}")
        
        # Check total matches
        total_matches = session.execute(text("SELECT COUNT(*) FROM matches")).scalar()
        logger.info(f"Total matches in database: {total_matches}")
        
        # Check matches with ELO data
        matches_with_elo = session.execute(text("""
            SELECT COUNT(*) FROM matches 
            WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
        """)).scalar() if elo_columns_exist else 0
        
        logger.info(f"Matches with ELO data: {matches_with_elo}")
        
        if elo_columns_exist and matches_with_elo > 0:
            # Show date range of ELO data
            date_range = session.execute(text("""
                SELECT MIN(date) as min_date, MAX(date) as max_date 
                FROM matches 
                WHERE team1_elo IS NOT NULL
            """)).fetchone()
            
            logger.info(f"ELO data date range: {date_range.min_date} to {date_range.max_date}")
        
        return {
            'elo_columns_exist': elo_columns_exist,
            'total_matches': total_matches,
            'matches_with_elo': matches_with_elo,
            'completion_percentage': (matches_with_elo / total_matches * 100) if total_matches > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error checking database status: {e}")
        return None
    finally:
        session.close()

def clear_elo_data(dry_run: bool = False):
    """Clear all existing ELO data from matches table"""
    session = next(get_session())
    
    try:
        if dry_run:
            logger.info("Would clear all ELO data from matches table (dry run)")
            return
        
        logger.info("Clearing existing ELO data...")
        
        # Clear ELO columns
        result = session.execute(text("""
            UPDATE matches 
            SET team1_elo = NULL, team2_elo = NULL 
            WHERE team1_elo IS NOT NULL OR team2_elo IS NOT NULL
        """))
        
        rows_updated = result.rowcount
        session.commit()
        
        logger.info(f"Cleared ELO data from {rows_updated} matches")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error clearing ELO data: {e}")
        raise
    finally:
        session.close()


def show_sample_elo_data():
    """Show sample ELO data for verification"""
    session = next(get_session())
    
    try:
        # Get some recent matches with high-profile teams
        matches = session.execute(text("""
            SELECT date, team1, team1_elo, team2, team2_elo, winner
            FROM matches 
            WHERE team1_elo IS NOT NULL 
            AND (team1 IN ('India', 'Australia', 'England') OR team2 IN ('India', 'Australia', 'England'))
            ORDER BY date DESC 
            LIMIT 10
        """)).fetchall()
        
        if matches:
            logger.info("\n=== SAMPLE ELO DATA ===")
            logger.info(f"{'Date':<12} {'Team1':<15} {'ELO1':<5} {'Team2':<15} {'ELO2':<5} {'Winner':<15}")
            logger.info("-" * 80)
            
            for match in matches:
                winner = match.winner or "Tie/NR"
                logger.info(f"{match.date.strftime('%Y-%m-%d'):<12} {match.team1:<15} {match.team1_elo:<5} {match.team2:<15} {match.team2_elo:<5} {winner:<15}")
        else:
            logger.info("No ELO data found for sample teams")
            
    except Exception as e:
        logger.error(f"Error showing sample data: {e}")
    finally:
        session.close()

def main():
    """Main setup function"""
    start_time = datetime.now()
    
    # Parse command line arguments
    dry_run = '--dry-run' in sys.argv
    verify_only = '--verify-only' in sys.argv
    recalculate = '--recalculate' in sys.argv
    
    logger.info("=== ELO RATING SYSTEM SETUP ===")
    logger.info(f"Start time: {start_time}")
    
    if dry_run:
        logger.info("DRY RUN MODE - No database changes will be made")
    if recalculate:
        logger.info("RECALCULATE MODE - Will clear existing ELO data and recalculate")
    
    try:
        # Check current status
        status = check_database_status()
        if not status:
            logger.error("Failed to check database status")
            return
        
        if verify_only:
            logger.info("VERIFY-ONLY MODE - Just checking existing data")
            show_sample_elo_data()
            verify_elo_calculation(sample_size=20)
            return
        
        # Step 1: Run migration if needed
        if not status['elo_columns_exist']:
            logger.info("Step 1: Running database migration...")
            if not dry_run:
                run_elo_migration()
            else:
                logger.info("(Skipping migration in dry-run mode)")
        else:
            logger.info("Step 1: ELO columns already exist, skipping migration")
        
        # Step 1.5: Clear existing data if recalculating
        if recalculate and status['matches_with_elo'] > 0:
            logger.info("Step 1.5: Clearing existing ELO data for recalculation...")
            clear_elo_data(dry_run)
            # Update status after clearing
            if not dry_run:
                status = check_database_status()
        
        # Step 2: Calculate historical ELOs if needed
        need_calculation = (recalculate or status['matches_with_elo'] < status['total_matches'])
        if need_calculation:
            missing_count = status['total_matches'] - (0 if recalculate else status['matches_with_elo'])
            logger.info(f"Step 2: Calculating ELO ratings for {missing_count} matches...")
            calculate_historical_elos(dry_run=dry_run)
        else:
            logger.info("Step 2: All matches already have ELO data")
        
        # Step 3: Verification
        if not dry_run:
            logger.info("Step 3: Verifying results...")
            show_sample_elo_data()
            verify_elo_calculation()
        
        # Final status
        if not dry_run:
            final_status = check_database_status()
            logger.info(f"\n=== SETUP COMPLETE ===")
            logger.info(f"ELO data completion: {final_status['completion_percentage']:.1f}%")
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Total execution time: {duration}")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise

if __name__ == "__main__":
    main()
