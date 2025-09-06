#!/usr/bin/env python3
"""
Direct database test for phase stats queries
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_session
from sqlalchemy.sql import text
from datetime import date
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test basic database connectivity"""
    try:
        db = next(get_session())
        
        # Test basic query
        result = db.execute(text("SELECT COUNT(*) as count FROM matches")).fetchone()
        logger.info(f"✅ Database connected successfully. Total matches: {result.count}")
        
        # Test team variations function
        from services.teams_enhanced_logging import get_all_team_name_variations
        variations = get_all_team_name_variations("RCB")
        logger.info(f"✅ Team variations for RCB: {variations}")
        
        return db
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return None

def test_team_phase_stats_query(db, team_name="RCB"):
    """Test the team phase stats query in isolation"""
    
    logger.info(f"🔍 Testing team phase stats query for {team_name}")
    
    try:
        from services.teams_enhanced_logging import get_all_team_name_variations
        team_variations = get_all_team_name_variations(team_name)
        
        # Test the basic team stats query
        query = text("""
            WITH team_phase_aggregates AS (
                SELECT 
                    COALESCE(SUM(bs.pp_runs), 0) as total_pp_runs,
                    COALESCE(SUM(bs.pp_balls), 0) as total_pp_balls,
                    COALESCE(SUM(bs.pp_wickets), 0) as total_pp_wickets,
                    COALESCE(SUM(bs.middle_runs), 0) as total_middle_runs,
                    COALESCE(SUM(bs.middle_balls), 0) as total_middle_balls,
                    COALESCE(SUM(bs.middle_wickets), 0) as total_middle_wickets,
                    COALESCE(SUM(bs.death_runs), 0) as total_death_runs,
                    COALESCE(SUM(bs.death_balls), 0) as total_death_balls,
                    COALESCE(SUM(bs.death_wickets), 0) as total_death_wickets,
                    COUNT(DISTINCT bs.match_id) as total_matches
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE bs.batting_team = ANY(:team_variations)
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
            )
            SELECT 
                total_pp_runs, total_pp_balls, total_pp_wickets,
                total_middle_runs, total_middle_balls, total_middle_wickets,
                total_death_runs, total_death_balls, total_death_wickets,
                total_matches,
                CASE WHEN total_pp_wickets > 0 THEN ROUND(total_pp_runs::numeric / total_pp_wickets, 2) ELSE NULL END as pp_average,
                CASE WHEN total_pp_balls > 0 THEN ROUND(total_pp_runs::numeric * 100 / total_pp_balls, 2) ELSE 0 END as pp_strike_rate,
                CASE WHEN total_middle_wickets > 0 THEN ROUND(total_middle_runs::numeric / total_middle_wickets, 2) ELSE NULL END as middle_average,
                CASE WHEN total_middle_balls > 0 THEN ROUND(total_middle_runs::numeric * 100 / total_middle_balls, 2) ELSE 0 END as middle_strike_rate,
                CASE WHEN total_death_wickets > 0 THEN ROUND(total_death_runs::numeric / total_death_wickets, 2) ELSE NULL END as death_average,
                CASE WHEN total_death_balls > 0 THEN ROUND(total_death_runs::numeric * 100 / total_death_balls, 2) ELSE 0 END as death_strike_rate
            FROM team_phase_aggregates
        """)
        
        params = {
            "team_variations": team_variations,
            "start_date": date(2023, 1, 1),
            "end_date": date(2025, 9, 6)
        }
        
        logger.info(f"📊 Query parameters: {params}")
        
        result = db.execute(query, params).fetchone()
        
        if result:
            logger.info(f"✅ Team query successful!")
            logger.info(f"   - Total matches: {result.total_matches}")
            logger.info(f"   - PP runs: {result.total_pp_runs}, balls: {result.total_pp_balls}")
            logger.info(f"   - Middle runs: {result.total_middle_runs}, balls: {result.total_middle_balls}")
            logger.info(f"   - Death runs: {result.total_death_runs}, balls: {result.total_death_balls}")
            return True
        else:
            logger.warning("❓ Team query returned no results")
            return False
            
    except Exception as e:
        logger.error(f"❌ Team query failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_benchmark_query(db, team_name="RCB"):
    """Test the benchmark query in isolation"""
    
    logger.info(f"🔍 Testing benchmark query for {team_name}")
    
    try:
        from services.teams_enhanced_logging import get_all_team_name_variations
        team_variations = get_all_team_name_variations(team_name)
        
        # Simple benchmark query without percentiles first
        simple_query = text("""
            WITH team_stats AS (
                SELECT 
                    bs.batting_team,
                    SUM(bs.pp_runs)::float / NULLIF(SUM(bs.pp_wickets), 0) as team_pp_avg,
                    SUM(bs.pp_runs)::float * 100 / NULLIF(SUM(bs.pp_balls), 0) as team_pp_sr
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE m.match_type = 'league'
                AND bs.batting_team != ANY(:team_variations)
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY bs.batting_team
                HAVING SUM(bs.pp_balls) > 0
                LIMIT 5
            )
            SELECT 
                COUNT(*) as benchmark_teams,
                AVG(team_pp_avg) as pp_avg_mean,
                AVG(team_pp_sr) as pp_sr_mean
            FROM team_stats
        """)
        
        params = {
            "team_variations": team_variations,
            "start_date": date(2023, 1, 1),
            "end_date": date(2025, 9, 6)
        }
        
        logger.info(f"📊 Benchmark query parameters: {params}")
        
        result = db.execute(simple_query, params).fetchone()
        
        if result:
            logger.info(f"✅ Simple benchmark query successful!")
            logger.info(f"   - Benchmark teams: {result.benchmark_teams}")
            logger.info(f"   - PP avg mean: {result.pp_avg_mean}")
            logger.info(f"   - PP SR mean: {result.pp_sr_mean}")
            
            # Now test with percentiles
            logger.info("🔍 Testing with percentiles...")
            
            percentile_query = text("""
                WITH team_stats AS (
                    SELECT 
                        bs.batting_team,
                        SUM(bs.pp_runs)::float / NULLIF(SUM(bs.pp_wickets), 0) as team_pp_avg
                    FROM batting_stats bs
                    INNER JOIN matches m ON bs.match_id = m.id
                    WHERE m.match_type = 'league'
                    AND bs.batting_team != ANY(:team_variations)
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    GROUP BY bs.batting_team
                    HAVING SUM(bs.pp_balls) > 0
                )
                SELECT 
                    COUNT(*) as benchmark_teams,
                    percentile_cont(0.25) within group (order by team_pp_avg) as pp_avg_p25,
                    percentile_cont(0.50) within group (order by team_pp_avg) as pp_avg_p50,
                    percentile_cont(0.75) within group (order by team_pp_avg) as pp_avg_p75
                FROM team_stats
            """)
            
            percentile_result = db.execute(percentile_query, params).fetchone()
            
            if percentile_result:
                logger.info(f"✅ Percentile query successful!")
                logger.info(f"   - P25: {percentile_result.pp_avg_p25}")
                logger.info(f"   - P50: {percentile_result.pp_avg_p50}")
                logger.info(f"   - P75: {percentile_result.pp_avg_p75}")
                return True
            else:
                logger.warning("❓ Percentile query returned no results")
                return False
                
        else:
            logger.warning("❓ Benchmark query returned no results")
            return False
            
    except Exception as e:
        logger.error(f"❌ Benchmark query failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main test function"""
    print("🏏 Direct Database Testing for Phase Stats")
    print("="*60)
    
    # Test database connection
    db = test_database_connection()
    if not db:
        return
    
    # Test team phase stats query
    print("\n" + "="*40)
    if not test_team_phase_stats_query(db):
        print("❌ Team query failed - this is likely the issue!")
        return
    
    # Test benchmark query
    print("\n" + "="*40)
    if not test_benchmark_query(db):
        print("❌ Benchmark query failed - this might be the issue!")
        return
    
    print("\n" + "="*60)
    print("✅ All database queries passed!")
    print("🤔 The issue might be in the API layer or data processing")
    print("💡 Try running the enhanced debug script to see API-level errors")
    
    # Close database connection
    db.close()

if __name__ == "__main__":
    main()
