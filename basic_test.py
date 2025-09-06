import sys
import os
import traceback
from datetime import date

try:
    print("Testing Context Model imports...")
    
    # Test database import
    from database import get_session
    print("✅ Database import successful")
    
    # Test venue utils import
    from venue_utils import VenueClusterManager
    print("✅ Venue utils import successful")
    
    # Test context model import
    from context_model import VenueResourceTableBuilder
    print("✅ Context model import successful")
    
    # Test initialization
    builder = VenueResourceTableBuilder()
    print("✅ VenueResourceTableBuilder initialized")
    print(f"   - Max overs: {builder.max_overs}")
    print(f"   - Min matches venue: {builder.min_matches_venue}")
    
    # Test database connection
    session_gen = get_session()
    session = next(session_gen)
    
    # Simple query test
    from sqlalchemy import text
    result = session.execute(text("SELECT COUNT(*) as count FROM matches")).fetchone()
    print(f"✅ Database connection works - {result.count} matches found")
    
    # Test with actual data
    if result.count > 0:
        print("\n=== Testing with Real Data ===")
        
        # Get a sample venue
        venue_result = session.execute(text("""
            SELECT venue, COUNT(*) as match_count 
            FROM matches 
            WHERE venue IS NOT NULL 
            GROUP BY venue 
            ORDER BY COUNT(*) DESC 
            LIMIT 1
        """)).fetchone()
        
        if venue_result:
            venue = venue_result.venue
            match_count = venue_result.match_count
            print(f"Testing with venue: {venue} ({match_count} matches)")
            
            # Test historical match states
            test_date = date(2023, 6, 1)
            states = builder.get_historical_match_states(session, venue, 1, test_date)
            print(f"✅ Found {len(states)} historical match states for innings 1")
            
            if states:
                # Show sample
                sample = states[0]
                print(f"   Sample state: Over {sample['over']}, {sample['wickets']} wickets, {sample['avg_runs_so_far']:.1f} runs")
                
                # Test resource calculation
                resource = builder.calculate_resource_percentage(5, 2, states)
                print(f"✅ Resource calculation works: {resource:.1f}% at over 5, 2 wickets")
            
            # Test venue manager
            cluster = builder.venue_manager.get_venue_cluster(venue)
            print(f"✅ Venue clustering: {venue} -> {cluster}")
    
    session.close()
    print("\n🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()
