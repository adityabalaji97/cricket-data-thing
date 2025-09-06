"""
Debug specific WPA query for venue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_session
from sqlalchemy import text
from datetime import date

def debug_wpa_query():
    """
    Debug the exact WPA query for a specific venue
    """
    print("🔍 Debugging WPA Query for Wankhede Stadium")
    print("=" * 50)
    
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        venue = "Wankhede Stadium, Mumbai"
        before_date = date(2023, 6, 1)
        league = "IPL"
        
        print(f"🏟️ Venue: {venue}")
        print(f"📅 Before: {before_date}")
        print(f"🏆 League: {league}")
        
        # Test the chase matches CTE first
        chase_query = text("""
            WITH chase_matches AS (
                -- Get second innings target and result for each match
                SELECT 
                    m.id as match_id,
                    m.winner,
                    first_inn.team1_score as target,
                    second_inn.team2_score as chase_score,
                    second_inn.batting_team as chasing_team,
                    CASE 
                        WHEN m.winner = second_inn.batting_team THEN 1 
                        ELSE 0 
                    END as won_chase
                FROM matches m
                JOIN (
                    -- First innings total
                    SELECT 
                        match_id,
                        SUM(runs_off_bat + extras) as team1_score
                    FROM deliveries
                    WHERE innings = 1
                    GROUP BY match_id
                ) first_inn ON m.id = first_inn.match_id
                JOIN (
                    -- Second innings details
                    SELECT 
                        match_id,
                        batting_team,
                        SUM(runs_off_bat + extras) as team2_score
                    FROM deliveries
                    WHERE innings = 2
                    GROUP BY match_id, batting_team
                ) second_inn ON m.id = second_inn.match_id
                WHERE m.venue = :venue
                    AND m.date < :before_date
                    AND (:league IS NULL OR m.competition = :league)
                    AND m.winner IS NOT NULL  -- Only completed matches
            )
            SELECT COUNT(*) as chase_match_count,
                   AVG(target) as avg_target,
                   AVG(CASE WHEN won_chase = 1 THEN 1.0 ELSE 0.0 END) as win_rate
            FROM chase_matches
        """)
        
        result = session.execute(chase_query, {
            "venue": venue,
            "before_date": before_date,
            "league": league
        }).fetchone()
        
        print(f"\n📊 Chase Matches Analysis:")
        print(f"  Total chase matches: {result.chase_match_count}")
        print(f"  Average target: {result.avg_target:.1f}" if result.avg_target else "  Average target: N/A")
        print(f"  Win rate: {result.win_rate:.3f}" if result.win_rate else "  Win rate: N/A")
        
        if result.chase_match_count == 0:
            print("\n❌ No chase matches found. Let's debug further...")
            
            # Check basic matches at venue
            basic_query = text("""
                SELECT COUNT(*) as total_matches
                FROM matches m
                WHERE m.venue = :venue
                AND m.date < :before_date
                AND (:league IS NULL OR m.competition = :league)
            """)
            
            basic_result = session.execute(basic_query, {
                "venue": venue,
                "before_date": before_date,
                "league": league
            }).fetchone()
            
            print(f"  Basic matches at venue: {basic_result.total_matches}")
            
            # Check matches with winners
            winner_query = text("""
                SELECT COUNT(*) as matches_with_winners
                FROM matches m
                WHERE m.venue = :venue
                AND m.date < :before_date
                AND (:league IS NULL OR m.competition = :league)
                AND m.winner IS NOT NULL
            """)
            
            winner_result = session.execute(winner_query, {
                "venue": venue,
                "before_date": before_date,
                "league": league
            }).fetchone()
            
            print(f"  Matches with winners: {winner_result.matches_with_winners}")
            
            # Check deliveries
            delivery_query = text("""
                SELECT 
                    COUNT(DISTINCT d.match_id) as matches_with_deliveries,
                    COUNT(CASE WHEN d.innings = 1 THEN 1 END) as innings1_deliveries,
                    COUNT(CASE WHEN d.innings = 2 THEN 1 END) as innings2_deliveries
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE m.venue = :venue
                AND m.date < :before_date
                AND (:league IS NULL OR m.competition = :league)
            """)
            
            delivery_result = session.execute(delivery_query, {
                "venue": venue,
                "before_date": before_date,
                "league": league
            }).fetchone()
            
            print(f"  Matches with deliveries: {delivery_result.matches_with_deliveries}")
            print(f"  Innings 1 deliveries: {delivery_result.innings1_deliveries}")
            print(f"  Innings 2 deliveries: {delivery_result.innings2_deliveries}")
            
        else:
            print(f"\n✅ Found chase data! Testing full query...")
            
            # Test the full WPA query (simplified)
            full_query = text("""
                WITH chase_matches AS (
                    SELECT 
                        m.id as match_id,
                        m.winner,
                        first_inn.team1_score as target,
                        second_inn.team2_score as chase_score,
                        second_inn.batting_team as chasing_team,
                        CASE WHEN m.winner = second_inn.batting_team THEN 1 ELSE 0 END as won_chase
                    FROM matches m
                    JOIN (
                        SELECT match_id, SUM(runs_off_bat + extras) as team1_score
                        FROM deliveries WHERE innings = 1 GROUP BY match_id
                    ) first_inn ON m.id = first_inn.match_id
                    JOIN (
                        SELECT match_id, batting_team, SUM(runs_off_bat + extras) as team2_score
                        FROM deliveries WHERE innings = 2 GROUP BY match_id, batting_team
                    ) second_inn ON m.id = second_inn.match_id
                    WHERE m.venue = :venue AND m.date < :before_date 
                    AND (:league IS NULL OR m.competition = :league) AND m.winner IS NOT NULL
                )
                SELECT 
                    COUNT(DISTINCT d.match_id) as unique_matches,
                    COUNT(*) as total_ball_states,
                    MIN(cm.target) as min_target,
                    MAX(cm.target) as max_target
                FROM deliveries d
                JOIN chase_matches cm ON d.match_id = cm.match_id
                WHERE d.innings = 2 AND d.over < 20
            """)
            
            full_result = session.execute(full_query, {
                "venue": venue,
                "before_date": before_date,
                "league": league
            }).fetchone()
            
            print(f"  Unique chase matches in deliveries: {full_result.unique_matches}")
            print(f"  Total ball states: {full_result.total_ball_states}")
            print(f"  Target range: {full_result.min_target} - {full_result.max_target}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_wpa_query()
