"""
Debug why win probabilities are always 1.000
"""
from database import get_database_connection
from precomputed_service import PrecomputedDataService
from precomputed_models import WPAOutcome
from models import Match
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_win_probability_issue():
    """Debug why win probabilities are always 1.000"""
    
    engine, session_factory = get_database_connection()
    session = session_factory()
    service = PrecomputedDataService()
    
    try:
        # Test the scenario that's showing 1.000
        venue = "Maharashtra Cricket Association Stadium"
        target = 156
        current_score = 72
        over = 10
        wickets = 2
        
        logger.info(f"Debugging scenario: {current_score}/{wickets} chasing {target} in over {over}")
        logger.info(f"Need {target - current_score} runs in {(20-over)*6} balls")
        
        # Get target and over buckets
        target_bucket = service._get_target_bucket(target)
        over_bucket = service._get_over_bucket(over)
        
        logger.info(f"Looking for: target_bucket={target_bucket}, over_bucket={over_bucket}, wickets={wickets}")
        
        # Check what WPA outcomes exist for this venue/scenario
        outcomes = session.query(WPAOutcome).filter(
            WPAOutcome.venue == venue,
            WPAOutcome.target_bucket == target_bucket,
            WPAOutcome.over_bucket == over_bucket,
            WPAOutcome.wickets_lost == wickets
        ).all()
        
        logger.info(f"Found {len(outcomes)} WPA outcomes for this scenario")
        
        for outcome in outcomes:
            logger.info(f"  Score range: {outcome.runs_range_min}-{outcome.runs_range_max}, "
                       f"Win prob: {outcome.win_probability}, Sample size: {outcome.sample_size}")
        
        # Check if our score (72) falls in any range
        matching_outcomes = [o for o in outcomes if o.runs_range_min <= current_score <= o.runs_range_max]
        logger.info(f"Matching outcomes for score {current_score}: {len(matching_outcomes)}")
        
        for outcome in matching_outcomes:
            logger.info(f"  MATCH: Score range {outcome.runs_range_min}-{outcome.runs_range_max}, "
                       f"Win prob: {outcome.win_probability}")
        
        # Test a few different scenarios to see the range
        test_scenarios = [
            (156, 20, 19, 8),  # Very close: 20/8 chasing 156 in final over  
            (156, 100, 15, 5), # Moderate: 100/5 chasing 156 in over 15
            (156, 50, 10, 2),  # Difficult: 50/2 chasing 156 in over 10
            (156, 10, 5, 0),   # Very difficult: 10/0 chasing 156 in over 5
        ]
        
        logger.info("\nTesting various scenarios:")
        for target, score, over, wickets in test_scenarios:
            needed = target - score
            balls = (20 - over) * 6
            rr = needed * 6 / balls if balls > 0 else float('inf')
            
            win_prob, source = service.get_win_probability(
                session=session,
                venue=venue,
                target=target,
                over=over,
                wickets=wickets,
                runs=score,
                match_date=None,  # Remove chronological constraint
                league="IPL"
            )
            
            logger.info(f"  {score}/{wickets} chasing {target} in over {over}: "
                       f"WP={win_prob:.3f}, RR={rr:.1f}, Source={source}")
        
        # Check the precomputed data quality
        logger.info("\nChecking data quality...")
        
        # Look at win probability distribution
        all_outcomes = session.query(WPAOutcome).filter(
            WPAOutcome.venue == venue
        ).limit(20).all()
        
        logger.info(f"Sample of all outcomes for {venue}:")
        for outcome in all_outcomes[:10]:
            logger.info(f"  Target {outcome.target_bucket}, Over {outcome.over_bucket}, "
                       f"Wickets {outcome.wickets_lost}: WP={outcome.win_probability}")
        
        # Check if all win probabilities are 1.0 (data issue)
        high_wp_count = session.query(WPAOutcome).filter(
            WPAOutcome.venue == venue,
            WPAOutcome.win_probability > 0.9
        ).count()
        
        total_count = session.query(WPAOutcome).filter(
            WPAOutcome.venue == venue
        ).count()
        
        logger.info(f"\nData quality check:")
        logger.info(f"  Total outcomes: {total_count}")
        logger.info(f"  High win prob (>0.9): {high_wp_count}")
        logger.info(f"  Percentage high: {high_wp_count/total_count*100:.1f}%")
        
        if high_wp_count / total_count > 0.8:
            logger.warning("⚠️ Most outcomes have high win probability - possible data issue!")
            logger.info("💡 This could be because:")
            logger.info("  - Precomputed data mainly from easy chases")
            logger.info("  - Sample bias in historical data")
            logger.info("  - Need to include more difficult chase scenarios")
            
    except Exception as e:
        logger.error(f"Debug failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    debug_win_probability_issue()
