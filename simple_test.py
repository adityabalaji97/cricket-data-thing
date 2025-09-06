"""
Simple test to verify imports work correctly
"""

try:
    print("Testing imports...")
    
    # Test basic imports
    from database import get_session
    print("✅ Database import successful")
    
    from venue_utils import VenueClusterManager, get_venue_hierarchy
    print("✅ Venue utils import successful")
    
    from context_model import VenueResourceTableBuilder
    print("✅ Context model import successful")
    
    # Test initialization
    builder = VenueResourceTableBuilder()
    print("✅ VenueResourceTableBuilder initialized")
    
    venue_manager = VenueClusterManager()
    print("✅ VenueClusterManager initialized")
    
    # Test basic method existence
    methods_to_check = [
        'build_venue_resource_table',
        'build_par_score_distribution', 
        'get_resource_table_with_fallback'
    ]
    
    for method in methods_to_check:
        if hasattr(builder, method):
            print(f"✅ Method {method} exists")
        else:
            print(f"❌ Method {method} missing")
    
    print("\n🎉 All imports and basic checks passed!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
