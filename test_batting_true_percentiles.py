#!/usr/bin/env python3
"""
Test script for the updated batting phase stats with true SQL percentiles
"""

import sys
sys.path.append('/Users/adityabalaji/cdt/cricket-data-thing')

from database import get_session
from services.teams_fixed import get_team_phase_stats_service_fixed
from datetime import date
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_batting_true_percentiles():
    """
    Test the updated batting function with true SQL percentiles
    """
    logger.info("=== TESTING TRUE PERCENTILES FOR BATTING STATS ===")
    
    try:
        # Get database session
        db = next(get_session())
        
        # Test with an IPL team (should use IPL context)
        logger.info("\n1. Testing with IPL team (RCB):")
        rcb_stats = get_team_phase_stats_service_fixed(
            team_name="RCB",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            players=None,
            db=db
        )
        
        logger.info(f"RCB Results:")
        logger.info(f"  Context: {rcb_stats['context']}")
        logger.info(f"  Benchmark teams: {rcb_stats['benchmark_teams']}")
        logger.info(f"  Total matches: {rcb_stats['total_matches']}")
        logger.info(f"  PP Strike Rate: {rcb_stats['powerplay']['strike_rate']:.1f} (Percentile: {rcb_stats['powerplay']['normalized_strike_rate']})")
        logger.info(f"  Middle Strike Rate: {rcb_stats['middle_overs']['strike_rate']:.1f} (Percentile: {rcb_stats['middle_overs']['normalized_strike_rate']})")
        logger.info(f"  Death Strike Rate: {rcb_stats['death_overs']['strike_rate']:.1f} (Percentile: {rcb_stats['death_overs']['normalized_strike_rate']})")
        
        # Test with custom players
        logger.info("\n2. Testing with custom players:")
        custom_stats = get_team_phase_stats_service_fixed(
            team_name="Custom Team",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            players=["V Kohli", "AB de Villiers", "MS Dhoni"],
            db=db
        )
        
        logger.info(f"Custom Players Results:")
        logger.info(f"  Context: {custom_stats['context']}")
        logger.info(f"  Benchmark teams: {custom_stats['benchmark_teams']}")
        logger.info(f"  Total matches: {custom_stats['total_matches']}")
        logger.info(f"  PP Strike Rate: {custom_stats['powerplay']['strike_rate']:.1f} (Percentile: {custom_stats['powerplay']['normalized_strike_rate']})")
        
        # Test with international team (if available)
        logger.info("\n3. Testing with international team (India):")
        india_stats = get_team_phase_stats_service_fixed(
            team_name="India",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            players=None,
            db=db
        )
        
        logger.info(f"India Results:")
        logger.info(f"  Context: {india_stats['context']}")
        logger.info(f"  Benchmark teams: {india_stats['benchmark_teams']}")
        logger.info(f"  Total matches: {india_stats['total_matches']}")
        if india_stats['total_matches'] > 0:
            logger.info(f"  PP Strike Rate: {india_stats['powerplay']['strike_rate']:.1f} (Percentile: {india_stats['powerplay']['normalized_strike_rate']})")
        
        logger.info("\n=== TEST COMPLETED SUCCESSFULLY ===")
        
        # Check if we got true percentiles vs fallback
        if "True SQL Percentiles" in rcb_stats['context']:
            logger.info("✅ TRUE PERCENTILES: Successfully using true SQL percentiles!")
            logger.info(f"✅ BENCHMARK DATA: {rcb_stats['benchmark_teams']} teams used for benchmarking")
        elif "Simplified Fallback" in rcb_stats['context']:
            logger.info("⚠️  FALLBACK: Using simplified normalization due to insufficient data")
        else:
            logger.info("❓ UNKNOWN: Unexpected context format")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    success = test_batting_true_percentiles()
    if success:
        print("\n🎉 Batting true percentiles implementation is working!")
    else:
        print("\n💥 There were errors in the implementation.")
        sys.exit(1)
