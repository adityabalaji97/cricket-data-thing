"""
Debug script to check venue names and data availability
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_session
from sqlalchemy import text
from datetime import date

def debug_venue_data():
    """
    Debug venue data to understand filtering issues
    """
    print("🔍 Debugging Venue Data")
    print("=" * 40)
    
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # Check available venues
        print("📊 Top venues by match count:")
        venue_query = text("""
            SELECT venue, COUNT(*) as match_count,
                   MIN(date) as earliest_date,
                   MAX(date) as latest_date
            FROM matches 
            WHERE venue IS NOT NULL 
            GROUP BY venue 
            ORDER BY COUNT(*) DESC 
            LIMIT 15
        """)
        
        venues = session.execute(venue_query).fetchall()
        
        for venue in venues:
            print(f"  {venue.venue}: {venue.match_count} matches ({venue.earliest_date} to {venue.latest_date})")
        
        # Test specific venue names with different variations
        test_venues = [
            "Wankhede Stadium", 
            "Wankhede Stadium, Mumbai",
            "Mumbai",
            "Eden Gardens",
            "Eden Gardens, Kolkata", 
            "Kolkata"
        ]
        
        print(f"\n🔍 Testing specific venue name matches:")
        for test_venue in test_venues:
            count_query = text("""
                SELECT COUNT(*) as count
                FROM matches 
                WHERE venue = :venue
                AND date < :test_date
            """)
            
            result = session.execute(count_query, {
                "venue": test_venue,
                "test_date": date(2023, 6, 1)
            }).fetchone()
            
            print(f"  '{test_venue}': {result.count} matches before 2023-06-01")
        
        # Check venue names containing keywords
        print(f"\n🔍 Venues containing 'Wankhede':")
        wankhede_query = text("""
            SELECT venue, COUNT(*) as count
            FROM matches 
            WHERE venue ILIKE '%wankhede%'
            AND date < :test_date
            GROUP BY venue
        """)
        
        wankhede_results = session.execute(wankhede_query, {
            "test_date": date(2023, 6, 1)
        }).fetchall()
        
        for result in wankhede_results:
            print(f"  '{result.venue}': {result.count} matches")
        
        # Check if we have any second innings data at all
        print(f"\n📈 Checking second innings data availability:")
        
        # Get a venue with good data
        good_venue = venues[0].venue if venues else None
        if good_venue:
            print(f"Testing with: {good_venue}")
            
            # Check second innings matches
            second_innings_query = text("""
                SELECT COUNT(DISTINCT d.match_id) as match_count,
                       COUNT(*) as delivery_count
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.innings = 2
                AND m.venue = :venue
                AND m.date < :test_date
            """)
            
            second_result = session.execute(second_innings_query, {
                "venue": good_venue,
                "test_date": date(2023, 6, 1)
            }).fetchone()
            
            print(f"  Second innings matches: {second_result.match_count}")
            print(f"  Second innings deliveries: {second_result.delivery_count}")
            
            # Check for completed matches with winners
            winner_query = text("""
                SELECT COUNT(*) as completed_matches
                FROM matches m
                WHERE m.venue = :venue
                AND m.date < :test_date
                AND m.winner IS NOT NULL
            """)
            
            winner_result = session.execute(winner_query, {
                "venue": good_venue,
                "test_date": date(2023, 6, 1)
            }).fetchone()
            
            print(f"  Completed matches with winners: {winner_result.completed_matches}")
        
        # Check leagues/competitions
        print(f"\n🏆 Available competitions:")
        comp_query = text("""
            SELECT competition, COUNT(*) as count
            FROM matches 
            WHERE date < :test_date
            GROUP BY competition
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        
        comps = session.execute(comp_query, {
            "test_date": date(2023, 6, 1)
        }).fetchall()
        
        for comp in comps:
            print(f"  {comp.competition}: {comp.count} matches")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_venue_data()
