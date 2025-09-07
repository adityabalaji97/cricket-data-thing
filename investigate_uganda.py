#!/usr/bin/env python3
"""
Quick investigation into Uganda's ELO rating
"""

from database import get_session
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def investigate_uganda():
    """Quick investigation into Uganda's matches and ELO"""
    session = next(get_session())
    
    try:
        # Find all Uganda matches
        result = session.execute(text("""
            SELECT 
                date, team1, team2, winner, competition, venue,
                team1_elo, team2_elo
            FROM matches 
            WHERE team1 = 'Uganda' OR team2 = 'Uganda'
            ORDER BY date
        """)).fetchall()
        
        logger.info(f"=== UGANDA MATCH ANALYSIS ===")
        logger.info(f"Total matches found: {len(result)}")
        
        if len(result) == 0:
            logger.info("No matches found for Uganda!")
            return
        
        logger.info(f"\n{'Date':<12} {'Team1':<20} {'Team2':<20} {'Winner':<20} {'Competition':<15}")
        logger.info("-" * 100)
        
        wins = losses = ties = 0
        opponents = set()
        
        for match in result:
            winner_display = match.winner if match.winner else "No Result"
            logger.info(f"{match.date.strftime('%Y-%m-%d'):<12} {match.team1:<20} {match.team2:<20} {winner_display:<20} {match.competition:<15}")
            
            # Track opponents
            if match.team1 == 'Uganda':
                opponents.add(match.team2)
                if match.winner == 'Uganda':
                    wins += 1
                elif match.winner == match.team2:
                    losses += 1
                else:
                    ties += 1
            else:
                opponents.add(match.team1)
                if match.winner == 'Uganda':
                    wins += 1
                elif match.winner == match.team1:
                    losses += 1
                else:
                    ties += 1
        
        logger.info(f"\n=== UGANDA RECORD ===")
        logger.info(f"Wins: {wins}")
        logger.info(f"Losses: {losses}")
        logger.info(f"Ties/No Results: {ties}")
        logger.info(f"Win Rate: {wins/(wins+losses)*100:.1f}%" if (wins+losses) > 0 else "No completed matches")
        
        logger.info(f"\n=== OPPONENTS FACED ===")
        for opponent in sorted(opponents):
            logger.info(f"  {opponent}")
        
        # Check if Uganda has unusually high ELO in recent matches
        if result:
            latest_match = result[-1]
            if latest_match.team1 == 'Uganda':
                uganda_elo = latest_match.team1_elo
            else:
                uganda_elo = latest_match.team2_elo
            logger.info(f"\nUganda's ELO in latest match: {uganda_elo}")
        
        # Check competition types
        competitions = {}
        for match in result:
            comp = match.competition
            competitions[comp] = competitions.get(comp, 0) + 1
        
        logger.info(f"\n=== COMPETITIONS ===")
        for comp, count in sorted(competitions.items()):
            logger.info(f"  {comp}: {count} matches")
            
    except Exception as e:
        logger.error(f"Error investigating Uganda: {e}")
    finally:
        session.close()

def check_elo_distribution():
    """Check the distribution of ELO ratings"""
    session = next(get_session())
    
    try:
        # Get ELO distribution
        result = session.execute(text("""
            WITH team_ratings AS (
                SELECT 
                    team1 as team,
                    team1_elo as elo
                FROM matches 
                WHERE team1_elo IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    team2 as team,
                    team2_elo as elo
                FROM matches 
                WHERE team2_elo IS NOT NULL
            ),
            latest_ratings AS (
                SELECT 
                    team,
                    elo,
                    ROW_NUMBER() OVER (PARTITION BY team ORDER BY elo DESC) as rn
                FROM team_ratings
            )
            SELECT team, elo
            FROM latest_ratings 
            WHERE rn = 1
            ORDER BY elo DESC
            LIMIT 20
        """)).fetchall()
        
        logger.info(f"\n=== TOP 20 TEAMS BY HIGHEST RECORDED ELO ===")
        for i, (team, elo) in enumerate(result, 1):
            logger.info(f"{i:2d}. {team:<30} {elo}")
            
    except Exception as e:
        logger.error(f"Error checking ELO distribution: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    investigate_uganda()
    check_elo_distribution()
