#!/usr/bin/env python3
"""
Sync From Delivery Details - Creates matches from delivery_details table.

COLUMN MAPPING:
    p_match -> match_id, inns -> innings, bat -> batter, bowl -> bowler,
    team_bat -> batting_team, team_bowl -> bowling_team, match_date -> date

FILTERS OUT: Incomplete matches (where innings 1 doesn't start at over 0)
"""

import logging
from typing import Dict, List, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from tqdm import tqdm
from database import get_database_connection
from models import Match

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DeliveryDetailsSync:
    INTERNATIONAL_COMPETITIONS = ['T20I', 'T20 World Cup', 'ICC', 'World Cup', 'Asia Cup']
    
    def __init__(self):
        self.engine, self.SessionLocal = get_database_connection()
    
    def get_incomplete_match_ids(self, session: Session) -> List[str]:
        """Get match IDs where innings 1 doesn't start at over 0 (incomplete data)"""
        result = session.execute(text('''
            WITH innings_starts AS (
                SELECT p_match, inns, MIN(over) as first_over
                FROM delivery_details
                WHERE p_match IS NOT NULL AND inns = 1
                GROUP BY p_match, inns
            )
            SELECT p_match FROM innings_starts WHERE first_over > 0
        ''')).fetchall()
        return [r[0] for r in result]
    
    def get_missing_match_ids(self, session: Session, limit: Optional[int] = None) -> List[str]:
        """Get match_ids that exist in delivery_details but not in matches.
        EXCLUDES incomplete matches (innings 1 doesn't start at over 0)."""
        query = """
            WITH complete_matches AS (
                -- Only include matches where innings 1 starts at over 0
                SELECT p_match
                FROM delivery_details
                WHERE p_match IS NOT NULL AND inns = 1
                GROUP BY p_match
                HAVING MIN(over) = 0
            )
            SELECT DISTINCT dd.p_match 
            FROM delivery_details dd
            INNER JOIN complete_matches cm ON dd.p_match = cm.p_match
            LEFT JOIN matches m ON dd.p_match = m.id
            WHERE m.id IS NULL
            ORDER BY dd.p_match
        """
        if limit:
            query += f" LIMIT {limit}"
        result = session.execute(text(query))
        return [row[0] for row in result.fetchall()]
    
    def get_match_ids_missing_stats(self, session: Session, limit: Optional[int] = None) -> List[str]:
        """Get match_ids that need stats. EXCLUDES incomplete matches."""
        query = """
            WITH complete_matches AS (
                SELECT p_match
                FROM delivery_details
                WHERE p_match IS NOT NULL AND inns = 1
                GROUP BY p_match
                HAVING MIN(over) = 0
            )
            SELECT DISTINCT dd.p_match
            FROM delivery_details dd
            INNER JOIN complete_matches cm ON dd.p_match = cm.p_match
            LEFT JOIN batting_stats bs ON dd.p_match = bs.match_id
            WHERE bs.match_id IS NULL
            ORDER BY dd.p_match
        """
        if limit:
            query += f" LIMIT {limit}"
        result = session.execute(text(query))
        return [row[0] for row in result.fetchall()]
    
    def check_sync_status(self) -> Dict:
        session = self.SessionLocal()
        try:
            # Total matches in delivery_details
            dd_matches = session.execute(text(
                "SELECT COUNT(DISTINCT p_match) FROM delivery_details WHERE p_match IS NOT NULL"
            )).scalar()
            
            # Complete matches only (innings 1 starts at over 0)
            complete_matches = session.execute(text('''
                SELECT COUNT(DISTINCT p_match)
                FROM delivery_details
                WHERE p_match IS NOT NULL AND inns = 1
                GROUP BY p_match
                HAVING MIN(over) = 0
            ''')).scalar() or 0
            
            # Incomplete matches
            incomplete_count = len(self.get_incomplete_match_ids(session))
            
            matches_count = session.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            missing_matches = len(self.get_missing_match_ids(session))
            missing_stats = len(self.get_match_ids_missing_stats(session))
            sample_missing = self.get_missing_match_ids(session, limit=5)
            
            return {
                'delivery_details_matches': dd_matches,
                'complete_matches': complete_matches,
                'incomplete_matches': incomplete_count,
                'matches_table_count': matches_count,
                'missing_in_matches': missing_matches,
                'missing_batting_stats': missing_stats,
                'sample_missing_ids': sample_missing
            }
        finally:
            session.close()
    
    def extract_match_data_from_dd(self, session: Session, match_id: str) -> Optional[Dict]:
        query = text("""
            SELECT p_match, match_date, ground, country, competition, winner, toss,
                   team_bat, team_bowl, inns, max_balls
            FROM delivery_details
            WHERE p_match = :match_id
            GROUP BY p_match, match_date, ground, country, competition, winner, toss,
                     team_bat, team_bowl, inns, max_balls
            ORDER BY inns
        """)
        rows = session.execute(query, {'match_id': match_id}).fetchall()
        if not rows:
            return None
        
        first_row = rows[0]
        teams = set()
        innings_teams = {}
        
        for row in rows:
            if row.team_bat:
                teams.add(row.team_bat)
            if row.team_bowl:
                teams.add(row.team_bowl)
            if row.team_bat:
                innings_teams[row.inns] = row.team_bat
        
        teams = list(teams)
        if len(teams) < 2:
            logger.warning(f"Match {match_id}: Could not determine both teams")
            return None
        
        team1 = innings_teams.get(1, teams[0])
        team2 = [t for t in teams if t != team1][0]
        
        toss_winner, toss_decision = self._parse_toss_field(first_row.toss, team1, team2)
        
        competition = first_row.competition or ''
        is_international = any(c.lower() in competition.lower() for c in self.INTERNATIONAL_COMPETITIONS)
        match_type = 'international' if is_international else 'league'
        
        max_balls = first_row.max_balls or 120
        overs = max_balls // 6
        
        match_data = {
            'id': match_id,
            'date': first_row.match_date,
            'venue': first_row.ground,
            'city': first_row.country,
            'team1': team1,
            'team2': team2,
            'winner': first_row.winner,
            'toss_winner': toss_winner,
            'toss_decision': toss_decision,
            'competition': first_row.competition,
            'match_type': match_type,
            'overs': overs,
            'balls_per_over': 6,
            'event_name': first_row.competition,
        }
        
        if toss_winner and toss_decision:
            if toss_decision == 'bat':
                match_data['bat_first'] = toss_winner
                match_data['bowl_first'] = team2 if toss_winner == team1 else team1
            else:
                match_data['bowl_first'] = toss_winner
                match_data['bat_first'] = team2 if toss_winner == team1 else team1
            
            match_data['win_toss_win_match'] = (toss_winner == first_row.winner) if first_row.winner else None
            if first_row.winner:
                match_data['won_batting_first'] = match_data.get('bat_first') == first_row.winner
                match_data['won_fielding_first'] = match_data.get('bowl_first') == first_row.winner
        
        return match_data
    
    def _parse_toss_field(self, toss_str: str, team1: str, team2: str) -> Tuple[Optional[str], Optional[str]]:
        if not toss_str:
            return None, None
        toss_str = str(toss_str).strip()
        toss_winner, toss_decision = None, None
        
        if ',' in toss_str:
            parts = toss_str.split(',', 1)
            toss_winner = parts[0].strip()
            if len(parts) > 1:
                decision = parts[1].strip().lower()
                if 'bat' in decision:
                    toss_decision = 'bat'
                elif 'field' in decision or 'bowl' in decision:
                    toss_decision = 'field'
        elif toss_str == team1:
            toss_winner, toss_decision = toss_str, 'bat'
        elif toss_str == team2:
            toss_winner, toss_decision = toss_str, 'field'
        
        return toss_winner, toss_decision
    
    def create_matches_from_dd(self, limit: Optional[int] = None, batch_size: int = 100) -> Dict:
        session = self.SessionLocal()
        stats = {'processed': 0, 'created': 0, 'errors': 0, 'skipped_incomplete': 0}
        
        try:
            missing_ids = self.get_missing_match_ids(session, limit)
            logger.info(f"Found {len(missing_ids)} complete matches to create")
            if not missing_ids:
                return stats
            
            matches_to_insert = []
            for match_id in tqdm(missing_ids, desc="Extracting match data"):
                try:
                    match_data = self.extract_match_data_from_dd(session, match_id)
                    if match_data:
                        matches_to_insert.append(match_data)
                        stats['processed'] += 1
                    else:
                        stats['errors'] += 1
                except Exception as e:
                    logger.error(f"Error extracting match {match_id}: {e}")
                    stats['errors'] += 1
                
                if len(matches_to_insert) >= batch_size:
                    for m in matches_to_insert:
                        session.add(Match(**m))
                    session.flush()
                    stats['created'] += len(matches_to_insert)
                    matches_to_insert = []
            
            if matches_to_insert:
                for m in matches_to_insert:
                    session.add(Match(**m))
                session.flush()
                stats['created'] += len(matches_to_insert)
            
            session.commit()
            return stats
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()


