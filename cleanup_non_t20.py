#!/usr/bin/env python3
"""
Cleanup Non-T20 Matches

Remove matches that are not T20 format based on:
1. Number of deliveries > 260 (T20 max is ~240 deliveries)
2. match_type field in JSON (if available)

This script will:
- Identify non-T20 matches
- Show summary of what will be deleted
- Delete matches and their deliveries
- Report final cleanup results
"""

import json
import os
from pathlib import Path
from sqlalchemy import text
from database import get_database_connection
from models import Match, Delivery
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NonT20Cleaner:
    """Clean up non-T20 matches from database"""
    
    def __init__(self, delivery_threshold: int = 300):
        """
        Initialize cleaner
        
        Args:
            delivery_threshold: Max deliveries for T20 (default 260)
        """
        self.delivery_threshold = delivery_threshold
        self.engine, self.SessionLocal = get_database_connection()
    
    def identify_matches_to_delete(self) -> dict:
        """
        Identify matches that should be deleted
        
        Returns:
            Dictionary with match info and deletion reasons
        """
        session = self.SessionLocal()
        
        try:
            # Query matches with delivery counts
            query = text("""
                SELECT 
                    m.id,
                    m.competition,
                    m.match_type,
                    m.team1,
                    m.team2,
                    m.date,
                    COUNT(d.id) as delivery_count
                FROM matches m
                LEFT JOIN deliveries d ON m.id = d.match_id
                GROUP BY m.id, m.competition, m.match_type, m.team1, m.team2, m.date
                HAVING COUNT(d.id) > :threshold
                ORDER BY COUNT(d.id) DESC
            """)
            
            result = session.execute(query, {"threshold": self.delivery_threshold})
            
            matches_to_delete = []
            total_deliveries_to_delete = 0
            
            for row in result:
                match_info = {
                    'match_id': row.id,
                    'competition': row.competition,
                    'match_type': row.match_type,
                    'team1': row.team1,
                    'team2': row.team2,
                    'date': row.date,
                    'delivery_count': row.delivery_count,
                    'reason': f'Too many deliveries ({row.delivery_count} > {self.delivery_threshold})'
                }
                matches_to_delete.append(match_info)
                total_deliveries_to_delete += row.delivery_count
            
            logger.info(f"Found {len(matches_to_delete)} matches to delete")
            logger.info(f"Total deliveries to delete: {total_deliveries_to_delete:,}")
            
            return {
                'matches': matches_to_delete,
                'total_matches': len(matches_to_delete),
                'total_deliveries': total_deliveries_to_delete
            }
            
        finally:
            session.close()
    
    def show_deletion_summary(self, deletion_info: dict) -> None:
        """Show summary of what will be deleted"""
        matches = deletion_info['matches']
        
        print(f"\n🗑️  NON-T20 MATCHES TO DELETE")
        print("=" * 80)
        print(f"Total matches to delete: {deletion_info['total_matches']}")
        print(f"Total deliveries to delete: {deletion_info['total_deliveries']:,}")
        print()
        
        # Group by competition for better overview
        by_competition = {}
        for match in matches:
            comp = match['competition'] or 'Unknown'
            if comp not in by_competition:
                by_competition[comp] = []
            by_competition[comp].append(match)
        
        for competition, comp_matches in by_competition.items():
            total_deliveries = sum(m['delivery_count'] for m in comp_matches)
            print(f"📋 {competition}: {len(comp_matches)} matches ({total_deliveries:,} deliveries)")
            
            # Show top 5 matches by delivery count
            sorted_matches = sorted(comp_matches, key=lambda x: x['delivery_count'], reverse=True)
            for match in sorted_matches[:5]:
                print(f"   - {match['match_id']}: {match['team1']} vs {match['team2']} "
                      f"({match['delivery_count']} deliveries) - {match['date']}")
            
            if len(comp_matches) > 5:
                print(f"   ... and {len(comp_matches) - 5} more matches")
            print()
    
    def delete_matches(self, deletion_info: dict, confirm: bool = False) -> dict:
        """
        Delete the identified matches and their deliveries
        
        Args:
            deletion_info: Info about matches to delete
            confirm: Whether to actually perform deletion
            
        Returns:
            Deletion results
        """
        if not confirm:
            print("❌ Deletion not confirmed. Use --confirm flag to actually delete.")
            return {'deleted_matches': 0, 'deleted_deliveries': 0}
        
        session = self.SessionLocal()
        match_ids = [m['match_id'] for m in deletion_info['matches']]
        
        try:
            logger.info(f"Starting deletion of {len(match_ids)} matches...")
            
            # Delete deliveries first (foreign key constraint)
            deliveries_deleted = session.execute(
                text("DELETE FROM deliveries WHERE match_id = ANY(:match_ids)"),
                {"match_ids": match_ids}
            ).rowcount
            
            # Delete matches
            matches_deleted = session.execute(
                text("DELETE FROM matches WHERE id = ANY(:match_ids)"),
                {"match_ids": match_ids}
            ).rowcount
            
            # Commit the transaction
            session.commit()
            
            logger.info(f"✅ Successfully deleted {matches_deleted} matches and {deliveries_deleted:,} deliveries")
            
            return {
                'deleted_matches': matches_deleted,
                'deleted_deliveries': deliveries_deleted
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error during deletion: {e}")
            raise
        finally:
            session.close()
    
    def get_database_stats(self) -> dict:
        """Get current database statistics"""
        session = self.SessionLocal()
        
        try:
            # Get match and delivery counts
            stats_query = text("""
                SELECT 
                    COUNT(DISTINCT m.id) as total_matches,
                    COUNT(d.id) as total_deliveries,
                    COUNT(DISTINCT m.id) FILTER (WHERE m.match_type = 'league') as league_matches,
                    COUNT(DISTINCT m.id) FILTER (WHERE m.match_type = 'international') as international_matches,
                    AVG(delivery_counts.delivery_count) as avg_deliveries_per_match,
                    MAX(delivery_counts.delivery_count) as max_deliveries_per_match,
                    MIN(delivery_counts.delivery_count) as min_deliveries_per_match
                FROM matches m
                LEFT JOIN deliveries d ON m.id = d.match_id
                LEFT JOIN (
                    SELECT match_id, COUNT(*) as delivery_count
                    FROM deliveries
                    GROUP BY match_id
                ) delivery_counts ON m.id = delivery_counts.match_id
            """)
            
            result = session.execute(stats_query).fetchone()
            
            return {
                'total_matches': result.total_matches,
                'total_deliveries': result.total_deliveries,
                'league_matches': result.league_matches,
                'international_matches': result.international_matches,
                'avg_deliveries_per_match': round(result.avg_deliveries_per_match or 0, 1),
                'max_deliveries_per_match': result.max_deliveries_per_match or 0,
                'min_deliveries_per_match': result.min_deliveries_per_match or 0
            }
            
        finally:
            session.close()
    
    def run_cleanup(self, confirm: bool = False) -> dict:
        """
        Run the complete cleanup process
        
        Args:
            confirm: Whether to actually perform deletion
            
        Returns:
            Cleanup results
        """
        logger.info("🚀 Starting non-T20 match cleanup process...")
        
        # Get initial stats
        initial_stats = self.get_database_stats()
        logger.info(f"Initial database state:")
        logger.info(f"  Total matches: {initial_stats['total_matches']:,}")
        logger.info(f"  Total deliveries: {initial_stats['total_deliveries']:,}")
        logger.info(f"  Average deliveries per match: {initial_stats['avg_deliveries_per_match']}")
        logger.info(f"  Max deliveries per match: {initial_stats['max_deliveries_per_match']}")
        
        # Identify matches to delete
        deletion_info = self.identify_matches_to_delete()
        
        if deletion_info['total_matches'] == 0:
            logger.info("🎉 No non-T20 matches found! Database is already clean.")
            return {'status': 'clean', 'initial_stats': initial_stats}
        
        # Show summary
        self.show_deletion_summary(deletion_info)
        
        # Perform deletion if confirmed
        deletion_results = self.delete_matches(deletion_info, confirm)
        
        # Get final stats if deletion was performed
        final_stats = None
        if confirm and deletion_results['deleted_matches'] > 0:
            final_stats = self.get_database_stats()
            logger.info(f"\nFinal database state:")
            logger.info(f"  Total matches: {final_stats['total_matches']:,}")
            logger.info(f"  Total deliveries: {final_stats['total_deliveries']:,}")
            logger.info(f"  Average deliveries per match: {final_stats['avg_deliveries_per_match']}")
            logger.info(f"  Max deliveries per match: {final_stats['max_deliveries_per_match']}")
        
        return {
            'status': 'completed' if confirm else 'preview',
            'initial_stats': initial_stats,
            'deletion_info': deletion_info,
            'deletion_results': deletion_results,
            'final_stats': final_stats
        }


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up non-T20 matches from database')
    parser.add_argument('--threshold', type=int, default=300,
                       help='Maximum deliveries for T20 matches (default: 260)')
    parser.add_argument('--confirm', action='store_true',
                       help='Actually perform deletion (without this, just shows preview)')
    parser.add_argument('--stats-only', action='store_true',
                       help='Just show database statistics')
    
    args = parser.parse_args()
    
    print("🏏 Non-T20 Match Cleanup Tool")
    print("=" * 50)
    
    try:
        cleaner = NonT20Cleaner(delivery_threshold=args.threshold)
        
        if args.stats_only:
            stats = cleaner.get_database_stats()
            print(f"\n📊 Current Database Statistics:")
            print(f"   Total matches: {stats['total_matches']:,}")
            print(f"   Total deliveries: {stats['total_deliveries']:,}")
            print(f"   League matches: {stats['league_matches']:,}")
            print(f"   International matches: {stats['international_matches']:,}")
            print(f"   Average deliveries per match: {stats['avg_deliveries_per_match']}")
            print(f"   Max deliveries per match: {stats['max_deliveries_per_match']}")
            print(f"   Min deliveries per match: {stats['min_deliveries_per_match']}")
            return
        
        # Run cleanup process
        results = cleaner.run_cleanup(confirm=args.confirm)
        
        if results['status'] == 'clean':
            print("\n🎉 Database is already clean!")
        elif results['status'] == 'preview':
            print(f"\n👀 PREVIEW MODE - No changes made")
            print(f"   Run with --confirm to actually delete these matches")
        else:
            print(f"\n✅ CLEANUP COMPLETED")
            print(f"   Deleted matches: {results['deletion_results']['deleted_matches']}")
            print(f"   Deleted deliveries: {results['deletion_results']['deleted_deliveries']:,}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
