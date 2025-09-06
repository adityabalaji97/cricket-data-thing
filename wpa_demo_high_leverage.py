"""
WPA Engine Demo - High Leverage Situations

This script demonstrates the WPA Engine with deliveries from
middle/death overs where WPA impact should be significant.
"""

from database import get_database_connection
from models import Delivery
from wpa_engine import OptimizedWPAEngine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_high_leverage_wpa():
    """Demo WPA calculation for high-leverage deliveries"""
    
    # Initialize engine and database
    engine, session_factory = get_database_connection()
    wpa_engine = OptimizedWPAEngine()
    
    session = session_factory()
    
    try:
        # Get deliveries from middle/death overs (overs 10-19) in second innings
        high_leverage_deliveries = session.query(Delivery).filter(
            Delivery.innings == 2,
            Delivery.over >= 10,  # Middle to death overs
            Delivery.over <= 19,
            Delivery.wpa_batter.is_(None)  # Not yet calculated
        ).limit(5).all()
        
        if not high_leverage_deliveries:
            logger.warning("No high-leverage deliveries found, trying overs 5-15...")
            # Try a broader range
            high_leverage_deliveries = session.query(Delivery).filter(
                Delivery.innings == 2,
                Delivery.over >= 5,  # Broader range
                Delivery.over <= 15,
                Delivery.wpa_batter.is_(None)
            ).limit(5).all()
        
        if not high_leverage_deliveries:
            logger.warning("No suitable deliveries found, using any second innings deliveries...")
            # Fallback to any second innings
            high_leverage_deliveries = session.query(Delivery).filter(
                Delivery.innings == 2,
                Delivery.wpa_batter.is_(None)
            ).order_by(Delivery.over.desc()).limit(5).all()  # Order by descending over to get later deliveries
        
        if not high_leverage_deliveries:
            logger.error("No second innings deliveries found!")
            return
        
        logger.info(f"Demo: Processing {len(high_leverage_deliveries)} high-leverage deliveries...")
        
        for i, delivery in enumerate(high_leverage_deliveries, 1):
            logger.info(f"\n--- High-Leverage Delivery {i}: Match {delivery.match_id}, Over {delivery.over}.{delivery.ball} ---")
            
            # Get match info
            match_info = wpa_engine.get_match_info(session, delivery.match_id)
            if match_info:
                logger.info(f"Match: {match_info['team1']} vs {match_info['team2']} at {match_info['venue']}")
                logger.info(f"Target: {match_info['first_innings_total'] + 1}")
            
            # Calculate match state before delivery
            before_state = wpa_engine.get_match_state_at_delivery(session, delivery)
            if before_state:
                logger.info(f"Before ball: {before_state.current_score}/{before_state.wickets_lost} "
                          f"(need {before_state.runs_needed} in {before_state.balls_remaining} balls)")
                logger.info(f"Required RR: {before_state.runs_needed * 6 / before_state.balls_remaining:.2f} "
                          f"(Wickets remaining: {before_state.wickets_remaining})")
            
            # Get delivery details
            delivery_runs = (delivery.runs_off_bat or 0) + (delivery.extras or 0)
            wicket_taken = "YES" if delivery.wicket_type else "NO"
            logger.info(f"Delivery: {delivery_runs} runs, Wicket: {wicket_taken}")
            
            # Calculate WPA
            wpa_result = wpa_engine.calculate_delivery_wpa(session, delivery)
            if wpa_result:
                wpa_batter, wpa_bowler, metadata = wpa_result
                logger.info(f"🎯 WPA Impact: Batter {wpa_batter:+.3f}, Bowler {wpa_bowler:+.3f}")
                logger.info(f"Data source: {metadata['data_source']}")
                logger.info(f"Win probability: {metadata['before_wp']:.3f} → {metadata['after_wp']:.3f}")
                
                # Analyze the impact
                if abs(wpa_batter) > 0.05:
                    logger.info("💥 HIGH IMPACT delivery!")
                elif abs(wpa_batter) > 0.01:
                    logger.info("⚡ Medium impact delivery")
                elif abs(wpa_batter) > 0.001:
                    logger.info("🔸 Low impact delivery")
                else:
                    logger.info("⚪ Minimal impact delivery")
                
                # Store in database (but don't commit to avoid affecting future tests)
                success = wpa_engine.calculate_and_store_delivery_wpa(session, delivery)
                if success:
                    logger.info("✅ WPA calculated and stored")
                else:
                    logger.error("❌ Failed to store WPA")
            else:
                logger.info("No WPA calculated (insufficient data)")
        
        logger.info("\n🎉 High-leverage demo completed!")
        
        # Show performance statistics
        stats = wpa_engine.get_performance_stats()
        logger.info(f"\n📊 Performance Stats:")
        logger.info(f"   Total calculations: {stats['total_calculations']}")
        logger.info(f"   Precomputed hits: {stats['precomputed_hits']} ({stats['precomputed_hit_rate']}%)")
        logger.info(f"   Performance mode: {stats['performance_mode']}")
        
        # Show some examples of what makes high WPA
        logger.info(f"\n💡 High WPA typically occurs when:")
        logger.info(f"   - Close chases (5-15 runs needed)")
        logger.info(f"   - Few wickets remaining (7-9 down)")
        logger.info(f"   - Final overs (16-20)")
        logger.info(f"   - Boundaries/wickets in pressure situations")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    print("WPA Engine Demo - High Leverage Situations")
    print("=" * 50)
    demo_high_leverage_wpa()
