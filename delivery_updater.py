"""
Delivery Updater for Phase 1: Add Base Columns

Populates the new columns in deliveries table:
- striker_batter_type: from players.batter_type for striker
- non_striker_batter_type: from players.batter_type for non_striker
- bowler_type: from players.bowler_type for bowler

This module follows the PRD requirements for modular, manageable code chunks.
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from models import Delivery, Player, Base
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class DeliveryUpdater:
    """Handles updating delivery data with player type information."""
    
    def __init__(self, db_url: str):
        """
        Initialize the delivery updater.
        
        Args:
            db_url: Database connection string
        """
        self.db_url = db_url
        self.engine = create_engine(db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Cache for player data to avoid repeated queries
        self.player_cache = {}
        self.load_player_cache()
    
    def load_player_cache(self):
        """
        Load all player data into memory cache for faster lookups.
        """
        try:
            players = self.session.query(Player).all()
            for player in players:
                self.player_cache[player.name] = {
                    'batter_type': player.batter_type,
                    'bowler_type': player.bowler_type
                }
            
            self.logger.info(f"Loaded {len(self.player_cache)} players into cache")
            
        except Exception as e:
            self.logger.error(f"Error loading player cache: {e}")
            raise
    
    def get_player_info(self, player_name: str) -> Dict[str, Optional[str]]:
        """
        Get player type information from cache.
        
        Args:
            player_name: Name of the player
            
        Returns:
            Dict with batter_type and bowler_type (None if not found)
        """
        return self.player_cache.get(player_name, {
            'batter_type': None,
            'bowler_type': None
        })
    
    def count_deliveries_to_update(self) -> int:
        """
        Count total deliveries that need to be updated.
        
        Returns:
            Number of deliveries to update
        """
        try:
            count = self.session.query(Delivery).filter(
                Delivery.striker_batter_type.is_(None)
            ).count()
            
            self.logger.info(f"Found {count} deliveries to update")
            return count
            
        except Exception as e:
            self.logger.error(f"Error counting deliveries: {e}")
            raise
    
    def update_deliveries_batch(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        Update deliveries in batches to avoid memory issues.
        
        Args:
            batch_size: Number of deliveries to process in each batch
            
        Returns:
            Dictionary with update statistics
        """
        total_updated = 0
        total_errors = 0
        batch_count = 0
        
        try:
            # Get total count for progress tracking
            total_deliveries = self.count_deliveries_to_update()
            
            if total_deliveries == 0:
                self.logger.info("No deliveries need updating")
                return {'total_updated': 0, 'total_errors': 0, 'batch_count': 0}
            
            self.logger.info(f"Starting batch update of {total_deliveries} deliveries...")
            
            # Process in batches
            offset = 0
            while True:
                # Get batch of deliveries
                deliveries = self.session.query(Delivery).filter(
                    Delivery.striker_batter_type.is_(None)
                ).offset(offset).limit(batch_size).all()
                
                if not deliveries:
                    break
                
                batch_count += 1
                batch_updated, batch_errors = self.process_delivery_batch(deliveries)
                
                total_updated += batch_updated
                total_errors += batch_errors
                
                # Commit batch
                self.session.commit()
                
                self.logger.info(
                    f"Batch {batch_count}: Updated {batch_updated}/{len(deliveries)} deliveries "
                    f"(Total: {total_updated}/{total_deliveries})"
                )
                
                offset += batch_size
                
                # Break if we've processed all deliveries
                if len(deliveries) < batch_size:
                    break
            
            self.logger.info(f"Batch update completed: {total_updated} updated, {total_errors} errors")
            
            return {
                'total_updated': total_updated,
                'total_errors': total_errors,
                'batch_count': batch_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error during batch update: {e}")
            raise
    
    def process_delivery_batch(self, deliveries: List[Delivery]) -> Tuple[int, int]:
        """
        Process a batch of deliveries and update their player type information.
        
        Args:
            deliveries: List of Delivery objects to update
            
        Returns:
            Tuple of (updated_count, error_count)
        """
        updated_count = 0
        error_count = 0
        
        for delivery in deliveries:
            try:
                # Get striker info
                striker_info = self.get_player_info(delivery.batter)
                delivery.striker_batter_type = striker_info['batter_type']
                
                # Get non-striker info
                non_striker_info = self.get_player_info(delivery.non_striker)
                delivery.non_striker_batter_type = non_striker_info['batter_type']
                
                # Get bowler info
                bowler_info = self.get_player_info(delivery.bowler)
                delivery.bowler_type = bowler_info['bowler_type']
                
                updated_count += 1
                
            except Exception as e:
                self.logger.error(
                    f"Error updating delivery {delivery.id}: {e}"
                )
                error_count += 1
        
        return updated_count, error_count
    
    def run_update(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        Main method to run the delivery update process.
        
        Args:
            batch_size: Number of deliveries to process in each batch
            
        Returns:
            Dictionary with update statistics
        """
        try:
            self.logger.info("Starting Phase 1 delivery update process...")
            
            results = self.update_deliveries_batch(batch_size)
            
            self.logger.info("Phase 1 delivery update completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Error during delivery update process: {e}")
            raise
        finally:
            self.session.close()


def main():
    """
    Main execution function for delivery update.
    """
    # Database configuration - using the same connection as main app
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    
    updater = DeliveryUpdater(db_url)
    
    try:
        results = updater.run_update(batch_size=1000)
        print("\n=== Phase 1 Delivery Update Results ===")
        print(f"Total updated: {results['total_updated']}")
        print(f"Total errors: {results['total_errors']}")
        print(f"Batches processed: {results['batch_count']}")
        print(f"Completed at: {results['timestamp']}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
