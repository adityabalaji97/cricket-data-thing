"""
Test script for Context Model - Testing with real database data

This script tests the VenueResourceTableBuilder with actual data from your database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from database import get_session
from context_model import VenueResourceTableBuilder
from venue_utils import VenueClusterManager, get_venue_hierarchy
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_venue_context_model():
    """Test the venue context model with real data"""
    
    # Get database session
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # Initialize the resource table builder
        builder = VenueResourceTableBuilder()
        venue_manager = VenueClusterManager()
        
        logger.info("Testing Venue Context Model with real data...")
        
        # Test 1: Get some popular venues from database
        logger.info("=== Test 1: Getting available venues ===")
        
        from sqlalchemy import text
        venue_query = text("""
            SELECT venue, COUNT(*) as match_count
            FROM matches 
            WHERE venue IS NOT NULL 
            GROUP BY venue 
            ORDER BY COUNT(*) DESC 
            LIMIT 10
        """)
        
        venues_result = session.execute(venue_query).fetchall()
        logger.info("Top venues by match count:")
        
        test_venues = []
        for row in venues_result:
            logger.info(f"  {row.venue}: {row.match_count} matches")
            test_venues.append(row.venue)
        
        if not test_venues:
            logger.error("No venues found in database!")
            return
            
        # Test 2: Test venue hierarchy
        logger.info("\n=== Test 2: Testing venue hierarchy ===")
        test_venue = test_venues[0]  # Use most popular venue
        test_date = date(2023, 1, 1)  # Use a recent date
        
        hierarchy = get_venue_hierarchy(session, test_venue, "IPL", test_date)
        logger.info(f"Hierarchy for {test_venue}:")
        for level, count in hierarchy.items():
            logger.info(f"  {level}: {count} matches")
        
        # Test 3: Test venue clustering
        logger.info("\n=== Test 3: Testing venue clustering ===")
        for venue in test_venues[:3]:
            cluster = venue_manager.get_venue_cluster(venue)
            normalized = venue_manager.normalize_venue_name(venue)
            logger.info(f"  {venue} -> cluster: {cluster}, normalized: {normalized}")
        
        # Test 4: Build resource table for a venue with sufficient data
        logger.info("\n=== Test 4: Building resource table ===")
        
        # Find a venue with enough matches
        suitable_venue = None
        for venue in test_venues:
            match_count = venue_manager.get_venue_match_count(session, venue, test_date)
            if match_count >= builder.min_matches_venue:
                suitable_venue = venue
                logger.info(f"Using {venue} with {match_count} matches")
                break
        
        if suitable_venue:
            # Build resource table
            logger.info(f"Building resource table for {suitable_venue}...")
            resource_table = builder.build_venue_resource_table(
                session, suitable_venue, test_date, "IPL"
            )
            
            # Display sample of resource table
            logger.info("Sample resource percentages:")
            for innings in [1, 2]:
                if innings in resource_table["innings"]:
                    logger.info(f"  Innings {innings}:")
                    innings_table = resource_table["innings"][innings]
                    for over in [0, 5, 10, 15, 19]:  # Sample overs
                        if over in innings_table:
                            for wickets in [0, 2, 5, 8]:  # Sample wickets
                                if wickets in innings_table[over]:
                                    resource = innings_table[over][wickets]
                                    logger.info(f"    Over {over}, {wickets} wickets: {resource}%")
        else:
            logger.warning("No venue found with sufficient matches for venue-specific analysis")
        
        # Test 5: Test fallback mechanism
        logger.info("\n=== Test 5: Testing fallback mechanism ===")
        
        # Test with a venue that might need fallback
        test_venue_fallback = test_venues[-1] if len(test_venues) > 1 else test_venues[0]
        
        fallback_result = builder.get_resource_table_with_fallback(
            session, test_venue_fallback, test_date, "IPL"
        )
        
        logger.info(f"Fallback result for {test_venue_fallback}:")
        logger.info(f"  Source: {fallback_result['source']}")
        logger.info(f"  Matches used: {fallback_result['matches_used']}")
        
        if fallback_result['source'] == 'cluster':
            logger.info(f"  Cluster: {fallback_result.get('cluster', 'N/A')}")
        elif fallback_result['source'] == 'league':
            logger.info(f"  League: {fallback_result.get('league', 'N/A')}")
        
        # Test 6: Build par score distribution
        logger.info("\n=== Test 6: Building par score distribution ===")
        
        if suitable_venue:
            par_distribution = builder.build_par_score_distribution(
                session, suitable_venue, test_date, "IPL"
            )
            
            logger.info("Sample par scores:")
            for innings in [1, 2]:
                if innings in par_distribution["innings"]:
                    logger.info(f"  Innings {innings}:")
                    innings_data = par_distribution["innings"][innings]
                    for over in [5, 10, 15, 19]:  # Sample overs
                        if over in innings_data:
                            data = innings_data[over]
                            logger.info(f"    Over {over}: avg={data['avg_score']:.1f}, "
                                      f"median={data['median']:.1f}, "
                                      f"samples={data['sample_size']}")
        
        logger.info("\n=== Context Model Test Completed Successfully! ===")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise
    finally:
        session.close()

def test_specific_venue_detailed():
    """Test with a specific venue in detail"""
    
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # Let's test with a well-known venue
        venue = "M Chinnaswamy Stadium"  # RCB's home ground
        test_date = date(2023, 6, 1)
        league = "IPL"
        
        builder = VenueResourceTableBuilder()
        
        logger.info(f"\n=== Detailed Test for {venue} ===")
        
        # Check data availability
        match_count = builder.venue_manager.get_venue_match_count(session, venue, test_date)
        logger.info(f"Matches available: {match_count}")
        
        if match_count == 0:
            logger.warning(f"No matches found for {venue}, trying different venue names...")
            
            # Try some alternative venue names
            alt_venues = [
                "Chinnaswamy Stadium",
                "Wankhede Stadium", 
                "Eden Gardens",
                "Feroz Shah Kotla"
            ]
            
            for alt_venue in alt_venues:
                alt_count = builder.venue_manager.get_venue_match_count(session, alt_venue, test_date)
                logger.info(f"  {alt_venue}: {alt_count} matches")
                if alt_count > 0:
                    venue = alt_venue
                    match_count = alt_count
                    break
        
        if match_count > 0:
            logger.info(f"Testing with {venue} ({match_count} matches)")
            
            # Test historical match states
            logger.info("Getting historical match states...")
            for innings in [1, 2]:
                states = builder.get_historical_match_states(session, venue, innings, test_date, league)
                logger.info(f"  Innings {innings}: {len(states)} states found")
                
                if states:
                    # Show sample states
                    sample_states = states[:10]
                    for state in sample_states:
                        logger.info(f"    Over {state['over']}, {state['wickets']} wickets: "
                                  f"{state['avg_runs_so_far']:.1f} runs, "
                                  f"final: {state['avg_final_score']:.1f}")
        
        logger.info("Detailed test completed!")
        
    except Exception as e:
        logger.error(f"Error in detailed test: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Starting Context Model Tests...")
    
    try:
        # Run basic tests
        test_venue_context_model()
        
        # Run detailed test
        test_specific_venue_detailed()
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
