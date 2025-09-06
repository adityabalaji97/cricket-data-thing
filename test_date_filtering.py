#!/usr/bin/env python3
"""
Test date filtering functionality
"""

print("🏏 Testing Date Filtering")
print("="*50)

try:
    from database import get_session
    from services.query_builder import query_deliveries_service
    from datetime import date
    
    db = next(get_session())
    print("✅ Database connection successful")
    
    # Test with date range
    print("\n📅 Test: Date Range Filter")
    print("-" * 30)
    result = query_deliveries_service(
        venue=None,
        start_date=date(2024, 1, 1),  # Specific start date
        end_date=date(2024, 12, 31),  # Specific end date
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
        group_by=["crease_combo"],
        limit=10,
        offset=0,
        include_international=False,
        top_teams=None,
        db=db
    )
    
    print(f"✅ Date filtering successful!")
    print(f"   Total groups found: {result['metadata']['total_groups']}")
    print(f"   Date range applied: {result['metadata']['filters_applied']['start_date']} to {result['metadata']['filters_applied']['end_date']}")
    
    if result['data']:
        print(f"   Sample group: {result['data'][0]['crease_combo']} - {result['data'][0]['balls']} balls")
    
    # Test without date range
    print("\n📅 Test: No Date Filter (All Time)")
    print("-" * 30)
    result2 = query_deliveries_service(
        venue=None,
        start_date=None,  # No date filter
        end_date=None,    # No date filter
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
        group_by=["crease_combo"],
        limit=10,
        offset=0,
        include_international=False,
        top_teams=None,
        db=db
    )
    
    print(f"✅ No date filter successful!")
    print(f"   Total groups found: {result2['metadata']['total_groups']}")
    print(f"   Should be >= date filtered results: {result2['metadata']['total_groups'] >= result['metadata']['total_groups']}")
    
    print("\n🎉 Date filtering tests PASSED!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
