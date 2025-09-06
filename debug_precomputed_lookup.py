"""
Debug why precomputed data isn't being found
"""
from database import get_database_connection
from precomputed_models import WPAOutcome
from precomputed_service import PrecomputedDataService
from models import Match
import logging
from datetime import date

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_precomputed_lookup():
    """Debug why precomputed data lookup is failing"""
    
    engine, session_factory = get_database_connection()
    session = session_factory()
    service = PrecomputedDataService()
    
    try:
        # Get a sample match that was tested
        match = session.query(Match).filter(Match.id == "548322").first()
        if not match:
            logger.error("Test match not found")
            return
        
        logger.info(f"Test match: {match.team1} vs {match.team2}")
        logger.info(f"Venue: {match.venue}")
        logger.info(f"Date: {match.date}")
        logger.info(f"Competition: {match.competition}")
        
        # Check if we have WPA data for this venue
        wpa_count = session.query(WPAOutcome).filter(
            WPAOutcome.venue == match.venue
        ).count()
        logger.info(f"WPA outcomes for this venue: {wpa_count}")
        
        # Check if we have data before this match date
        wpa_before_count = session.query(WPAOutcome).filter(
            WPAOutcome.venue == match.venue,
            WPAOutcome.data_through_date < match.date
        ).count()
        logger.info(f"WPA outcomes before match date: {wpa_before_count}")
        
        # Test the actual lookup
        logger.info("Testing precomputed lookup...")
        
        # Sample parameters from the test
        target = 156
        over = 0
        wickets = 0
        runs = 2
        
        target_bucket = service._get_target_bucket(target)
        over_bucket = service._get_over_bucket(over)
        
        logger.info(f"Looking for: target_bucket={target_bucket}, over_bucket={over_bucket}, wickets={wickets}")
        
        # Direct query to see what's available
        direct_query = session.query(WPAOutcome).filter(
            WPAOutcome.venue == match.venue,
            WPAOutcome.target_bucket == target_bucket,
            WPAOutcome.over_bucket == over_bucket,
            WPAOutcome.wickets_lost == wickets,
            WPAOutcome.data_through_date < match.date
        )
        
        available = direct_query.all()
        logger.info(f"Direct query found: {len(available)} results")
        
        if available:
            sample = available[0]
            logger.info(f"Sample result: runs_range={sample.runs_range_min}-{sample.runs_range_max}, win_prob={sample.win_probability}")
        
        # Test the service lookup
        win_prob, data_source = service.get_win_probability(
            session=session,
            venue=match.venue,
            target=target,
            over=over,
            wickets=wickets,
            runs=runs,
            match_date=match.date,
            league=match.competition
        )
        
        logger.info(f"Service returned: win_prob={win_prob}, source={data_source}")
        
        # Check what target/over buckets we actually have
        logger.info("Checking available buckets for this venue...")
        buckets = session.query(
            WPAOutcome.target_bucket, 
            WPAOutcome.over_bucket,
            WPAOutcome.wickets_lost
        ).filter(
            WPAOutcome.venue == match.venue,
            WPAOutcome.data_through_date < match.date
        ).distinct().limit(10).all()
        
        logger.info("Available buckets (first 10):")
        for bucket in buckets:
            logger.info(f"  target={bucket.target_bucket}, over={bucket.over_bucket}, wickets={bucket.wickets_lost}")
            
    except Exception as e:
        logger.error(f"Debug failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    debug_precomputed_lookup()
