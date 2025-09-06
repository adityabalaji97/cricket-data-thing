"""
WPA Engine Demo - Simple Usage Example

This script demonstrates basic usage of the WPA Engine
for calculating per-delivery WPA values.
"""

from database import get_database_connection
from models import Delivery
from wpa_engine import OptimizedWPAEngine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_wpa_calculation():
    """Simple demo of WPA calculation for a few deliveries"""
    
    # Initialize engine and database
    engine, session_factory = get_database_connection()
    wpa_engine = OptimizedWPAEngine()
    
    session = session_factory()
    
    try:
        # Get a few second innings deliveries to demonstrate
        sample_deliveries = session.query(Delivery).filter(
            Delivery.innings == 2,
            Delivery.wpa_batter.is_(None)  # Not yet calculated
        ).limit(3).all()
        
        if not sample_deliveries:
            logger.warning("No sample deliveries found for demo")
            return
        
        logger.info(f"Demo: Processing {len(sample_deliveries)} deliveries...")
        
        for i, delivery in enumerate(sample_deliveries, 1):
            logger.info(f"\n--- Delivery {i}: {delivery.match_id}, Over {delivery.over}.{delivery.ball} ---")
            
            # Get match info
            match_info = wpa_engine.get_match_info(session, delivery.match_id)
            if match_info:
                logger.info(f"Match: {match_info['team1']} vs {match_info['team2']} at {match_info['venue']}")
                logger.info(f"Target: {match_info['first_innings_total'] + 1}")
            
            # Calculate match state
            before_state = wpa_engine.get_match_state_at_delivery(session, delivery)
            if before_state:
                logger.info(f"Before ball: {before_state.current_score}/{before_state.wickets_lost} (need {before_state.runs_needed} in {before_state.balls_remaining} balls)")
            
            # Calculate WPA
            wpa_result = wpa_engine.calculate_delivery_wpa(session, delivery)
            if wpa_result:
                wpa_batter, wpa_bowler, metadata = wpa_result
                logger.info(f"WPA Impact: Batter {wpa_batter:+.3f}, Bowler {wpa_bowler:+.3f}")
                logger.info(f"Data source: {metadata['data_source']}")
                
                # Store in database
                success = wpa_engine.calculate_and_store_delivery_wpa(session, delivery)
                if success:
                    logger.info("✅ WPA stored in database")
                else:
                    logger.error("❌ Failed to store WPA")
            else:
                logger.info("No WPA calculated (first innings or insufficient data)")
        
        logger.info("\n🎉 Demo completed!")
        
        # Show performance statistics
        stats = wpa_engine.get_performance_stats()
        logger.info(f"\n📊 Performance Stats:")
        logger.info(f"   Total calculations: {stats['total_calculations']}")
        logger.info(f"   Precomputed hits: {stats['precomputed_hits']} ({stats['precomputed_hit_rate']}%)")
        logger.info(f"   Performance mode: {stats['performance_mode']}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    print("WPA Engine Demo")
    print("=" * 40)
    demo_wpa_calculation()
