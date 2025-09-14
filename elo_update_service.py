#!/usr/bin/env python3
"""
ELO Update Service

Modular service for efficient ELO rating calculations that can:
1. Calculate ELO for existing matches without ratings
2. Calculate ELO for newly added matches in chronological order
3. Handle incremental updates without full recalculation
4. Work both standalone and integrated with match loading

Usage Examples:
    # Calculate ELO for all matches missing ratings
    service = ELOUpdateService()
    service.calculate_missing_elo_ratings()
    
    # Calculate ELO for specific new matches
    service.calculate_elo_for_new_matches(['match_id_1', 'match_id_2'])
    
    # Calculate ELO during match loading (incremental)
    service.calculate_elo_for_match_batch(new_match_ids)
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from database import get_session
from models import Match
from elo_calculator import ELOCalculator, normalize_team_name, teams_are_same

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ELOUpdateService:
    """Service for efficient ELO rating updates and calculations"""
    
    def __init__(self, k_factor: int = 32):
        """
        Initialize ELO update service
        
        Args:
            k_factor: ELO K-factor for rating changes (default: 32)
        """
        self.k_factor = k_factor
        self.elo_calculator = ELOCalculator(k_factor=k_factor)
        
    def get_matches_without_elo(self, session: Session, limit: Optional[int] = None) -> List[Match]:
        """
        Get matches that don't have ELO ratings, ordered chronologically
        
        Args:
            session: Database session
            limit: Optional limit on number of matches to return
            
        Returns:
            List of matches without ELO ratings
        """
        query = session.query(Match).filter(
            or_(Match.team1_elo.is_(None), Match.team2_elo.is_(None))
        ).order_by(Match.date, Match.id)
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def get_matches_after_date(self, session: Session, after_date: datetime, 
                              include_missing_elo: bool = True) -> List[Match]:
        """
        Get matches after a specific date that may need ELO recalculation
        
        Args:
            session: Database session
            after_date: Date after which to get matches
            include_missing_elo: Whether to include matches without ELO
            
        Returns:
            List of matches after the specified date
        """
        if include_missing_elo:
            # Get matches after date OR matches without ELO
            matches = session.query(Match).filter(
                or_(
                    Match.date > after_date,
                    Match.team1_elo.is_(None),
                    Match.team2_elo.is_(None)
                )
            ).order_by(Match.date, Match.id).all()
        else:
            # Just matches after date
            matches = session.query(Match).filter(
                Match.date > after_date
            ).order_by(Match.date, Match.id).all()
            
        return matches
    
    def find_earliest_missing_elo_date(self, session: Session) -> Optional[datetime]:
        """
        Find the earliest date where ELO data is missing
        
        Args:
            session: Database session
            
        Returns:
            Earliest date with missing ELO, or None if all matches have ELO
        """
        result = session.execute(text("""
            SELECT MIN(date) 
            FROM matches 
            WHERE team1_elo IS NULL OR team2_elo IS NULL
        """)).scalar()
        
        return result
    
    def calculate_elo_for_chronological_matches(self, matches: List[Match], 
                                              session: Session, 
                                              start_fresh: bool = False) -> Dict[str, int]:
        """
        Calculate ELO ratings for a chronologically ordered list of matches
        
        Args:
            matches: List of matches in chronological order
            session: Database session
            start_fresh: Whether to start with fresh ELO calculator (ignore existing ratings)
            
        Returns:
            Dictionary with statistics about the calculation
        """
        if not matches:
            logger.info("No matches to process")
            return {'processed': 0, 'updated': 0, 'errors': 0}
        
        logger.info(f"Calculating ELO for {len(matches)} matches...")
        logger.info(f"Date range: {matches[0].date} to {matches[-1].date}")
        
        stats = {'processed': 0, 'updated': 0, 'errors': 0}
        updates_to_commit = []
        
        # If not starting fresh, we need to load existing team ratings up to the start date
        if not start_fresh and matches:
            self._load_existing_team_ratings(session, matches[0].date)
        
        for match in matches:
            try:
                # Calculate ELO ratings before this match
                team1_old, team2_old, team1_new, team2_new = self.elo_calculator.update_ratings(
                    match.team1, match.team2, match.winner, match.match_type
                )
                
                # Prepare database update (store pre-match ratings)
                updates_to_commit.append({
                    'match_id': match.id,
                    'team1_elo': team1_old,
                    'team2_elo': team2_old
                })
                
                stats['processed'] += 1
                
                # Log progress every 500 matches
                if stats['processed'] % 500 == 0:
                    logger.info(f"Processed {stats['processed']}/{len(matches)} matches")
                    logger.info(f"Sample: {match.team1} ({team1_old}→{team1_new}) vs {match.team2} ({team2_old}→{team2_new})")
                
                # Commit in batches for performance
                if len(updates_to_commit) >= 1000:
                    batch_updated = self._commit_elo_updates(session, updates_to_commit)
                    stats['updated'] += batch_updated
                    updates_to_commit = []
                    
            except Exception as e:
                logger.error(f"Error processing match {match.id}: {e}")
                stats['errors'] += 1
                continue
        
        # Commit remaining updates
        if updates_to_commit:
            batch_updated = self._commit_elo_updates(session, updates_to_commit)
            stats['updated'] += batch_updated
        
        logger.info(f"ELO calculation complete - Processed: {stats['processed']}, Updated: {stats['updated']}, Errors: {stats['errors']}")
        return stats
    
    def _load_existing_team_ratings(self, session: Session, before_date: datetime) -> None:
        """
        Load existing team ratings from matches before a specific date
        
        Args:
            session: Database session
            before_date: Date before which to load ratings
        """
        logger.info(f"Loading existing team ratings before {before_date}...")
        
        # Simplified approach: Get the latest ELO ratings for each team
        # This gets the most recent match before our cutoff date for each team
        team_ratings = {}
        
        # Get all teams that have matches before the cutoff date with ELO data
        teams_query = session.execute(text("""
            SELECT DISTINCT team1 as team FROM matches 
            WHERE date < :before_date AND team1_elo IS NOT NULL
            UNION 
            SELECT DISTINCT team2 as team FROM matches 
            WHERE date < :before_date AND team2_elo IS NOT NULL
        """), {'before_date': before_date}).fetchall()
        
        teams = [row.team for row in teams_query]
        logger.info(f"Found {len(teams)} teams with ELO history before {before_date}")
        
        loaded_count = 0
        for team in teams:
            # Get the most recent match for this team before cutoff
            latest_match = session.execute(text("""
                SELECT date, team1, team2, team1_elo, team2_elo, winner, match_type
                FROM matches 
                WHERE (team1 = :team OR team2 = :team) 
                AND date < :before_date 
                AND team1_elo IS NOT NULL AND team2_elo IS NOT NULL
                ORDER BY date DESC, id DESC
                LIMIT 1
            """), {'team': team, 'before_date': before_date}).fetchone()
            
            if latest_match:
                # Calculate what the team's ELO would be AFTER this match
                if latest_match.team1 == team:
                    pre_match_elo = latest_match.team1_elo
                    opponent_elo = latest_match.team2_elo
                else:
                    pre_match_elo = latest_match.team2_elo
                    opponent_elo = latest_match.team1_elo
                
                # Calculate the post-match ELO (what we want to start with)
                expected_score = 1 / (1 + 10**((opponent_elo - pre_match_elo) / 400))
                
                if latest_match.winner == team:
                    actual_score = 1.0
                elif latest_match.winner is None:
                    actual_score = 0.5
                else:
                    actual_score = 0.0
                
                elo_change = round(32 * (actual_score - expected_score))
                post_match_elo = pre_match_elo + elo_change
                
                # Store in calculator using normalized name
                normalized_name = normalize_team_name(team)
                self.elo_calculator.team_ratings[normalized_name] = post_match_elo
                loaded_count += 1
                
                if loaded_count <= 10:
                    logger.info(f"Loaded: {team} -> {post_match_elo} (from {latest_match.date})")
        
        logger.info(f"Successfully loaded {loaded_count} existing team ratings")
        if loaded_count > 10:
            logger.info("... (showing first 10 for brevity)")
        
    def _commit_elo_updates(self, session: Session, updates: List[Dict]) -> int:
        """
        Commit ELO updates to database using bulk update
        
        Args:
            session: Database session
            updates: List of update dictionaries
            
        Returns:
            Number of rows updated
        """
        try:
            # Use bulk update for performance
            for update in updates:
                session.execute(
                    text("UPDATE matches SET team1_elo = :team1_elo, team2_elo = :team2_elo WHERE id = :match_id"),
                    update
                )
            session.commit()
            return len(updates)
        except Exception as e:
            session.rollback()
            logger.error(f"Error committing ELO updates: {e}")
            raise
    
    def calculate_missing_elo_ratings(self, batch_size: int = 1000, 
                                    max_matches: Optional[int] = None) -> Dict[str, int]:
        """
        Calculate ELO ratings for all matches that don't have them
        
        Args:
            batch_size: Number of matches to process at once
            max_matches: Maximum number of matches to process (for testing)
            
        Returns:
            Dictionary with processing statistics
        """
        session = next(get_session())
        
        try:
            logger.info("🔍 Finding matches without ELO ratings...")
            
            # Check current status
            total_matches = session.query(Match).count()
            matches_with_elo = session.execute(text("""
                SELECT COUNT(*) FROM matches 
                WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
            """)).scalar()
            
            missing_count = total_matches - matches_with_elo
            logger.info(f"Total matches: {total_matches}")
            logger.info(f"Matches with ELO: {matches_with_elo}")
            logger.info(f"Matches missing ELO: {missing_count}")
            
            if missing_count == 0:
                logger.info("✅ All matches already have ELO ratings!")
                return {'processed': 0, 'updated': 0, 'errors': 0}
            
            # Find earliest date where ELO is missing
            earliest_missing_date = self.find_earliest_missing_elo_date(session)
            logger.info(f"Earliest missing ELO date: {earliest_missing_date}")
            
            # Get all matches from that date forward (to maintain chronological order)
            matches_to_process = self.get_matches_after_date(
                session, 
                earliest_missing_date - timedelta(days=1),  # Start one day before to be safe
                include_missing_elo=True
            )
            
            if max_matches:
                matches_to_process = matches_to_process[:max_matches]
                logger.info(f"Limited to {max_matches} matches for testing")
            
            logger.info(f"Processing {len(matches_to_process)} matches from {earliest_missing_date}")
            
            # Calculate ELO ratings
            stats = self.calculate_elo_for_chronological_matches(
                matches_to_process, session, start_fresh=False
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating missing ELO ratings: {e}")
            raise
        finally:
            session.close()
    
    def calculate_elo_for_new_matches(self, new_match_ids: List[str]) -> Dict[str, int]:
        """
        Calculate ELO ratings for specific new matches
        
        Args:
            new_match_ids: List of match IDs that are newly added
            
        Returns:
            Dictionary with processing statistics
        """
        session = next(get_session())
        
        try:
            logger.info(f"🔍 Calculating ELO for {len(new_match_ids)} new matches...")
            
            # Get the new matches
            new_matches = session.query(Match).filter(
                Match.id.in_(new_match_ids)
            ).order_by(Match.date, Match.id).all()
            
            if not new_matches:
                logger.info("No new matches found")
                return {'processed': 0, 'updated': 0, 'errors': 0}
            
            # Find the earliest new match date
            earliest_new_date = min(match.date for match in new_matches)
            logger.info(f"Earliest new match date: {earliest_new_date}")
            
            # Get all matches from that date forward to maintain chronological order
            all_matches_from_date = session.query(Match).filter(
                Match.date >= earliest_new_date
            ).order_by(Match.date, Match.id).all()
            
            logger.info(f"Need to process {len(all_matches_from_date)} matches to maintain chronological order")
            
            # Calculate ELO ratings
            stats = self.calculate_elo_for_chronological_matches(
                all_matches_from_date, session, start_fresh=False
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating ELO for new matches: {e}")
            raise
        finally:
            session.close()
    
    def calculate_elo_for_match_batch(self, match_ids: List[str], 
                                    optimize_for_recent: bool = True) -> Dict[str, int]:
        """
        Calculate ELO ratings for a batch of matches (optimized for loading process)
        
        Args:
            match_ids: List of match IDs to process
            optimize_for_recent: If True, assume matches are recent and minimize recalculation
            
        Returns:
            Dictionary with processing statistics
        """
        session = next(get_session())
        
        try:
            if not match_ids:
                return {'processed': 0, 'updated': 0, 'errors': 0}
            
            logger.info(f"🔍 Calculating ELO for batch of {len(match_ids)} matches...")
            
            # Get the matches
            matches = session.query(Match).filter(
                Match.id.in_(match_ids)
            ).order_by(Match.date, Match.id).all()
            
            if not matches:
                logger.info("No matches found for batch")
                return {'processed': 0, 'updated': 0, 'errors': 0}
            
            if optimize_for_recent:
                # Check if these are all recent matches (after existing ELO data)
                latest_elo_date = session.execute(text("""
                    SELECT MAX(date) FROM matches 
                    WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
                """)).scalar()
                
                earliest_batch_date = min(match.date for match in matches)
                
                if latest_elo_date and earliest_batch_date >= latest_elo_date:
                    # These are all recent matches, can calculate incrementally
                    logger.info(f"Optimized: batch contains only recent matches after {latest_elo_date}")
                    stats = self.calculate_elo_for_chronological_matches(
                        matches, session, start_fresh=False
                    )
                else:
                    # Some matches are older, need broader recalculation
                    logger.info(f"Need broader recalculation - earliest batch: {earliest_batch_date}, latest ELO: {latest_elo_date}")
                    stats = self.calculate_elo_for_new_matches([m.id for m in matches])
            else:
                # Full chronological recalculation
                stats = self.calculate_elo_for_new_matches([m.id for m in matches])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating ELO for match batch: {e}")
            raise
        finally:
            session.close()
    
    def verify_elo_data(self, sample_size: int = 10) -> Dict[str, any]:
        """
        Verify ELO data quality and show sample calculations
        
        Args:
            sample_size: Number of matches to sample for verification
            
        Returns:
            Dictionary with verification results
        """
        session = next(get_session())
        
        try:
            logger.info("🔍 Verifying ELO data quality...")
            
            # Check completion percentage
            total_matches = session.query(Match).count()
            matches_with_elo = session.execute(text("""
                SELECT COUNT(*) FROM matches 
                WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
            """)).scalar()
            
            completion_pct = (matches_with_elo / total_matches * 100) if total_matches > 0 else 0
            
            # Get sample matches
            sample_matches = session.execute(text("""
                SELECT id, date, team1, team1_elo, team2, team2_elo, winner
                FROM matches 
                WHERE team1_elo IS NOT NULL AND team2_elo IS NOT NULL
                ORDER BY date DESC 
                LIMIT :limit
            """), {'limit': sample_size}).fetchall()
            
            # Check for any obvious data issues
            zero_elo_count = session.execute(text("""
                SELECT COUNT(*) FROM matches 
                WHERE (team1_elo = 0 OR team2_elo = 0) 
                AND (team1_elo IS NOT NULL AND team2_elo IS NOT NULL)
            """)).scalar()
            
            verification_results = {
                'total_matches': total_matches,
                'matches_with_elo': matches_with_elo,
                'completion_percentage': completion_pct,
                'zero_elo_count': zero_elo_count,
                'sample_matches': [dict(match) for match in sample_matches]
            }
            
            logger.info(f"ELO completion: {completion_pct:.1f}% ({matches_with_elo}/{total_matches})")
            logger.info(f"Matches with zero ELO: {zero_elo_count}")
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Error verifying ELO data: {e}")
            raise
        finally:
            session.close()


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ELO Update Service - Calculate missing ELO ratings')
    parser.add_argument('--calculate-missing', action='store_true',
                       help='Calculate ELO for all matches missing ratings')
    parser.add_argument('--verify', action='store_true',
                       help='Verify ELO data quality')
    parser.add_argument('--match-ids', nargs='+',
                       help='Calculate ELO for specific match IDs')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for processing (default: 1000)')
    parser.add_argument('--max-matches', type=int,
                       help='Maximum number of matches to process (for testing)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes will be made")
        # For dry run, we'd need to modify the service to not commit changes
        logger.warning("Dry run not fully implemented yet")
        return
    
    service = ELOUpdateService()
    
    try:
        if args.verify:
            logger.info("🔍 Verifying ELO data...")
            results = service.verify_elo_data(sample_size=20)
            
            print(f"\n📊 ELO Data Verification Results:")
            print(f"  Total matches: {results['total_matches']}")
            print(f"  Matches with ELO: {results['matches_with_elo']}")
            print(f"  Completion: {results['completion_percentage']:.1f}%")
            print(f"  Zero ELO issues: {results['zero_elo_count']}")
            
            if results['sample_matches']:
                print(f"\n📋 Sample Recent Matches:")
                print(f"{'Date':<12} {'Team1':<15} {'ELO1':<5} {'Team2':<15} {'ELO2':<5} {'Winner':<15}")
                print("-" * 80)
                for match in results['sample_matches'][:10]:
                    winner = match['winner'] or 'Tie/NR'
                    print(f"{match['date'].strftime('%Y-%m-%d'):<12} {match['team1']:<15} {match['team1_elo']:<5} {match['team2']:<15} {match['team2_elo']:<5} {winner:<15}")
        
        elif args.calculate_missing:
            logger.info("🚀 Calculating missing ELO ratings...")
            stats = service.calculate_missing_elo_ratings(
                batch_size=args.batch_size,
                max_matches=args.max_matches
            )
            
            print(f"\n✅ ELO Calculation Complete!")
            print(f"  Processed: {stats['processed']} matches")
            print(f"  Updated: {stats['updated']} database records")
            print(f"  Errors: {stats['errors']}")
        
        elif args.match_ids:
            logger.info(f"🚀 Calculating ELO for {len(args.match_ids)} specific matches...")
            stats = service.calculate_elo_for_new_matches(args.match_ids)
            
            print(f"\n✅ ELO Calculation Complete!")
            print(f"  Processed: {stats['processed']} matches")
            print(f"  Updated: {stats['updated']} database records")
            print(f"  Errors: {stats['errors']}")
        
        else:
            print("Please specify an action: --calculate-missing, --verify, or --match-ids")
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Error in ELO update service: {e}")
        print(f"❌ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
