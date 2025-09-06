"""
Test script for WPA Engine - Verification and Integration Test

This script tests the core WPA engine functionality with sample deliveries
to ensure proper integration with existing infrastructure.
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from database import get_database_connection
from models import Match, Delivery
from wpa_engine import OptimizedWPAEngine
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WPAEngineTest:
    """Test suite for WPA Engine functionality"""
    
    def __init__(self):
        self.engine, self.session_factory = get_database_connection()
        self.wpa_engine = OptimizedWPAEngine()
        
    def get_sample_second_innings_deliveries(self, limit: int = 10) -> list:
        """
        Get sample second innings deliveries for testing.
        
        Args:
            limit: Number of deliveries to fetch
            
        Returns:
            List of delivery objects
        """
        session = self.session_factory()
        try:
            # Get deliveries from a second innings chase
            deliveries = session.query(Delivery).filter(
                Delivery.innings == 2,
                Delivery.wpa_batter.is_(None)  # Not yet calculated
            ).limit(limit).all()
            
            logger.info(f"Found {len(deliveries)} sample second innings deliveries")
            return deliveries
            
        except Exception as e:
            logger.error(f"Error getting sample deliveries: {e}")
            return []
        finally:
            session.close()
    
    def test_match_state_calculation(self):
        """Test match state calculation for sample deliveries"""
        logger.info("🧪 Testing match state calculation...")
        
        session = self.session_factory()
        try:
            # Get a sample delivery
            sample_deliveries = self.get_sample_second_innings_deliveries(5)
            
            if not sample_deliveries:
                logger.warning("No sample deliveries found for testing")
                return False
            
            for delivery in sample_deliveries:
                logger.info(f"Testing delivery {delivery.id} (Match: {delivery.match_id}, Over: {delivery.over}.{delivery.ball})")
                
                # Test match state calculation
                match_state = self.wpa_engine.get_match_state_at_delivery(session, delivery)
                
                if match_state:
                    logger.info(f"✅ Match state: {match_state}")
                    logger.info(f"   State details: {match_state.to_dict()}")
                    
                    # Test post-delivery state
                    after_state = self.wpa_engine.get_match_state_after_delivery(session, delivery)
                    if after_state:
                        logger.info(f"✅ After state: {after_state}")
                    else:
                        logger.warning(f"⚠️ Could not calculate after state for delivery {delivery.id}")
                else:
                    logger.warning(f"⚠️ Could not calculate match state for delivery {delivery.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error testing match state calculation: {e}")
            return False
        finally:
            session.close()
    
    def test_win_probability_calculation(self):
        """Test win probability calculation"""
        logger.info("🧪 Testing win probability calculation...")
        
        session = self.session_factory()
        try:
            sample_deliveries = self.get_sample_second_innings_deliveries(3)
            
            if not sample_deliveries:
                logger.warning("No sample deliveries found for WP testing")
                return False
            
            for delivery in sample_deliveries:
                # Get match info and state
                match_info = self.wpa_engine.get_match_info(session, delivery.match_id)
                match_state = self.wpa_engine.get_match_state_at_delivery(session, delivery)
                
                if match_info and match_state:
                    logger.info(f"Testing WP for delivery {delivery.id}")
                    logger.info(f"Match: {match_info['team1']} vs {match_info['team2']} at {match_info['venue']}"))
                    
                    # Calculate win probability
                    win_prob = self.wpa_engine.calculate_win_probability(
                        session, match_state, match_info["venue"], 
                        match_info["date"], match_info["competition"]
                    )
                    
                    logger.info(f"✅ Win probability: {win_prob:.3f} ({win_prob*100:.1f}%)")
                    logger.info(f"   Target: {match_state.target}, Score: {match_state.current_score}, Needed: {match_state.runs_needed}")
                    logger.info(f"   Overs: {match_state.overs_completed:.1f}, Wickets: {match_state.wickets_lost}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error testing win probability calculation: {e}")
            return False
        finally:
            session.close()
    
    def test_wpa_calculation(self):
        """Test complete WPA calculation for sample deliveries"""
        logger.info("🧪 Testing complete WPA calculation...")
        
        session = self.session_factory()
        try:
            sample_deliveries = self.get_sample_second_innings_deliveries(5)
            
            if not sample_deliveries:
                logger.warning("No sample deliveries found for WPA testing")
                return False
            
            successful_calculations = 0
            
            for delivery in sample_deliveries:
                logger.info(f"Testing WPA calculation for delivery {delivery.id}")
                
                # Calculate WPA
                wpa_result = self.wpa_engine.calculate_delivery_wpa(session, delivery)
                
                if wpa_result:
                    wpa_batter, wpa_bowler, metadata = wpa_result  # Updated to expect 3 values
                    logger.info(f"✅ WPA calculated - Batter: {wpa_batter:+.3f}, Bowler: {wpa_bowler:+.3f}")
                    logger.info(f"   Data source: {metadata['data_source']}, Venue: {metadata['venue']}")
                    
                    # Verify WPA values are reasonable
                    if abs(wpa_batter) <= 1.0 and abs(wpa_bowler) <= 1.0:
                        logger.info(f"   WPA values are within expected range")
                        successful_calculations += 1
                    else:
                        logger.warning(f"   WPA values seem extreme: {wpa_batter}, {wpa_bowler}")
                    
                    # Verify batter + bowler WPA = 0 (conservation of win probability)
                    if abs(wpa_batter + wpa_bowler) < 0.001:
                        logger.info(f"   ✅ WPA conservation verified")
                    else:
                        logger.warning(f"   ⚠️ WPA conservation issue: sum = {wpa_batter + wpa_bowler}")
                        
                else:
                    logger.info(f"   No WPA calculated (likely first innings or insufficient data)")
            
            logger.info(f"Successfully calculated WPA for {successful_calculations}/{len(sample_deliveries)} deliveries")
            return successful_calculations > 0
            
        except Exception as e:
            logger.error(f"Error testing WPA calculation: {e}")
            return False
        finally:
            session.close()
    
    def test_database_integration(self):
        """Test database storage of WPA values"""
        logger.info("🧪 Testing database integration...")
        
        session = self.session_factory()
        try:
            # Get one sample delivery
            sample_deliveries = self.get_sample_second_innings_deliveries(1)
            
            if not sample_deliveries:
                logger.warning("No sample deliveries found for DB testing")
                return False
            
            delivery = sample_deliveries[0]
            logger.info(f"Testing database storage with delivery {delivery.id}")
            
            # Calculate and store WPA
            success = self.wpa_engine.calculate_and_store_delivery_wpa(session, delivery)
            
            if success:
                logger.info("✅ WPA calculation and storage successful")
                
                # Verify the delivery was updated
                session.refresh(delivery)
                if delivery.has_wpa_calculated():
                    logger.info(f"✅ Database verification: WPA values stored")
                    logger.info(f"   Batter WPA: {delivery.wpa_batter}")
                    logger.info(f"   Bowler WPA: {delivery.wpa_bowler}")
                    logger.info(f"   Computed: {delivery.wpa_computed_date}")
                    return True
                else:
                    logger.error("❌ Database verification failed: WPA values not found")
                    return False
            else:
                logger.error("❌ WPA calculation and storage failed")
                return False
                
        except Exception as e:
            logger.error(f"Error testing database integration: {e}")
            return False
        finally:
            session.close()
    
    def run_full_test_suite(self):
        """Run complete test suite for WPA engine"""
        logger.info("🚀 Starting WPA Engine Test Suite")
        logger.info("=" * 60)
        
        test_results = {
            "match_state": False,
            "win_probability": False,
            "wpa_calculation": False,
            "database_integration": False
        }
        
        # Run all tests
        test_results["match_state"] = self.test_match_state_calculation()
        test_results["win_probability"] = self.test_win_probability_calculation()
        test_results["wpa_calculation"] = self.test_wpa_calculation()
        test_results["database_integration"] = self.test_database_integration()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("🏁 WPA Engine Test Results:")
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        logger.info(f"Overall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed! WPA Engine is ready for production use.")
            return True
        else:
            logger.warning("⚠️ Some tests failed. Review issues before proceeding.")
            return False


def main():
    """Run WPA engine tests"""
    try:
        tester = WPAEngineTest()
        success = tester.run_full_test_suite()
        
        if success:
            print("\n✅ WPA Engine test suite completed successfully!")
            return 0
        else:
            print("\n❌ WPA Engine test suite had failures!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
