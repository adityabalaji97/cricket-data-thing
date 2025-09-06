"""
Debug script to investigate why no historical match states are found
"""

import sys
import os
import traceback
from datetime import date

def debug_historical_states():
    try:
        print("🔍 Debugging Historical Match States")
        print("=" * 50)
        
        from database import get_session
        from context_model import VenueResourceTableBuilder
        from sqlalchemy import text
        
        # Initialize
        builder = VenueResourceTableBuilder()
        session_gen = get_session()
        session = next(session_gen)
        
        # Test venue from the previous run
        test_venue = "Shere Bangla National Stadium, Mirpur"
        test_date = date(2023, 1, 1)
        test_league = "IPL"
        
        print(f"Testing venue: {test_venue}")
        print(f"Before date: {test_date}")
        print(f"League filter: {test_league}")
        
        # Step 1: Check if matches exist at this venue
        matches_query = text("""
            SELECT COUNT(*) as total_matches,
                   MIN(date) as first_match,
                   MAX(date) as last_match,
                   COUNT(CASE WHEN date < :test_date THEN 1 END) as matches_before_date
            FROM matches 
            WHERE venue = :venue
        """)\n        
        matches_result = session.execute(matches_query, {
            "venue": test_venue,
            "test_date": test_date
        }).fetchone()
        
        print(f"\n📊 Match Statistics:")
        print(f"   Total matches: {matches_result.total_matches}")
        print(f"   Date range: {matches_result.first_match} to {matches_result.last_match}")
        print(f"   Matches before {test_date}: {matches_result.matches_before_date}")
        
        # Step 2: Check competitions at this venue
        competitions_query = text("""
            SELECT competition, COUNT(*) as count
            FROM matches 
            WHERE venue = :venue
            AND date < :test_date
            GROUP BY competition
            ORDER BY COUNT(*) DESC
        """)
        
        competitions_result = session.execute(competitions_query, {
            "venue": test_venue,
            "test_date": test_date
        }).fetchall()
        
        print(f"\n📋 Competitions at venue (before {test_date}):")
        for comp in competitions_result:
            print(f"   {comp.competition}: {comp.count} matches")
        
        # Step 3: Check if deliveries exist for this venue
        deliveries_query = text("""
            SELECT COUNT(*) as delivery_count,
                   COUNT(DISTINCT d.match_id) as unique_matches,
                   MIN(d.innings) as min_innings,
                   MAX(d.innings) as max_innings
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE m.venue = :venue
            AND m.date < :test_date
        """)
        
        deliveries_result = session.execute(deliveries_query, {
            "venue": test_venue,
            "test_date": test_date
        }).fetchone()
        
        print(f"\n📦 Delivery Statistics:")
        print(f"   Total deliveries: {deliveries_result.delivery_count}")
        print(f"   Unique matches with deliveries: {deliveries_result.unique_matches}")
        print(f"   Innings range: {deliveries_result.min_innings} to {deliveries_result.max_innings}")
        
        # Step 4: Test our original query step by step
        print(f"\n🔍 Testing Original Query Components...")
        
        # Test without league filter first
        test_query_no_league = text("""
            WITH match_states AS (
                SELECT 
                    d.match_id,
                    d.over,
                    COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END) as wickets,
                    SUM(d2.runs_off_bat + d2.extras) as runs_so_far,
                    final_scores.final_score
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                JOIN deliveries d2 ON d.match_id = d2.match_id 
                    AND d.innings = d2.innings 
                    AND (d2.over < d.over OR (d2.over = d.over AND d2.ball <= d.ball))
                JOIN (
                    SELECT 
                        match_id,
                        innings,
                        SUM(runs_off_bat + extras) as final_score
                    FROM deliveries
                    WHERE innings = 1
                    GROUP BY match_id, innings
                ) final_scores ON d.match_id = final_scores.match_id 
                    AND d.innings = final_scores.innings
                WHERE d.innings = 1
                    AND m.venue = :venue
                    AND m.date < :before_date
                    AND d.over < 20
                GROUP BY d.match_id, d.over, d.ball, final_scores.final_score
                HAVING COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END) < 10
            )
            SELECT COUNT(*) as state_count
            FROM match_states
        """)
        
        no_league_result = session.execute(test_query_no_league, {
            "venue": test_venue,
            "before_date": test_date
        }).fetchone()
        
        print(f"   Without league filter: {no_league_result.state_count} states")
        
        # Test with a more common league for this venue
        if competitions_result:
            common_league = competitions_result[0].competition
            print(f"   Testing with most common league: {common_league}")
            
            states_with_common_league = builder.get_historical_match_states(
                session, test_venue, 1, test_date, common_league
            )
            print(f"   With {common_league}: {len(states_with_common_league)} states")
        
        # Step 5: Test with a later date
        later_date = date(2024, 1, 1)
        print(f"\n📅 Testing with later date: {later_date}")
        
        states_later_date = builder.get_historical_match_states(
            session, test_venue, 1, later_date, None
        )
        print(f"   States with later date (no league filter): {len(states_later_date)}")
        
        if states_later_date:
            print("   Sample states:")
            for i, state in enumerate(states_later_date[:3]):
                print(f"     Over {state['over']}, {state['wickets']} wickets: {state['avg_runs_so_far']:.1f} runs")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_historical_states()
