"""
Quick verification script for Context Model
"""

def quick_verify():
    try:
        print("🏏 Quick Context Model Verification")
        print("=" * 40)
        
        # Test imports
        from context_model import VenueResourceTableBuilder
        from venue_utils import VenueClusterManager
        from database import get_session
        
        print("✅ All imports successful")
        
        # Test initialization
        builder = VenueResourceTableBuilder()
        venue_manager = VenueClusterManager()
        
        print("✅ Objects initialized")
        print(f"   - Max overs: {builder.max_overs}")
        print(f"   - Min venue matches: {builder.min_matches_venue}")
        print(f"   - Available clusters: {len(venue_manager.venue_clusters)}")
        
        # Test database connection
        session_gen = get_session()
        session = next(session_gen)
        
        from sqlalchemy import text
        
        # Quick data check
        match_count = session.execute(text("SELECT COUNT(*) FROM matches")).scalar()
        delivery_count = session.execute(text("SELECT COUNT(*) FROM deliveries")).scalar()
        
        print("✅ Database connection successful")
        print(f"   - Matches: {match_count:,}")
        print(f"   - Deliveries: {delivery_count:,}")
        
        # Test venue clustering
        test_venues = ["Wankhede Stadium", "Eden Gardens", "Chinnaswamy Stadium"]
        print("✅ Venue clustering test:")
        
        for venue in test_venues:
            cluster = venue_manager.get_venue_cluster(venue)
            normalized = venue_manager.normalize_venue_name(venue)
            print(f"   - {venue} -> {cluster} (normalized: {normalized})")
        
        session.close()
        
        print("\n🎉 Context Model verification complete!")
        print("✅ Ready for WPA Engine implementation")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_verify()
    exit(0 if success else 1)
