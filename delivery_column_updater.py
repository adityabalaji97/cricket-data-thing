#!/usr/bin/env python3
"""
Delivery Column Updater - Bulk Operations

This script efficiently updates delivery columns that depend on player data:
- striker_batter_type
- non_striker_batter_type  
- bowler_type
- crease_combo
- ball_direction

Designed for 1.6M+ deliveries with optimized bulk operations.

Usage:
    python delivery_column_updater.py --update-all
    python delivery_column_updater.py --update-batter-types
    python delivery_column_updater.py --update-bowler-types
    python delivery_column_updater.py --update-derived-columns
    python delivery_column_updater.py --batch-size 50000
"""

import argparse
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import get_database_connection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DeliveryColumnUpdater:
    """Efficiently updates delivery columns with bulk operations."""
    
    def __init__(self, batch_size: int = 25000):
        """
        Initialize the updater.
        
        Args:
            batch_size: Number of deliveries to process in each batch
        """
        self.batch_size = batch_size
        self.engine, SessionLocal = get_database_connection()
        self.session = SessionLocal()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up database connection."""
        self.session.close()
    
    def get_delivery_count(self) -> int:
        """Get total count of deliveries for progress tracking."""
        result = self.session.execute(text("SELECT COUNT(*) FROM deliveries"))
        return result.scalar()
    
    def get_update_stats(self) -> Dict[str, int]:
        """Get current statistics of delivery columns."""
        stats_query = text("""
            SELECT 
                COUNT(*) as total_deliveries,
                COUNT(striker_batter_type) as striker_populated,
                COUNT(non_striker_batter_type) as non_striker_populated,
                COUNT(bowler_type) as bowler_type_populated,
                COUNT(crease_combo) as crease_combo_populated,
                COUNT(ball_direction) as ball_direction_populated,
                COUNT(CASE WHEN striker_batter_type IS NULL THEN 1 END) as striker_null,
                COUNT(CASE WHEN non_striker_batter_type IS NULL THEN 1 END) as non_striker_null,
                COUNT(CASE WHEN bowler_type IS NULL THEN 1 END) as bowler_null
            FROM deliveries
        """)
        
        result = self.session.execute(stats_query)
        row = result.fetchone()
        
        return {
            'total_deliveries': row[0],
            'striker_populated': row[1],
            'non_striker_populated': row[2],
            'bowler_type_populated': row[3],
            'crease_combo_populated': row[4],
            'ball_direction_populated': row[5],
            'striker_null': row[6],
            'non_striker_null': row[7],
            'bowler_null': row[8]
        }
    
    def update_batter_types_bulk(self) -> int:
        """
        Update striker_batter_type and non_striker_batter_type using bulk operations.
        
        Returns:
            Number of deliveries updated
        """
        logger.info("Starting bulk update of batter types...")
        
        total_deliveries = self.get_delivery_count()
        processed = 0
        
        # Use a single optimized query that updates both columns at once
        for offset in range(0, total_deliveries, self.batch_size):
            try:
                # Bulk update query using subquery for efficiency
                update_query = text("""
                    UPDATE deliveries 
                    SET 
                        striker_batter_type = COALESCE(p1.batter_type, 'unknown'),
                        non_striker_batter_type = COALESCE(p2.batter_type, 'unknown')
                    FROM (
                        SELECT id, batter, non_striker
                        FROM deliveries 
                        ORDER BY id 
                        LIMIT :batch_size OFFSET :offset
                    ) AS batch
                    LEFT JOIN players p1 ON batch.batter = p1.name
                    LEFT JOIN players p2 ON batch.non_striker = p2.name
                    WHERE deliveries.id = batch.id
                """)
                
                result = self.session.execute(update_query, {
                    "batch_size": self.batch_size, 
                    "offset": offset
                })
                
                batch_updated = result.rowcount
                processed += batch_updated
                
                # Commit after each batch
                self.session.commit()
                
                progress = (processed / total_deliveries) * 100
                logger.info(f"Batter types: {processed:,}/{total_deliveries:,} ({progress:.1f}%) - Batch: {batch_updated:,}")
                
            except Exception as e:
                logger.error(f"Error updating batter types at offset {offset}: {e}")
                self.session.rollback()
                raise
        
        logger.info(f"✅ Completed batter types update: {processed:,} deliveries")
        return processed
    
    def update_bowler_types_bulk(self) -> int:
        """
        Update bowler_type using bulk operations.
        
        Returns:
            Number of deliveries updated
        """
        logger.info("Starting bulk update of bowler types...")
        
        total_deliveries = self.get_delivery_count()
        processed = 0
        
        for offset in range(0, total_deliveries, self.batch_size):
            try:
                update_query = text("""
                    UPDATE deliveries 
                    SET bowler_type = COALESCE(p.bowler_type, 'unknown')
                    FROM (
                        SELECT id, bowler
                        FROM deliveries 
                        ORDER BY id 
                        LIMIT :batch_size OFFSET :offset
                    ) AS batch
                    LEFT JOIN players p ON batch.bowler = p.name
                    WHERE deliveries.id = batch.id
                """)
                
                result = self.session.execute(update_query, {
                    "batch_size": self.batch_size, 
                    "offset": offset
                })
                
                batch_updated = result.rowcount
                processed += batch_updated
                
                # Commit after each batch
                self.session.commit()
                
                progress = (processed / total_deliveries) * 100
                logger.info(f"Bowler types: {processed:,}/{total_deliveries:,} ({progress:.1f}%) - Batch: {batch_updated:,}")
                
            except Exception as e:
                logger.error(f"Error updating bowler types at offset {offset}: {e}")
                self.session.rollback()
                raise
        
        logger.info(f"✅ Completed bowler types update: {processed:,} deliveries")
        return processed
    
    def update_derived_columns_bulk(self) -> Tuple[int, int]:
        """
        Update crease_combo and ball_direction using bulk operations.
        
        Returns:
            Tuple of (crease_combo_updated, ball_direction_updated)
        """
        logger.info("Starting bulk update of derived columns...")
        
        total_deliveries = self.get_delivery_count()
        crease_processed = 0
        ball_processed = 0
        
        for offset in range(0, total_deliveries, self.batch_size):
            try:
                # Update crease_combo
                crease_query = text("""
                    UPDATE deliveries 
                    SET crease_combo = CASE
                        WHEN striker_batter_type = 'unknown' OR non_striker_batter_type = 'unknown' THEN 'unknown'
                        WHEN striker_batter_type = 'RHB' AND non_striker_batter_type = 'RHB' THEN 'rhb_rhb'
                        WHEN striker_batter_type = 'LHB' AND non_striker_batter_type = 'LHB' THEN 'lhb_lhb'
                        WHEN (striker_batter_type = 'LHB' AND non_striker_batter_type = 'RHB') OR 
                             (striker_batter_type = 'RHB' AND non_striker_batter_type = 'LHB') THEN 'lhb_rhb'
                        ELSE 'unknown'
                    END
                    WHERE id IN (
                        SELECT id FROM deliveries 
                        ORDER BY id 
                        LIMIT :batch_size OFFSET :offset
                    )
                """)
                
                crease_result = self.session.execute(crease_query, {
                    "batch_size": self.batch_size, 
                    "offset": offset
                })
                
                # Update ball_direction
                ball_query = text("""
                    UPDATE deliveries 
                    SET ball_direction = CASE
                        WHEN striker_batter_type = 'unknown' OR bowler_type = 'unknown' THEN 'unknown'
                        WHEN (striker_batter_type = 'RHB' AND bowler_type IN ('RO', 'LC')) 
                             OR (striker_batter_type = 'LHB' AND bowler_type IN ('RL', 'LO')) THEN 'intoBatter'
                        WHEN (striker_batter_type = 'LHB' AND bowler_type IN ('RO', 'LC'))
                             OR (striker_batter_type = 'RHB' AND bowler_type IN ('RL', 'LO')) THEN 'awayFromBatter'
                        ELSE 'unknown'
                    END
                    WHERE id IN (
                        SELECT id FROM deliveries 
                        ORDER BY id 
                        LIMIT :batch_size OFFSET :offset
                    )
                """)
                
                ball_result = self.session.execute(ball_query, {
                    "batch_size": self.batch_size, 
                    "offset": offset
                })
                
                crease_batch = crease_result.rowcount
                ball_batch = ball_result.rowcount
                crease_processed += crease_batch
                ball_processed += ball_batch
                
                # Commit after each batch
                self.session.commit()
                
                progress = (crease_processed / total_deliveries) * 100
                logger.info(f"Derived columns: {crease_processed:,}/{total_deliveries:,} ({progress:.1f}%) - Crease: {crease_batch:,}, Ball: {ball_batch:,}")
                
            except Exception as e:
                logger.error(f"Error updating derived columns at offset {offset}: {e}")
                self.session.rollback()
                raise
        
        logger.info(f"✅ Completed derived columns update: Crease {crease_processed:,}, Ball direction {ball_processed:,}")
        return crease_processed, ball_processed
    
    def update_specific_players(self, player_names: List[str]) -> int:
        """
        Update delivery columns for specific players only (more efficient for small updates).
        
        Args:
            player_names: List of player names to update
            
        Returns:
            Number of deliveries updated
        """
        logger.info(f"Updating delivery columns for {len(player_names)} specific players...")
        
        # Convert to tuple for SQL IN clause
        players_tuple = tuple(player_names)
        updated = 0
        
        try:
            # Update batter types for specific players
            batter_query = text("""
                UPDATE deliveries 
                SET 
                    striker_batter_type = COALESCE(p1.batter_type, 'unknown'),
                    non_striker_batter_type = COALESCE(p2.batter_type, 'unknown')
                FROM players p1, players p2
                WHERE deliveries.batter = p1.name 
                AND deliveries.non_striker = p2.name
                AND (deliveries.batter = ANY(:players) OR deliveries.non_striker = ANY(:players))
            """)
            
            result = self.session.execute(batter_query, {"players": list(players_tuple)})
            batter_updated = result.rowcount
            
            # Update bowler types for specific players
            bowler_query = text("""
                UPDATE deliveries 
                SET bowler_type = COALESCE(p.bowler_type, 'unknown')
                FROM players p
                WHERE deliveries.bowler = p.name 
                AND deliveries.bowler = ANY(:players)
            """)
            
            result = self.session.execute(bowler_query, {"players": list(players_tuple)})
            bowler_updated = result.rowcount
            
            # Update derived columns for affected deliveries
            derived_query = text("""
                UPDATE deliveries 
                SET 
                    crease_combo = CASE
                        WHEN striker_batter_type = 'unknown' OR non_striker_batter_type = 'unknown' THEN 'unknown'
                        WHEN striker_batter_type = 'RHB' AND non_striker_batter_type = 'RHB' THEN 'rhb_rhb'
                        WHEN striker_batter_type = 'LHB' AND non_striker_batter_type = 'LHB' THEN 'lhb_lhb'
                        WHEN (striker_batter_type = 'LHB' AND non_striker_batter_type = 'RHB') OR 
                             (striker_batter_type = 'RHB' AND non_striker_batter_type = 'LHB') THEN 'lhb_rhb'
                        ELSE 'unknown'
                    END,
                    ball_direction = CASE
                        WHEN striker_batter_type = 'unknown' OR bowler_type = 'unknown' THEN 'unknown'
                        WHEN (striker_batter_type = 'RHB' AND bowler_type IN ('RO', 'LC')) 
                             OR (striker_batter_type = 'LHB' AND bowler_type IN ('RL', 'LO')) THEN 'intoBatter'
                        WHEN (striker_batter_type = 'LHB' AND bowler_type IN ('RO', 'LC'))
                             OR (striker_batter_type = 'RHB' AND bowler_type IN ('RL', 'LO')) THEN 'awayFromBatter'
                        ELSE 'unknown'
                    END
                WHERE batter = ANY(:players) OR non_striker = ANY(:players) OR bowler = ANY(:players)
            """)
            
            result = self.session.execute(derived_query, {"players": list(players_tuple)})
            derived_updated = result.rowcount
            
            # Commit all changes
            self.session.commit()
            
            total_updated = max(batter_updated, bowler_updated, derived_updated)
            logger.info(f"✅ Updated {total_updated:,} deliveries for specific players")
            logger.info(f"   Batter types: {batter_updated:,}, Bowler types: {bowler_updated:,}, Derived: {derived_updated:,}")
            
            return total_updated
            
        except Exception as e:
            logger.error(f"Error updating specific players: {e}")
            self.session.rollback()
            raise
    
    def run_full_update(self) -> Dict[str, int]:
        """
        Run complete update of all delivery columns.
        
        Returns:
            Dictionary with update statistics
        """
        logger.info("🚀 Starting full delivery columns update...")
        
        start_time = datetime.now()
        
        # Get initial stats
        initial_stats = self.get_update_stats()
        logger.info(f"Initial state: {initial_stats['total_deliveries']:,} total deliveries")
        logger.info(f"  Striker null: {initial_stats['striker_null']:,}")
        logger.info(f"  Non-striker null: {initial_stats['non_striker_null']:,}")
        logger.info(f"  Bowler null: {initial_stats['bowler_null']:,}")
        
        results = {}
        
        # Step 1: Update batter types
        results['batter_types_updated'] = self.update_batter_types_bulk()
        
        # Step 2: Update bowler types
        results['bowler_types_updated'] = self.update_bowler_types_bulk()
        
        # Step 3: Update derived columns
        crease_updated, ball_updated = self.update_derived_columns_bulk()
        results['crease_combo_updated'] = crease_updated
        results['ball_direction_updated'] = ball_updated
        
        # Get final stats
        final_stats = self.get_update_stats()
        results['final_stats'] = final_stats
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"🎉 Full update completed in {duration}")
        logger.info(f"Final state:")
        logger.info(f"  Striker populated: {final_stats['striker_populated']:,}")
        logger.info(f"  Non-striker populated: {final_stats['non_striker_populated']:,}")
        logger.info(f"  Bowler populated: {final_stats['bowler_type_populated']:,}")
        logger.info(f"  Crease combo populated: {final_stats['crease_combo_populated']:,}")
        logger.info(f"  Ball direction populated: {final_stats['ball_direction_populated']:,}")
        
        return results


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Update delivery columns with bulk operations')
    parser.add_argument('--update-all', action='store_true', help='Update all delivery columns')
    parser.add_argument('--update-batter-types', action='store_true', help='Update only batter types')
    parser.add_argument('--update-bowler-types', action='store_true', help='Update only bowler types')
    parser.add_argument('--update-derived-columns', action='store_true', help='Update only derived columns')
    parser.add_argument('--update-players', nargs='+', help='Update specific players only')
    parser.add_argument('--batch-size', type=int, default=25000, help='Batch size for processing (default: 25000)')
    parser.add_argument('--stats-only', action='store_true', help='Show current statistics only')
    
    args = parser.parse_args()
    
    if not any([args.update_all, args.update_batter_types, args.update_bowler_types, 
                args.update_derived_columns, args.update_players, args.stats_only]):
        print("❌ Please provide one of the update options")
        parser.print_help()
        sys.exit(1)
    
    print("🏏 Starting Delivery Column Updater...")
    print("="*60)
    
    try:
        with DeliveryColumnUpdater(batch_size=args.batch_size) as updater:
            if args.stats_only:
                stats = updater.get_update_stats()
                print(f"\n📊 Current Delivery Column Statistics:")
                print(f"   Total deliveries: {stats['total_deliveries']:,}")
                print(f"   Striker batter_type populated: {stats['striker_populated']:,}")
                print(f"   Non-striker batter_type populated: {stats['non_striker_populated']:,}")
                print(f"   Bowler type populated: {stats['bowler_type_populated']:,}")
                print(f"   Crease combo populated: {stats['crease_combo_populated']:,}")
                print(f"   Ball direction populated: {stats['ball_direction_populated']:,}")
                
            elif args.update_all:
                results = updater.run_full_update()
                print(f"\n✅ Full update completed!")
                
            elif args.update_batter_types:
                updated = updater.update_batter_types_bulk()
                print(f"\n✅ Batter types updated: {updated:,} deliveries")
                
            elif args.update_bowler_types:
                updated = updater.update_bowler_types_bulk()
                print(f"\n✅ Bowler types updated: {updated:,} deliveries")
                
            elif args.update_derived_columns:
                crease, ball = updater.update_derived_columns_bulk()
                print(f"\n✅ Derived columns updated:")
                print(f"   Crease combo: {crease:,} deliveries")
                print(f"   Ball direction: {ball:,} deliveries")
                
            elif args.update_players:
                updated = updater.update_specific_players(args.update_players)
                print(f"\n✅ Updated {updated:,} deliveries for {len(args.update_players)} players")
        
        print(f"\n🎉 Delivery column update completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during update: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()