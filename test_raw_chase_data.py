"""
Test raw chase data to understand if the source data is biased
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_session
from sqlalchemy import text
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_raw_chase_data():
    """Test the raw chase data to see if it's biased"""
    
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # Test raw chase outcomes for a specific venue
        venue = "Rajiv Gandhi International Stadium"
        through_date = date(2025, 12, 31)
        
        logger.info(f"Testing raw chase data for: {venue}")
        
        # Get basic chase statistics
        chase_stats_query = text("""
            WITH chase_data AS (
                SELECT 
                    d.match_id,
                    m.venue,
                    first_innings.total_runs + 1 as target,
                    CASE WHEN m.winner = d.batting_team THEN 1 ELSE 0 END as chase_successful,
                    COUNT(*) as ball_count
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                JOIN (
                    SELECT 
                        match_id,
                        SUM(runs_off_bat + extras) as total_runs
                    FROM deliveries 
                    WHERE innings = 1
                    GROUP BY match_id
                ) first_innings ON d.match_id = first_innings.match_id
                WHERE m.venue = :venue
                    AND m.date < :through_date
                    AND d.innings = 2
                    AND m.winner IS NOT NULL
                GROUP BY d.match_id, m.venue, first_innings.total_runs, m.winner, d.batting_team
            )
            SELECT 
                COUNT(DISTINCT match_id) as total_matches,
                AVG(target) as avg_target,
                MIN(target) as min_target,
                MAX(target) as max_target,
                SUM(chase_successful) as successful_chases,
                COUNT(*) as total_chase_records,
                AVG(CAST(chase_successful AS FLOAT)) as win_rate
            FROM chase_data
        """)
        
        result = session.execute(chase_stats_query, {
            "venue": venue,
            "through_date": through_date
        }).fetchone()
        
        logger.info(f"Raw chase statistics:")
        logger.info(f"  Total matches: {result.total_matches}")
        logger.info(f"  Total chase records: {result.total_chase_records}")
        logger.info(f"  Successful chases: {result.successful_chases}")
        logger.info(f"  Win rate: {result.win_rate:.3f}")
        logger.info(f"  Target range: {result.min_target} - {result.max_target}")
        logger.info(f"  Average target: {result.avg_target:.1f}")
        
        # Check for data issues
        if result.total_matches != result.total_chase_records:
            logger.warning(f"⚠️ Mismatch: {result.total_matches} matches but {result.total_chase_records} records!")
            logger.info("This suggests each match is creating multiple records - potential duplication issue")
            
        if result.win_rate == 0.0 or result.win_rate == 1.0:
            logger.warning(f"⚠️ Extreme win rate: {result.win_rate:.3f}")
            logger.info("This could explain why buckets have binary probabilities")
        
        # Sample individual matches to see the pattern
        sample_query = text("""
            WITH chase_data AS (
                SELECT DISTINCT
                    d.match_id,
                    m.venue,
                    m.date,
                    m.team1,
                    m.team2,
                    m.winner,
                    first_innings.total_runs + 1 as target,
                    CASE WHEN m.winner = d.batting_team THEN 1 ELSE 0 END as chase_successful
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                JOIN (
                    SELECT 
                        match_id,
                        SUM(runs_off_bat + extras) as total_runs
                    FROM deliveries 
                    WHERE innings = 1
                    GROUP BY match_id
                ) first_innings ON d.match_id = first_innings.match_id
                WHERE m.venue = :venue
                    AND m.date < :through_date
                    AND d.innings = 2
                    AND m.winner IS NOT NULL
            )
            SELECT *
            FROM chase_data
            ORDER BY date DESC
            LIMIT 10
        """)
        
        samples = session.execute(sample_query, {
            "venue": venue,
            "through_date": through_date
        }).fetchall()
        
        logger.info(f"\nSample matches:")
        for sample in samples:
            logger.info(f"  {sample.date}: {sample.team1} vs {sample.team2}")
            logger.info(f"    Target: {sample.target}, Winner: {sample.winner}, Success: {sample.chase_successful}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_raw_chase_data()
