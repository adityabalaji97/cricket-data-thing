"""
Debug actual WPA outcomes data to understand binary probability issue
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_session
from precomputed_models import WPAOutcome
from sqlalchemy import text, func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_wpa_outcomes():
    """Analyze the actual WPA outcomes data to find the root cause"""
    
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # Get basic statistics about WPA outcomes
        total_outcomes = session.query(WPAOutcome).count()
        logger.info(f"Total WPA outcomes: {total_outcomes}")
        
        # Check win probability distribution
        wp_stats = session.query(
            func.min(WPAOutcome.win_probability).label('min_wp'),
            func.max(WPAOutcome.win_probability).label('max_wp'),
            func.avg(WPAOutcome.win_probability).label('avg_wp'),
            func.count().label('total_count')
        ).first()
        
        logger.info(f"Win Probability Stats:")
        logger.info(f"  Min: {wp_stats.min_wp}")
        logger.info(f"  Max: {wp_stats.max_wp}")
        logger.info(f"  Avg: {wp_stats.avg_wp:.3f}")
        logger.info(f"  Count: {wp_stats.total_count}")
        
        # Check how many are exactly 0.0 or 1.0
        binary_query = session.query(
            func.count().filter(WPAOutcome.win_probability == 0.0).label('zero_count'),
            func.count().filter(WPAOutcome.win_probability == 1.0).label('one_count'),
            func.count().filter(
                (WPAOutcome.win_probability > 0.0) & (WPAOutcome.win_probability < 1.0)
            ).label('middle_count')
        ).first()
        
        logger.info(f"\nBinary Distribution:")
        logger.info(f"  Exactly 0.0: {binary_query.zero_count}")
        logger.info(f"  Exactly 1.0: {binary_query.one_count}")
        logger.info(f"  Between 0-1: {binary_query.middle_count}")
        
        binary_percentage = (binary_query.zero_count + binary_query.one_count) / total_outcomes * 100
        logger.info(f"  Binary percentage: {binary_percentage:.1f}%")
        
        # Sample some actual records to see the pattern
        logger.info("\nSample WPA Outcomes:")
        samples = session.query(WPAOutcome).limit(20).all()
        
        for sample in samples:
            logger.info(f"  {sample.venue[:30]:30} | Target: {sample.target_bucket:3d} | "
                       f"Over: {sample.over_bucket:2d} | Wickets: {sample.wickets_lost} | "
                       f"Score: {sample.runs_range_min:3d}-{sample.runs_range_max:3d} | "
                       f"WP: {sample.win_probability:.3f} | "
                       f"Sample: {sample.successful_chases}/{sample.total_outcomes}")
        
        # Check specific problematic scenarios
        logger.info("\nAnalyzing specific problematic scenarios...")
        
        # Look for scenarios that should have mixed outcomes
        mixed_scenarios = session.query(WPAOutcome).filter(
            WPAOutcome.target_bucket.between(150, 160),  # Moderate targets
            WPAOutcome.over_bucket.between(4, 8),        # Middle overs
            WPAOutcome.wickets_lost.between(1, 3),       # Some wickets lost
            WPAOutcome.sample_size >= 10                 # Decent sample size
        ).all()
        
        logger.info(f"Found {len(mixed_scenarios)} scenarios that should have mixed outcomes:")
        
        for scenario in mixed_scenarios[:10]:  # Show first 10
            success_rate = scenario.successful_chases / scenario.total_outcomes
            logger.info(f"  Target {scenario.target_bucket}, Over {scenario.over_bucket}, "
                       f"Wickets {scenario.wickets_lost}: "
                       f"{scenario.successful_chases}/{scenario.total_outcomes} = {success_rate:.3f} "
                       f"(stored as {scenario.win_probability:.3f})")
            
            if success_rate != scenario.win_probability:
                logger.warning(f"    ⚠️ Mismatch! Calculated {success_rate:.3f} vs stored {scenario.win_probability:.3f}")
        
        # Check if the issue is in bucketing - are we getting extreme scenarios only?
        logger.info("\nAnalyzing bucket distributions...")
        
        # Check target distribution
        target_dist = session.query(
            WPAOutcome.target_bucket,
            func.count().label('count'),
            func.avg(WPAOutcome.win_probability).label('avg_wp')
        ).group_by(WPAOutcome.target_bucket).order_by(WPAOutcome.target_bucket).all()
        
        logger.info("Target bucket distribution:")
        for dist in target_dist:
            logger.info(f"  Target {dist.target_bucket}: {dist.count} outcomes, avg WP: {dist.avg_wp:.3f}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    analyze_wpa_outcomes()
