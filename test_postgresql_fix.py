#!/usr/bin/env python3
"""
Quick test for PostgreSQL fix
"""

print("🏏 Testing PostgreSQL ROUND Function Fix")
print("="*50)

try:
    # Test imports
    from database import get_session
    from services.query_builder import query_deliveries_service
    print("✅ Imports successful")
    
    # Test database connection
    db = next(get_session())
    print("✅ Database connection successful")
    
    # Test grouped query (this was failing before)
    result = query_deliveries_service(
        venue=None, start_date=None, end_date=None, leagues=["IPL"], teams=[], players=[],
        crease_combo=None, ball_direction=None, bowler_type=None, striker_batter_type=None,
        non_striker_batter_type=None, innings=None, over_min=None, over_max=5, wicket_type=None,
        group_by=["crease_combo"], limit=10, offset=0, include_international=False, top_teams=None, db=db
    )
    print(f"✅ Grouped query successful: {result['metadata']['returned_groups']} groups returned")
    print(f"   Total groups: {result['metadata']['total_groups']}")
    print(f"   Grouped by: {result['metadata']['grouped_by']}")
    
    if result['data']:
        sample = result['data'][0]
        print(f"\n   📊 Sample group: {sample['crease_combo']}")
        print(f"      Balls: {sample['balls']:,}")
        print(f"      Runs: {sample['runs']:,}")
        print(f"      Strike Rate: {sample['strike_rate']:.2f}")
        print(f"      Dot %: {sample['dot_percentage']:.2f}%")
        print(f"      Boundary %: {sample['boundary_percentage']:.2f}%")
        if sample['average']:
            print(f"      Average: {sample['average']:.2f}")
        else:
            print(f"      Average: N/A (no wickets)")
    
    print("\n🎉 PostgreSQL Fix SUCCESSFUL!")
    print("✅ ROUND function issue resolved")
    print("✅ Grouped queries now working")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
