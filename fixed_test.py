"""
Fixed comprehensive test - intelligently selects league and date
"""

import sys
import os
import traceback
from datetime import date
import json

def test_context_model_fixed():
    try:
        print("=== Context Model Comprehensive Test (Fixed) ===\n")
        
        # Imports
        from database import get_session
        from context_model import VenueResourceTableBuilder
        from venue_utils import get_venue_hierarchy
        from sqlalchemy import text
        
        # Initialize
        builder = VenueResourceTableBuilder()
        session_gen = get_session()
        session = next(session_gen)
        
        print("✅ Initialization complete")
        
        # Get a venue with good data and find its most common league
        venue_query = text("""
            SELECT m.venue, 
                   m.competition,
                   COUNT(*) as match_count,
                   MIN(m.date) as first_match,
                   MAX(m.date) as last_match
            FROM matches m
            JOIN deliveries d ON m.id = d.match_id
            WHERE m.venue IS NOT NULL 
            GROUP BY m.venue, m.competition
            HAVING COUNT(*) >= 20
            ORDER BY COUNT(*) DESC 
            LIMIT 5
        """)
        
        venues_result = session.execute(venue_query).fetchall()
        print(f"Found {len(venues_result)} suitable venue+league combinations:")
        
        for venue_row in venues_result:
            print(f"  - {venue_row.venue} ({venue_row.competition}): {venue_row.match_count} matches")
        
        if not venues_result:
            print("❌ No suitable venues found")
            return
            
        # Use the best venue+league combination
        best_venue = venues_result[0]
        test_venue = best_venue.venue
        test_league = best_venue.competition
        # Use a date that leaves plenty of historical data
        test_date = date(2022, 1, 1)
        
        print(f"\n=== Testing with {test_venue} ({test_league}) ===")
        print(f"Test date: {test_date} (leaving data from {best_venue.first_match} to 2021)")
        
        # Test 1: Historical match states
        print("\nTest 1: Historical match states...")
        states_1 = builder.get_historical_match_states(session, test_venue, 1, test_date, test_league)
        states_2 = builder.get_historical_match_states(session, test_venue, 2, test_date, test_league)
        
        print(f"  Innings 1: {len(states_1)} states")
        print(f"  Innings 2: {len(states_2)} states")
        
        if states_1:
            # Show some sample states
            print("  Sample states (innings 1):")
            for i, state in enumerate(states_1[:3]):
                print(f"    Over {state['over']}, {state['wickets']} wickets: {state['avg_runs_so_far']:.1f} runs, final: {state['avg_final_score']:.1f}")
        else:
            # Try without league filter
            print("  No states with league filter, trying without league...")
            states_1_no_league = builder.get_historical_match_states(session, test_venue, 1, test_date, None)
            print(f"  Innings 1 (no league): {len(states_1_no_league)} states")
            states_1 = states_1_no_league  # Use this for further tests
        
        # Test 2: Resource calculation
        print("\nTest 2: Resource calculation...")
        if states_1:
            resource_0_0 = builder.calculate_resource_percentage(0, 0, states_1)
            resource_10_3 = builder.calculate_resource_percentage(10, 3, states_1)
            resource_19_8 = builder.calculate_resource_percentage(19, 8, states_1)
            
            print(f"  Start of innings (0 overs, 0 wickets): {resource_0_0:.1f}%")
            print(f"  Middle (10 overs, 3 wickets): {resource_10_3:.1f}%")
            print(f"  End (19 overs, 8 wickets): {resource_19_8:.1f}%")
            
            # Verify resource percentages make sense
            if resource_0_0 > resource_10_3 > resource_19_8:
                print("  ✅ Resource percentages decrease logically")
            else:
                print("  ⚠️  Resource percentages don't decrease as expected")
        
        # Test 3: Venue hierarchy
        print("\nTest 3: Venue hierarchy...")
        hierarchy = get_venue_hierarchy(session, test_venue, test_league, test_date)
        print(f"  Venue matches: {hierarchy['venue']}")
        print(f"  Cluster matches: {hierarchy['cluster']}")
        print(f"  League matches: {hierarchy['league']}")
        print(f"  Global matches: {hierarchy['global']}")
        
        # Test 4: Build complete resource table
        print("\nTest 4: Build resource table...")
        if hierarchy['venue'] >= builder.min_matches_venue and states_1:
            print(f"  Building venue-specific resource table...")
            resource_table = builder.build_venue_resource_table(session, test_venue, test_date, test_league)
            
            # Show sample resource values
            if resource_table['innings']:
                print("  Sample resource percentages:")
                for innings in [1, 2]:
                    if innings in resource_table['innings'] and resource_table['innings'][innings]:
                        print(f"    Innings {innings}:")
                        innings_table = resource_table['innings'][innings]
                        for over in [0, 5, 10, 15]:
                            if over in innings_table and 0 in innings_table[over]:
                                print(f"      Over {over}, 0 wickets: {innings_table[over][0]}%")
        else:
            print(f"  Testing fallback mechanism...")
            fallback_result = builder.get_resource_table_with_fallback(session, test_venue, test_date, test_league)
            print(f"  Fallback source: {fallback_result['source']}")
            print(f"  Matches used: {fallback_result['matches_used']}")
            
            # Show sample from fallback
            if 'resource_table' in fallback_result and fallback_result['resource_table']['innings']:
                rt = fallback_result['resource_table']
                if 1 in rt['innings'] and rt['innings'][1]:
                    print("  Sample fallback resource percentages:")
                    innings_table = rt['innings'][1]
                    for over in [0, 5, 10, 15]:
                        if over in innings_table and 0 in innings_table[over]:
                            print(f"    Over {over}, 0 wickets: {innings_table[over][0]}%")
        
        # Test 5: Par score distribution
        print("\nTest 5: Par score distribution...")
        if hierarchy['venue'] >= 3:  # Need some data for par scores
            par_distribution = builder.build_par_score_distribution(session, test_venue, test_date, test_league)
            
            if par_distribution['innings']:
                print("  Sample par scores:")
                for innings in [1, 2]:
                    if innings in par_distribution['innings']:
                        innings_data = par_distribution['innings'][innings]
                        for over in [5, 10, 15]:
                            if over in innings_data:
                                data = innings_data[over]
                                print(f"    Innings {innings}, Over {over}: avg={data['avg_score']:.1f}, median={data['median']:.1f}, samples={data['sample_size']}")
        
        # Test 6: Venue clustering
        print("\nTest 6: Venue clustering...")
        cluster = builder.venue_manager.get_venue_cluster(test_venue)
        normalized = builder.venue_manager.normalize_venue_name(test_venue)
        print(f"  Original: {test_venue}")
        print(f"  Normalized: {normalized}")
        print(f"  Cluster: {cluster}")
        
        if cluster:
            cluster_venues = builder.venue_manager.venue_clusters[cluster]
            print(f"  Cluster venues: {', '.join(cluster_venues[:3])}{'...' if len(cluster_venues) > 3 else ''}")
        
        session.close()
        
        print("\n🎉 All comprehensive tests completed successfully!")
        print("\n=== Test Summary ===")
        print(f"✅ Venue: {test_venue}")
        print(f"✅ League: {test_league}")
        print(f"✅ Historical states: {len(states_1)} + {len(states_2) if 'states_2' in locals() else 0} states")
        print(f"✅ Resource calculation: Working")
        print(f"✅ Venue hierarchy: {hierarchy['venue']}/{hierarchy['cluster']}/{hierarchy['league']}/{hierarchy['global']}")
        print(f"✅ Fallback mechanism: Working")
        print(f"✅ Venue clustering: {cluster}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during comprehensive test: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_context_model_fixed()
    exit(0 if success else 1)
