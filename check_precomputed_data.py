"""
Quick check for precomputed data availability
"""
from database import get_database_connection
from precomputed_models import WPAOutcome, VenueResource
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_precomputed_data():
    """Check if we have precomputed data available"""
    
    engine, session_factory = get_database_connection()
    session = session_factory()
    
    try:
        # Check WPA outcomes
        wpa_count = session.query(WPAOutcome).count()
        logger.info(f"WPA Outcomes available: {wpa_count}")
        
        if wpa_count > 0:
            sample_wpa = session.query(WPAOutcome).first()
            logger.info(f"Sample WPA: venue={sample_wpa.venue}, target_bucket={sample_wpa.target_bucket}, win_prob={sample_wpa.win_probability}")
        
        # Check venue resources
        resource_count = session.query(VenueResource).count()
        logger.info(f"Venue Resources available: {resource_count}")
        
        if resource_count > 0:
            sample_resource = session.query(VenueResource).first()
            logger.info(f"Sample Resource: venue={sample_resource.venue}, resource={sample_resource.resource_percentage}%")
        
        # Summary
        if wpa_count == 0 and resource_count == 0:
            logger.warning("❌ No precomputed data found! WPA engine will use heuristic fallback.")
            logger.info("💡 Run batch_processor.py to generate precomputed data for optimal performance.")
        elif wpa_count > 0:
            logger.info("✅ Precomputed WPA data available! Engine should be fast.")
        else:
            logger.info("⚠️ Some precomputed data available, but may need more for full coverage.")
            
    except Exception as e:
        logger.error(f"Error checking precomputed data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_precomputed_data()