def print_status(status: Dict):
    print("\n" + "=" * 60)
    print("DELIVERY_DETAILS SYNC STATUS")
    print("=" * 60)
    print(f"Total matches in delivery_details: {status['delivery_details_matches']:,}")
    print(f"  ✅ Complete (innings 1 starts at over 0): {status.get('complete_matches', 'N/A')}")
    print(f"  ⚠️  Incomplete (skipped): {status.get('incomplete_matches', 0)}")
    print(f"Records in matches table: {status['matches_table_count']:,}")
    print(f"Missing from matches (to sync): {status['missing_in_matches']:,}")
    print(f"Missing batting_stats: {status['missing_batting_stats']:,}")
    if status['sample_missing_ids']:
        print(f"\nSample missing match IDs: {status['sample_missing_ids'][:5]}")
    print("=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Sync from delivery_details')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--sync-matches', action='store_true')
    parser.add_argument('--sync-stats', action='store_true')
    parser.add_argument('--sync-all', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--confirm', action='store_true')
    args = parser.parse_args()
    
    syncer = DeliveryDetailsSync()
    status = syncer.check_sync_status()
    print_status(status)
    
    if args.check:
        return
    
    if not any([args.sync_matches, args.sync_stats, args.sync_all]):
        print("\nUse --sync-matches, --sync-stats, or --sync-all")
        return
    
    if not args.confirm:
        response = input("\nProceed? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled.")
            return
    
    if args.sync_matches or args.sync_all:
        print("\n🔄 Syncing matches...")
        result = syncer.create_matches_from_dd(limit=args.limit)
        print(f"✅ Created: {result['created']}, Errors: {result['errors']}")
    
    if args.sync_stats or args.sync_all:
        print("\n🔄 Syncing stats...")
        from sync_stats_from_dd import create_stats_from_delivery_details
        result = create_stats_from_delivery_details(limit=args.limit)
        print(f"✅ Batting: {result['batting_created']}, Bowling: {result['bowling_created']}")
    
    print("\n🎉 Done! Run: venue_standardization.py, fix_league_names.py, calculate_missing_elo.py")


if __name__ == "__main__":
    main()
