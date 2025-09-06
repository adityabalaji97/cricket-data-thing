"""
Test WPA with different matches to see if the 100% win probability issue is widespread
"""
from database import get_database_connection
from models import Match, Delivery
from wpa_engine import OptimizedWPAEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_different_matches():
    """Test WPA calculations with different matches"""
    
    engine, session_factory = get_database_connection()
    session = session_factory()
    wpa_engine = OptimizedWPAEngine()
    
    try:
        # Get several different matches from different years/venues
        different_matches = session.query(Match).filter(
            Match.match_type == "league",
            Match.date > "2015-01-01",  # More recent matches
            Match.venue != "Maharashtra Cricket Association Stadium"  # Different venue
        ).limit(5).all()
        
        logger.info(f"Found {len(different_matches)} different matches to test")
        
        for i, match in enumerate(different_matches, 1):
            logger.info(f"\n=== Match {i}: {match.team1} vs {match.team2} ===")
            logger.info(f"Venue: {match.venue}")
            logger.info(f"Date: {match.date}")
            logger.info(f"Competition: {match.competition}")
            
            # Get a few second innings deliveries from this match
            deliveries = session.query(Delivery).filter(
                Delivery.match_id == match.id,
                Delivery.innings == 2,
                Delivery.over >= 5,  # Middle overs
                Delivery.over <= 15
            ).limit(3).all()
            
            if not deliveries:
                logger.info("No suitable deliveries found for this match")
                continue
            
            for j, delivery in enumerate(deliveries, 1):
                logger.info(f"\n--- Delivery {j}: Over {delivery.over}.{delivery.ball} ---")
                
                # Get match state
                before_state = wpa_engine.get_match_state_at_delivery(session, delivery)
                if not before_state:
                    continue
                
                logger.info(f"Situation: {before_state.current_score}/{before_state.wickets_lost} "
                          f"chasing {before_state.target}")
                logger.info(f"Need: {before_state.runs_needed} runs in {before_state.balls_remaining} balls "
                          f"(RR: {before_state.runs_needed * 6 / before_state.balls_remaining:.1f})")
                
                # Calculate WPA
                wpa_result = wpa_engine.calculate_delivery_wpa(session, delivery)
                if wpa_result:
                    wpa_batter, wpa_bowler, metadata = wpa_result
                    
                    logger.info(f"WPA: Batter {wpa_batter:+.3f}, Bowler {wpa_bowler:+.3f}")
                    logger.info(f"Win probability: {metadata['before_wp']:.3f} → {metadata['after_wp']:.3f}")
                    logger.info(f"Data source: {metadata['data_source']}")
                    
                    # Check if this is also showing unrealistic probabilities
                    required_rr = before_state.runs_needed * 6 / before_state.balls_remaining
                    if metadata['before_wp'] >= 0.99 and required_rr > 10:
                        logger.warning(f"⚠️  Potentially unrealistic: {metadata['before_wp']:.3f} WP for RR {required_rr:.1f}")
                    elif metadata['before_wp'] < 0.99:
                        logger.info(f"✅ Reasonable WP for the situation")
                else:
                    logger.info("No WPA calculated")
        
        # Summary
        logger.info(f"\n📊 Testing Summary:")
        logger.info(f"This will help us understand if the 100% win probability issue is:")
        logger.info(f"- Specific to the Maharashtra Cricket Association Stadium")
        logger.info(f"- Specific to older matches (2012)")
        logger.info(f"- A broader issue with the precomputed data")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_different_matches()
