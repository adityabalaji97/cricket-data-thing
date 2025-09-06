#!/usr/bin/env python3
"""
Crease Combo Granular Update Script

Updates the crease_combo column in deliveries table to be more specific:
- "same" becomes "rhb_rhb" or "lhb_lhb" based on actual batter types
- "left_right" becomes "lhb_rhb" 

This provides more granular analysis of batter combinations at the crease.
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from models import Delivery, Base
import logging
from typing import Dict
from datetime import datetime


class CreaseComboGranularUpdater:
    """Updates crease combo values to be more granular."""
    
    def __init__(self, db_url: str):
        """
        Initialize the updater.
        
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
    
    def get_current_crease_combo_stats(self) -> Dict[str, int]:
        """Get current distribution of crease_combo values."""
        try:
            stats = {}
            
            # Get counts for each crease_combo value
            result = self.session.execute(text("""
                SELECT crease_combo, COUNT(*) as count
                FROM deliveries 
                WHERE crease_combo IS NOT NULL
                GROUP BY crease_combo
                ORDER BY count DESC
            """))
            
            for row in result:
                stats[row[0]] = row[1]
            
            self.logger.info("Current crease_combo distribution:")
            for combo, count in stats.items():
                self.logger.info(f"  {combo}: {count:,}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting crease combo stats: {e}")
            raise
    
    def update_same_to_specific(self) -> Dict[str, int]:
        """
        Update 'same' crease_combo values to specific combinations.
        
        Returns:
            Dictionary with update counts
        """
        results = {'rhb_rhb': 0, 'lhb_lhb': 0, 'errors': 0}
        
        try:
            # Update RHB + RHB combinations
            rhb_rhb_query = text("""
                UPDATE deliveries 
                SET crease_combo = 'rhb_rhb'
                WHERE crease_combo = 'same' 
                AND striker_batter_type = 'RHB' 
                AND non_striker_batter_type = 'RHB'
            """)
            
            rhb_result = self.session.execute(rhb_rhb_query)
            results['rhb_rhb'] = rhb_result.rowcount
            self.logger.info(f"Updated {results['rhb_rhb']:,} deliveries to 'rhb_rhb'")
            
            # Update LHB + LHB combinations
            lhb_lhb_query = text("""
                UPDATE deliveries 
                SET crease_combo = 'lhb_lhb'
                WHERE crease_combo = 'same' 
                AND striker_batter_type = 'LHB' 
                AND non_striker_batter_type = 'LHB'
            """)
            
            lhb_result = self.session.execute(lhb_lhb_query)
            results['lhb_lhb'] = lhb_result.rowcount
            self.logger.info(f"Updated {results['lhb_lhb']:,} deliveries to 'lhb_lhb'")
            
            # Commit the changes
            self.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating 'same' combinations: {e}")
            self.session.rollback()
            results['errors'] += 1
        
        return results
    
    def update_left_right_to_lhb_rhb(self) -> Dict[str, int]:
        """
        Update 'left_right' crease_combo values to 'lhb_rhb'.
        
        Returns:
            Dictionary with update counts
        """
        results = {'lhb_rhb': 0, 'errors': 0}
        
        try:
            # Update all left_right to lhb_rhb
            left_right_query = text("""
                UPDATE deliveries 
                SET crease_combo = 'lhb_rhb'
                WHERE crease_combo = 'left_right'
            """)
            
            lr_result = self.session.execute(left_right_query)
            results['lhb_rhb'] = lr_result.rowcount
            self.logger.info(f"Updated {results['lhb_rhb']:,} deliveries from 'left_right' to 'lhb_rhb'")
            
            # Commit the changes
            self.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating 'left_right' combinations: {e}")
            self.session.rollback()
            results['errors'] += 1
        
        return results
    
    def check_remaining_same_records(self) -> int:
        """Check if any 'same' records remain (these would be edge cases)."""
        try:
            result = self.session.execute(text("""
                SELECT COUNT(*) 
                FROM deliveries 
                WHERE crease_combo = 'same'
            """))
            
            remaining = result.scalar()
            
            if remaining > 0:
                self.logger.warning(f"⚠️  {remaining:,} records still have 'same' value")
                
                # Show details of remaining records
                details = self.session.execute(text("""
                    SELECT striker_batter_type, non_striker_batter_type, COUNT(*)
                    FROM deliveries 
                    WHERE crease_combo = 'same'
                    GROUP BY striker_batter_type, non_striker_batter_type
                    ORDER BY COUNT(*) DESC
                    LIMIT 5
                """))
                
                self.logger.info("Remaining 'same' records breakdown:")
                for row in details:
                    self.logger.info(f"  {row[0]} + {row[1]}: {row[2]:,}")
            else:
                self.logger.info("✅ No 'same' records remaining")
            
            return remaining
            
        except Exception as e:
            self.logger.error(f"Error checking remaining records: {e}")
            return -1
    
    def run_granular_update(self) -> Dict[str, int]:
        """
        Main method to run the granular crease combo update.
        
        Returns:
            Dictionary with all update statistics
        """
        try:
            self.logger.info("Starting granular crease combo update...")
            
            # Get initial stats
            initial_stats = self.get_current_crease_combo_stats()
            
            # Update 'same' to specific combinations
            same_results = self.update_same_to_specific()
            
            # Update 'left_right' to 'lhb_rhb'
            lr_results = self.update_left_right_to_lhb_rhb()
            
            # Check for any remaining 'same' records
            remaining_same = self.check_remaining_same_records()
            
            # Get final stats
            self.logger.info("\nFinal crease_combo distribution:")
            final_stats = self.get_current_crease_combo_stats()
            
            # Combine results
            all_results = {
                'initial_same': initial_stats.get('same', 0),
                'initial_left_right': initial_stats.get('left_right', 0),
                'rhb_rhb_created': same_results['rhb_rhb'],
                'lhb_lhb_created': same_results['lhb_lhb'],
                'lhb_rhb_created': lr_results['lhb_rhb'],
                'remaining_same': remaining_same,
                'total_errors': same_results['errors'] + lr_results['errors'],
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info("Granular crease combo update completed successfully!")
            return all_results
            
        except Exception as e:
            self.logger.error(f"Error during granular update: {e}")
            raise
        finally:
            self.session.close()


def main():
    """Main execution function."""
    # Database configuration
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    
    updater = CreaseComboGranularUpdater(db_url)
    
    try:
        results = updater.run_granular_update()
        
        print("\n=== Granular Crease Combo Update Results ===")
        print(f"Initial 'same' records: {results['initial_same']:,}")
        print(f"Initial 'left_right' records: {results['initial_left_right']:,}")
        print()
        print(f"Created 'rhb_rhb': {results['rhb_rhb_created']:,}")
        print(f"Created 'lhb_lhb': {results['lhb_lhb_created']:,}")
        print(f"Created 'lhb_rhb': {results['lhb_rhb_created']:,}")
        print()
        print(f"Remaining 'same': {results['remaining_same']:,}")
        print(f"Errors: {results['total_errors']:,}")
        print(f"Completed at: {results['timestamp']}")
        
        if results['total_errors'] == 0 and results['remaining_same'] == 0:
            print("\n🎉 Granular update completed successfully!")
            print("\nNew crease combo values:")
            print("  • rhb_rhb: Both batters are right-handed")
            print("  • lhb_lhb: Both batters are left-handed") 
            print("  • lhb_rhb: Left-handed and right-handed combination")
            print("  • unknown: When batter types are unknown")
        else:
            print(f"\n⚠️  Update completed with {results['total_errors']} errors")
            if results['remaining_same'] > 0:
                print(f"⚠️  {results['remaining_same']} 'same' records remain (check logs)")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
