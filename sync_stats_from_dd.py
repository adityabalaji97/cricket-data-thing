#!/usr/bin/env python3
"""
Sync Stats from Delivery Details - Creates batting_stats/bowling_stats.

COLUMN MAPPING:
    p_match -> match_id, inns -> innings, bat -> batter, bowl -> bowler,
    team_bat -> batting_team, team_bowl -> bowling_team

FILTERS OUT: Incomplete matches (where innings 1 doesn't start at over 0)
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from tqdm import tqdm
from database import get_database_connection
from models import BattingStats, BowlingStats
from fantasy_points_v2 import FantasyPointsCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StatsFromDeliveryDetails:
    POWERPLAY_END = 6
    MIDDLE_END = 15
    BOWLER_WICKETS = ['bowled', 'caught', 'lbw', 'caught and bowled', 'stumped', 'hit wicket']
    
    def __init__(self):
        self.engine, self.SessionLocal = get_database_connection()
        self.fantasy_calculator = FantasyPointsCalculator()
    
    def get_matches_needing_stats(self, session: Session, limit: Optional[int] = None) -> List[str]:
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
            INNER JOIN matches m ON dd.p_match = m.id
            LEFT JOIN batting_stats bs ON dd.p_match = bs.match_id
            WHERE bs.match_id IS NULL
            ORDER BY dd.p_match
        """
        if limit:
            query += f" LIMIT {limit}"
        result = session.execute(text(query))
        return [row[0] for row in result.fetchall()]
    
    def get_match_deliveries(self, session: Session, match_id: str) -> List[Dict]:
        query = text("""
            SELECT p_match as match_id, inns as innings, over, ball,
                   bat as batter, bowl as bowler,
                   team_bat as batting_team, team_bowl as bowling_team,
                   score, outcome, out, dismissal, noball, wide, byes, legbyes
            FROM delivery_details
            WHERE p_match = :match_id
            ORDER BY inns, over, ball
        """)
        result = session.execute(query, {'match_id': match_id})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def calculate_batting_stats(self, match_id: str, innings: int, batter: str, deliveries: List[Dict]) -> BattingStats:
        batter_dels = [d for d in deliveries if d['innings'] == innings and d['batter'] == batter]
        if not batter_dels:
            return None
        
        stats = BattingStats(
            match_id=match_id, innings=innings, striker=batter,
            batting_team=batter_dels[0]['batting_team']
        )
        
        stats.runs = sum(d['score'] or 0 for d in batter_dels)
        stats.balls_faced = len([d for d in batter_dels if not d['wide']])
        stats.wickets = sum(1 for d in batter_dels if d['out'])
        stats.dots = sum(1 for d in batter_dels if (d['score'] or 0) == 0 and not d['wide'])
        stats.ones = sum(1 for d in batter_dels if (d['score'] or 0) == 1)
        stats.twos = sum(1 for d in batter_dels if (d['score'] or 0) == 2)
        stats.threes = sum(1 for d in batter_dels if (d['score'] or 0) == 3)
        stats.fours = sum(1 for d in batter_dels if (d['score'] or 0) == 4)
        stats.sixes = sum(1 for d in batter_dels if (d['score'] or 0) == 6)
        
        if stats.balls_faced > 0:
            stats.strike_rate = (stats.runs * 100.0) / stats.balls_faced
        
        # Phase stats
        for phase, (start, end) in [('pp', (0, 6)), ('middle', (6, 15)), ('death', (15, 99))]:
            phase_dels = [d for d in batter_dels if start <= d['over'] < end]
            setattr(stats, f'{phase}_runs', sum(d['score'] or 0 for d in phase_dels))
            balls = len([d for d in phase_dels if not d['wide']])
            setattr(stats, f'{phase}_balls', balls)
            setattr(stats, f'{phase}_dots', sum(1 for d in phase_dels if (d['score'] or 0) == 0 and not d['wide']))
            setattr(stats, f'{phase}_wickets', sum(1 for d in phase_dels if d['out']))
            setattr(stats, f'{phase}_boundaries', sum(1 for d in phase_dels if (d['score'] or 0) in [4, 6]))
            if balls > 0:
                setattr(stats, f'{phase}_strike_rate', (getattr(stats, f'{phase}_runs') * 100.0) / balls)
        
        # Batting position - based on entry order
        innings_dels = [d for d in deliveries if d['innings'] == innings]
        first_ball = min(batter_dels, key=lambda x: (x['over'], x['ball']))
        
        # Count unique batters who batted before this one
        prior_batters = set()
        for d in innings_dels:
            if (d['over'], d['ball']) < (first_ball['over'], first_ball['ball']):
                prior_batters.add(d['batter'])
        stats.batting_position = len(prior_batters) + 1
        
        # Entry point
        stats.entry_overs = first_ball['over'] + (first_ball['ball'] / 6.0)
        prior_dels = [d for d in innings_dels 
                      if (d['over'], d['ball']) < (first_ball['over'], first_ball['ball'])]
        stats.entry_runs = sum(d['score'] or 0 for d in prior_dels)
        stats.entry_balls = len([d for d in prior_dels if not d['wide']])
        
        # Team comparison
        other_dels = [d for d in innings_dels if d['batter'] != batter]
        stats.team_runs_excl_batter = sum(d['score'] or 0 for d in other_dels)
        stats.team_balls_excl_batter = len([d for d in other_dels if not d['wide']])
        if stats.team_balls_excl_batter > 0:
            stats.team_sr_excl_batter = (stats.team_runs_excl_batter * 100.0) / stats.team_balls_excl_batter
            if stats.strike_rate:
                stats.sr_diff = stats.strike_rate - stats.team_sr_excl_batter
        
        stats.fantasy_points = self.fantasy_calculator.calculate_batting_points(stats)
        return stats
    
    def calculate_bowling_stats(self, match_id: str, innings: int, bowler: str, deliveries: List[Dict]) -> BowlingStats:
        bowler_dels = [d for d in deliveries if d['innings'] == innings and d['bowler'] == bowler]
        if not bowler_dels:
            return None
        
        stats = BowlingStats(
            match_id=match_id, innings=innings, bowler=bowler,
            bowling_team=bowler_dels[0]['bowling_team']
        )
        
        legal_balls = len([d for d in bowler_dels if not d['wide'] and not d['noball']])
        stats.overs = legal_balls / 6
        stats.runs_conceded = sum((d['score'] or 0) + (d['wide'] or 0) + (d['noball'] or 0) for d in bowler_dels)
        stats.wickets = sum(1 for d in bowler_dels if d['out'] and d['dismissal'] and 
                          d['dismissal'].lower() in [w.lower() for w in self.BOWLER_WICKETS])
        stats.dots = sum(1 for d in bowler_dels if (d['score'] or 0) == 0 and not d['wide'] and not d['noball'])
        stats.fours_conceded = sum(1 for d in bowler_dels if (d['score'] or 0) == 4)
        stats.sixes_conceded = sum(1 for d in bowler_dels if (d['score'] or 0) == 6)
        stats.extras = sum((d['wide'] or 0) + (d['noball'] or 0) for d in bowler_dels)
        
        if stats.overs > 0:
            stats.economy = stats.runs_conceded / stats.overs
        
        # Bowling order - based on when they first bowled
        innings_dels = [d for d in deliveries if d['innings'] == innings]
        first_ball = min(bowler_dels, key=lambda x: (x['over'], x['ball']))
        
        prior_bowlers = set()
        for d in innings_dels:
            if (d['over'], d['ball']) < (first_ball['over'], first_ball['ball']):
                prior_bowlers.add(d['bowler'])
        stats.bowling_position = len(prior_bowlers) + 1
        
        # Phase stats
        for phase, (start, end) in [('pp', (0, 6)), ('middle', (6, 15)), ('death', (15, 99))]:
            phase_dels = [d for d in bowler_dels if start <= d['over'] < end]
            legal = len([d for d in phase_dels if not d['wide'] and not d['noball']])
            setattr(stats, f'{phase}_overs', legal / 6)
            runs = sum((d['score'] or 0) + (d['wide'] or 0) + (d['noball'] or 0) for d in phase_dels)
            setattr(stats, f'{phase}_runs', runs)
            setattr(stats, f'{phase}_wickets', sum(1 for d in phase_dels if d['out'] and d['dismissal'] and 
                          d['dismissal'].lower() in [w.lower() for w in self.BOWLER_WICKETS]))
            setattr(stats, f'{phase}_dots', sum(1 for d in phase_dels if (d['score'] or 0) == 0 and not d['wide'] and not d['noball']))
            setattr(stats, f'{phase}_boundaries', sum(1 for d in phase_dels if (d['score'] or 0) in [4, 6]))
            if legal > 0:
                setattr(stats, f'{phase}_economy', runs / (legal / 6))
        
        # Team comparison
        other_dels = [d for d in innings_dels if d['bowler'] != bowler]
        stats.team_runs_excl_bowler = sum((d['score'] or 0) + (d['wide'] or 0) + (d['noball'] or 0) for d in other_dels)
        other_legal = len([d for d in other_dels if not d['wide'] and not d['noball']])
        stats.team_overs_excl_bowler = other_legal / 6
        if stats.team_overs_excl_bowler > 0:
            stats.team_economy_excl_bowler = stats.team_runs_excl_bowler / stats.team_overs_excl_bowler
            if stats.economy:
                stats.economy_diff = stats.economy - stats.team_economy_excl_bowler
        
        stats.fantasy_points = self.fantasy_calculator.calculate_bowling_points(stats)
        return stats
    
    def process_match_stats(self, session: Session, match_id: str) -> Dict:
        deliveries = self.get_match_deliveries(session, match_id)
        if not deliveries:
            return {'batting': 0, 'bowling': 0}
        
        batting_count, bowling_count = 0, 0
        
        for innings in [1, 2]:
            innings_dels = [d for d in deliveries if d['innings'] == innings]
            if not innings_dels:
                continue
            
            batters = set(d['batter'] for d in innings_dels if d['batter'])
            bowlers = set(d['bowler'] for d in innings_dels if d['bowler'])
            
            for batter in batters:
                try:
                    bat_stats = self.calculate_batting_stats(match_id, innings, batter, deliveries)
                    if bat_stats:
                        session.add(bat_stats)
                        batting_count += 1
                except Exception as e:
                    logger.warning(f"Batting stats error {batter}: {e}")
            
            for bowler in bowlers:
                try:
                    bowl_stats = self.calculate_bowling_stats(match_id, innings, bowler, deliveries)
                    if bowl_stats:
                        session.add(bowl_stats)
                        bowling_count += 1
                except Exception as e:
                    logger.warning(f"Bowling stats error {bowler}: {e}")
        
        return {'batting': batting_count, 'bowling': bowling_count}


def create_stats_from_delivery_details(limit: Optional[int] = None, batch_size: int = 50) -> Dict:
    processor = StatsFromDeliveryDetails()
    session = processor.SessionLocal()
    stats = {'matches_processed': 0, 'batting_created': 0, 'bowling_created': 0, 'errors': 0}
    
    try:
        match_ids = processor.get_matches_needing_stats(session, limit)
        logger.info(f"Found {len(match_ids)} complete matches needing stats")
        
        for i, match_id in enumerate(tqdm(match_ids, desc="Processing stats")):
            try:
                result = processor.process_match_stats(session, match_id)
                stats['batting_created'] += result['batting']
                stats['bowling_created'] += result['bowling']
                stats['matches_processed'] += 1
                if (i + 1) % batch_size == 0:
                    session.commit()
            except Exception as e:
                logger.error(f"Error {match_id}: {e}")
                stats['errors'] += 1
                session.rollback()
        
        session.commit()
        return stats
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    
    result = create_stats_from_delivery_details(limit=args.limit)
    print(f"\n✅ Done! Batting: {result['batting_created']}, Bowling: {result['bowling_created']}")
