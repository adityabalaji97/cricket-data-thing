"""
Test the improved precomputed lookup with relaxed chronological constraint
"""
from database import get_database_connection
from precomputed_service import PrecomputedDataService
from models import Match
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_improved_lookup():
    """Test the improved precomputed lookup"""
    
    engine, session_factory = get_database_connection()
    session = session_factory()
    service = PrecomputedDataService()
    
    try:
        # Get the same test match
        match = session.query(Match).filter(Match.id == "548322").first()
        
        logger.info(f"Testing improved lookup for: {match.venue} on {match.date}")
        
        # Test parameters from the demo
        target = 156
        over = 0
        wickets = 0
        runs = 2
        
        # Test the improved service
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
        
        logger.info(f"✅ Improved service result:")
        logger.info(f"   Win probability: {win_prob}")
        logger.info(f"   Data source: {data_source}")
        
        if data_source in ["venue", "venue_relaxed", "cluster", "league", "global"]:
            logger.info("🎉 SUCCESS: Using precomputed data!")
        else:
            logger.warning("⚠️ Still using heuristic fallback")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_improved_lookup()
