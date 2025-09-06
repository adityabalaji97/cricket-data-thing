"""
Derived Columns Updater for Phase 2: Add Derived Columns

Populates the derived analysis columns in deliveries table:
- crease_combo: Analysis of left-right batter combination at crease
- ball_direction: Analysis of ball direction relative to striker

Logic implementation:
- crease_combo = "same" if striker_batterType = non_striker_batterType
- crease_combo = "unknown" if striker_batterType = unknown OR non_striker_batterType = unknown  
- crease_combo = "left_right" if striker_batterType != non_striker_batterType (and both known)

- ball_direction = "intoBatter" if:
  (striker_batterType = RHB AND bowler_type IN [RO, LC]) OR
  (striker_batterType = LHB AND bowler_type IN [RL, LO])
- ball_direction = "awayFromBatter" if:
  (striker_batterType = LHB AND bowler_type IN [RO, LC]) OR  
  (striker_batterType = RHB AND bowler_type IN [RL, LO])

This module follows the PRD requirements for modular, manageable code chunks.
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from models import Delivery, Base
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class DerivedColumnsUpdater:
    """Handles updating derived analysis columns in deliveries table."""
    
    def __init__(self, db_url: str):
        """
        Initialize the derived columns updater.
        
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
        
        # Define bowler type mappings for ball direction logic
        self.into_batter_bowler_types = {
            'RHB': ['RO', 'LC'],  # Right-handed batter: Right-arm off-spin, Left-arm chinaman
            'LHB': ['RL', 'LO']   # Left-handed batter: Right-arm leg-spin, Left-arm orthodox
        }
        
        self.away_from_batter_bowler_types = {
            'LHB': ['RO', 'LC'],  # Left-handed batter: Right-arm off-spin, Left-arm chinaman  
            'RHB': ['RL', 'LO']   # Right-handed batter: Right-arm leg-spin, Left-arm orthodox
        }
    
    def calculate_crease_combo(self, striker_type: Optional[str], non_striker_type: Optional[str]) -> str:
        """
        Calculate granular crease combination based on batter types.
        
        Args:
            striker_type: Striker batter type (LHB/RHB)
            non_striker_type: Non-striker batter type (LHB/RHB)
            
        Returns:
            Crease combo: 'rhb_rhb', 'lhb_lhb', 'lhb_rhb', or 'unknown'
        """
        # Check for unknown values
        if not striker_type or not non_striker_type or striker_type == 'unknown' or non_striker_type == 'unknown':
            return 'unknown'
        
        # Check for specific combinations
        if striker_type == 'RHB' and non_striker_type == 'RHB':
            return 'rhb_rhb'
        elif striker_type == 'LHB' and non_striker_type == 'LHB':
            return 'lhb_lhb'
        elif (striker_type == 'LHB' and non_striker_type == 'RHB') or (striker_type == 'RHB' and non_striker_type == 'LHB'):
            return 'lhb_rhb'
        
        # Fallback for any unexpected combinations
        return 'unknown'
    
    def calculate_ball_direction(self, striker_type: Optional[str], bowler_type: Optional[str]) -> str:
        """
        Calculate ball direction based on striker type and bowler type.
        
        Args:
            striker_type: Striker batter type (LHB/RHB)
            bowler_type: Bowler type (LO/LM/RL/RM/RO/etc)
            
        Returns:
            Ball direction: 'intoBatter', 'awayFromBatter', or 'unknown'
        """
        # Check for unknown/missing values
        if not striker_type or not bowler_type or striker_type == 'unknown' or bowler_type == 'unknown':
            return 'unknown'
        
        # Check for intoBatter direction
        if striker_type in self.into_batter_bowler_types:
            if bowler_type in self.into_batter_bowler_types[striker_type]:
                return 'intoBatter'
        
        # Check for awayFromBatter direction
        if striker_type in self.away_from_batter_bowler_types:
            if bowler_type in self.away_from_batter_bowler_types[striker_type]:
                return 'awayFromBatter'
        
        # If no specific direction found, return unknown
        return 'unknown'
    
    def count_deliveries_to_update(self) -> int:
        """
        Count total deliveries that need derived column updates.
        
        Returns:
            Number of deliveries to update
        """
        try:
            count = self.session.query(Delivery).filter(
                Delivery.crease_combo.is_(None)
            ).count()
            
            self.logger.info(f"Found {count} deliveries needing derived column updates")
            return count
            
        except Exception as e:
            self.logger.error(f"Error counting deliveries for derived updates: {e}")
            raise
    
    def process_derived_batch(self, deliveries: List[Delivery]) -> Tuple[int, int]:
        """
        Process a batch of deliveries and update their derived columns.
        
        Args:
            deliveries: List of Delivery objects to update
            
        Returns:
            Tuple of (updated_count, error_count)
        """
        updated_count = 0
        error_count = 0
        
        for delivery in deliveries:
            try:
                # Calculate crease combo
                delivery.crease_combo = self.calculate_crease_combo(
                    delivery.striker_batter_type,
                    delivery.non_striker_batter_type
                )
                
                # Calculate ball direction
                delivery.ball_direction = self.calculate_ball_direction(
                    delivery.striker_batter_type,
                    delivery.bowler_type
                )
                
                updated_count += 1
                
            except Exception as e:
                self.logger.error(
                    f"Error updating derived columns for delivery {delivery.id}: {e}"
                )
                error_count += 1
        
        return updated_count, error_count
    
    def update_derived_columns_batch(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        Update derived columns in batches to avoid memory issues.
        
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
                self.logger.info("No deliveries need derived column updates")
                return {'total_updated': 0, 'total_errors': 0, 'batch_count': 0}
            
            self.logger.info(f"Starting batch update of derived columns for {total_deliveries} deliveries...")
            
            # Process in batches
            offset = 0
            while True:
                # Get batch of deliveries that need derived column updates
                deliveries = self.session.query(Delivery).filter(
                    Delivery.crease_combo.is_(None)
                ).offset(offset).limit(batch_size).all()
                
                if not deliveries:
                    break
                
                batch_count += 1
                batch_updated, batch_errors = self.process_derived_batch(deliveries)
                
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
            
            self.logger.info(f"Derived columns batch update completed: {total_updated} updated, {total_errors} errors")
            
            return {
                'total_updated': total_updated,
                'total_errors': total_errors,
                'batch_count': batch_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error during derived columns batch update: {e}")
            raise
    
    def run_update(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        Main method to run the derived columns update process.
        
        Args:
            batch_size: Number of deliveries to process in each batch
            
        Returns:
            Dictionary with update statistics
        """
        try:
            self.logger.info("Starting Phase 2 derived columns update process...")
            
            results = self.update_derived_columns_batch(batch_size)
            
            self.logger.info("Phase 2 derived columns update completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Error during derived columns update process: {e}")
            raise
        finally:
            self.session.close()


def main():
    """
    Main execution function for derived columns update.
    """
    # Database configuration - using the same connection as main app
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    
    updater = DerivedColumnsUpdater(db_url)
    
    try:
        results = updater.run_update(batch_size=1000)
        print("\n=== Phase 2 Derived Columns Update Results ===")
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
