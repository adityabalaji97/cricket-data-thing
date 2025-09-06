"""
Test script for WPA Curve Trainer

This script tests the WPA Curve Trainer implementation following
the same patterns as the existing context model tests.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_session
from wpa_curve_trainer import WPACurveTrainer
from wpa_fallback import WPAEngineWithFallback
from datetime import date
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_wpa_curve_trainer():
    """
    Test the WPA Curve Trainer with real database data.
    """
    print("🏏 Testing WPA Curve Trainer Implementation")
    print("=" * 50)
    
    # Get database session
    session_gen = get_session()
    session = next(session_gen)
    if not session:
        print("❌ Failed to connect to database")
        return
    
    try:
        # Initialize WPA engine
        wpa_engine = WPAEngineWithFallback()
        print("✅ WPA Engine initialized successfully")
        
        # Test with a well-known venue
        test_venue = "Wankhede Stadium, Mumbai"  # Use exact name from database
        test_date = date(2023, 6, 1)  # Use a date that has historical data
        test_league = "IPL"
        
        print(f"\n🏟️ Testing venue: {test_venue}")
        print(f"📅 Before date: {test_date}")
        print(f"🏆 League: {test_league}")
        
        # Test basic chase outcomes retrieval
        print("\n📊 Testing chase outcomes retrieval...")
        outcomes = wpa_engine.trainer.get_second_innings_outcomes(
            session, test_venue, test_date, test_league
        )
        
        print(f"✅ Found {len(outcomes)} chase outcomes")
        if outcomes:
            sample_outcome = outcomes[0]
            print(f"📝 Sample outcome: Over {sample_outcome['over']}, "
                  f"Score {sample_outcome['runs_so_far']}/{sample_outcome['wickets_lost']}, "
                  f"Target {sample_outcome['target']}, Won: {sample_outcome['won_chase']}")
        
        # Test win probability calculation
        print("\n🎯 Testing win probability calculation...")
        if outcomes:
            test_prob = wpa_engine.trainer.calculate_win_probability(
                target_score=160, current_score=80, over=10, wickets=3, 
                outcomes_data=outcomes
            )
            print(f"✅ Win probability for 80/3 in 10 overs chasing 160: {test_prob:.3f}")
        
        # Test with fallback hierarchy
        print(f"\n🔄 Testing WPA lookup table with fallback for {test_venue}...")
        wpa_result = wpa_engine.get_wpa_lookup_table_with_fallback(
            session, test_venue, test_date, test_league
        )
        
        print(f"✅ WPA table source: {wpa_result['source']}")
        print(f"📈 Matches used: {wpa_result['matches_used']}")
        
        wpa_table = wpa_result['wpa_table']
        print(f"📊 Sample size: {wpa_table.get('sample_size', 0)}")
        
        # Test lookup table structure
        if wpa_table.get('lookup_table'):
            lookup = wpa_table['lookup_table']
            target_keys = list(lookup.keys())
            print(f"🎯 Target buckets available: {target_keys[:3]}...")
            
            if target_keys:
                first_target = target_keys[0]
                over_keys = list(lookup[first_target].keys())
                print(f"⏰ Over buckets for target {first_target}: {over_keys[:5]}...")
        
        # Test different venues with different fallback levels
        test_venues = [
            ("Eden Gardens", "IPL"),  # Should have venue-specific data
            ("Some Random Stadium", "IPL"),  # Should fallback
        ]
        
        print(f"\n🏟️ Testing fallback hierarchy...")
        for venue, league in test_venues:
            print(f"\nTesting {venue}...")
            try:
                result = wpa_engine.get_wpa_lookup_table_with_fallback(
                    session, venue, test_date, league
                )
                print(f"  Source: {result['source']}, Matches: {result['matches_used']}")
            except Exception as e:
                print(f"  ⚠️ Error: {str(e)}")
        
        print(f"\n✅ WPA Curve Trainer tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()


if __name__ == "__main__":
    test_wpa_curve_trainer()
