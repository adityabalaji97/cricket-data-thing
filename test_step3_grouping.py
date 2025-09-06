#!/usr/bin/env python3
"""
Test script for Step 3: Query Builder Grouping Functionality
"""

import sys
sys.path.append('.')

from database import get_session
from services.query_builder import query_deliveries_service
from datetime import date
import json

def test_step3_grouping():
    """Test Step 3: Grouping functionality"""
    
    print("🏏 Testing Step 3: Query Builder Grouping Functionality")
    print("="*60)
    
    db = next(get_session())
    
    # Test 1: Ungrouped Query (Individual Deliveries)
    print("\n📋 Test 1: Ungrouped Query (Individual Deliveries)")
    print("-"*50)
    
    try:
        result = query_deliveries_service(
            venue=None,
            start_date=None,
            end_date=None,
            leagues=["IPL"],
            teams=[],
            players=[],
            crease_combo="lhb_rhb",  # Mixed handed partnerships
            ball_direction=None,
            bowler_type=None,
            striker_batter_type=None,
            non_striker_batter_type=None,
            innings=None,
            over_min=None,
            over_max=None,
            wicket_type=None,
            group_by=[],  # No grouping - should return individual deliveries
            limit=10,
            offset=0,
            include_international=False,
            top_teams=None,
            db=db
        )
        
        print(f"✅ Total matching deliveries: {result['metadata']['total_matching_rows']:,}")
        print(f"✅ Returned deliveries: {result['metadata']['returned_rows']}")
        print(f"✅ Data type: {type(result['data'])}")
        if result['data']:
            print(f"✅ First delivery structure: {list(result['data'][0].keys())}")
            print(f"✅ Sample delivery: {json.dumps(result['data'][0], indent=2)}")
        
        print(f"✅ Note: {result['metadata']['note']}")
        
    except Exception as e:
        print(f"❌ Ungrouped query failed: {e}")
        return False
    
    # Test 2: Single Grouping (Crease Combo Analysis)
    print("\n📊 Test 2: Single Grouping - Crease Combo Analysis")
    print("-"*50)
    
    try:
        result = query_deliveries_service(
            venue=None,
            start_date=None,
            end_date=None,
            leagues=["IPL"],
            teams=[],
            players=[],
            crease_combo=None,  # All crease combinations
            ball_direction=None,
            bowler_type=None,
            striker_batter_type=None,
            non_striker_batter_type=None,
            innings=None,
            over_min=None,
            over_max=5,  # Powerplay only
            wicket_type=None,
            group_by=["crease_combo"],  # Group by crease combination
            limit=10,
            offset=0,
            include_international=False,
            top_teams=None,
            db=db
        )
        
        print(f"✅ Total groups: {result['metadata']['total_groups']}")
        print(f"✅ Returned groups: {result['metadata']['returned_groups']}")
        print(f"✅ Grouped by: {result['metadata']['grouped_by']}")
        print(f"✅ Data type: {type(result['data'])}")
        if result['data']:
            print(f"✅ First group structure: {list(result['data'][0].keys())}")
            print(f"✅ Sample group stats: {json.dumps(result['data'][0], indent=2)}")
        
        print(f"✅ Note: {result['metadata']['note']}")
        
    except Exception as e:
        print(f"❌ Single grouping failed: {e}")
        return False
    
    # Test 3: Multiple Grouping (Venue + Ball Direction)
    print("\n📊 Test 3: Multiple Grouping - Venue + Ball Direction")
    print("-"*50)
    
    try:
        result = query_deliveries_service(
            venue=None,
            start_date=None,
            end_date=None,
            leagues=["IPL"],
            teams=[],
            players=[],
            crease_combo="lhb_rhb",  # Mixed handed partnerships only
            ball_direction=None,
            bowler_type="LO",  # Left-arm orthodox spinners
            striker_batter_type=None,
            non_striker_batter_type=None,
            innings=None,
            over_min=6,  # Middle overs
            over_max=15,
            wicket_type=None,
            group_by=["venue", "ball_direction"],  # Group by venue and ball direction
            limit=20,
            offset=0,
            include_international=False,
            top_teams=None,
            db=db
        )
        
        print(f"✅ Total groups: {result['metadata']['total_groups']}")
        print(f"✅ Returned groups: {result['metadata']['returned_groups']}")
        print(f"✅ Grouped by: {result['metadata']['grouped_by']}")
        print(f"✅ Data type: {type(result['data'])}")
        if result['data']:
            print(f"✅ First group structure: {list(result['data'][0].keys())}")
            
            # Show top 3 results
            for i, group in enumerate(result['data'][:3]):
                print(f"\n   📍 Group {i+1}: {group['venue']} - {group['ball_direction']}")
                print(f"      Balls: {group['balls']:,}, Runs: {group['runs']:,}, Strike Rate: {group['strike_rate']:.1f}")
                print(f"      Dot %: {group['dot_percentage']:.1f}%, Boundary %: {group['boundary_percentage']:.1f}%")
        
        print(f"\n✅ Note: {result['metadata']['note']}")
        
    except Exception as e:
        print(f"❌ Multiple grouping failed: {e}")
        return False
    
    # Test 4: Phase Grouping (Calculated Column)
    print("\n📊 Test 4: Phase Grouping - Powerplay vs Middle vs Death")
    print("-"*50)
    
    try:
        result = query_deliveries_service(
            venue=None,
            start_date=None,
            end_date=None,
            leagues=["IPL"],
            teams=[],
            players=[],
            crease_combo="lhb_rhb",  # Mixed handed partnerships
            ball_direction="intoBatter",  # Into the batter
            bowler_type=None,
            striker_batter_type=None,
            non_striker_batter_type=None,
            innings=None,
            over_min=None,
            over_max=None,
            wicket_type=None,
            group_by=["phase"],  # Group by calculated phase column
            limit=10,
            offset=0,
            include_international=False,
            top_teams=None,
            db=db
        )
        
        print(f"✅ Total groups: {result['metadata']['total_groups']}")
        print(f"✅ Returned groups: {result['metadata']['returned_groups']}")
        print(f"✅ Grouped by: {result['metadata']['grouped_by']}")
        
        if result['data']:
            print("\n   📈 Phase Analysis for LHB-RHB partnerships vs balls into batter:")
            for group in result['data']:
                avg_str = f"{group['average']:.1f}" if group['average'] else 'N/A'
                print(f"      {group['phase'].upper()}: {group['balls']:,} balls, {group['runs']:,} runs, SR: {group['strike_rate']:.1f}")
                print(f"                Avg: {avg_str}, Dot%: {group['dot_percentage']:.1f}%, Boundary%: {group['boundary_percentage']:.1f}%")
        
        print(f"\n✅ Note: {result['metadata']['note']}")
        
    except Exception as e:
        print(f"❌ Phase grouping failed: {e}")
        return False
    
    # Test 5: Error Handling - Invalid Group By
    print("\n🚨 Test 5: Error Handling - Invalid Group By Column")
    print("-"*50)
    
    try:
        result = query_deliveries_service(
            venue=None,
            start_date=None,
            end_date=None,
            leagues=["IPL"],
            teams=[],
            players=[],
            crease_combo=None,
            ball_direction=None,
            bowler_type=None,
            striker_batter_type=None,
            non_striker_batter_type=None,
            innings=None,
            over_min=None,
            over_max=None,
            wicket_type=None,
            group_by=["invalid_column"],  # Invalid column name
            limit=10,
            offset=0,
            include_international=False,
            top_teams=None,
            db=db
        )
        
        print(f"❌ Should have failed but didn't!")
        return False
        
    except Exception as e:
        print(f"✅ Correctly caught error: {str(e)}")
    
    print("\n🎉 Step 3: Grouping functionality tests PASSED!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_step3_grouping()
    sys.exit(0 if success else 1)
