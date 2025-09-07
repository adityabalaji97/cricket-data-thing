#!/usr/bin/env python3
"""
Test the new tiered ELO starting system
"""

from elo_calculator import get_starting_elo, normalize_team_name
from models import INTERNATIONAL_TEAMS_RANKED
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tiered_elo_system():
    """Test that the tiered ELO starting system works correctly"""
    
    logger.info("=== TESTING TIERED ELO STARTING SYSTEM ===")
    
    # Test Top 10 teams (should get 1500)
    logger.info("\n--- TOP 10 TEAMS (Expected: 1500 ELO) ---")
    top_10 = INTERNATIONAL_TEAMS_RANKED[:10]
    for i, team in enumerate(top_10, 1):
        elo = get_starting_elo(team, is_international=True)
        status = "✓" if elo == 1500 else "✗"
        logger.info(f"{i:2d}. {team:<20} -> {elo} {status}")
    
    # Test Teams 11-20 (should get 1400)
    logger.info("\n--- TEAMS 11-20 (Expected: 1400 ELO) ---")
    teams_11_20 = INTERNATIONAL_TEAMS_RANKED[10:20]
    for i, team in enumerate(teams_11_20, 11):
        elo = get_starting_elo(team, is_international=True)
        status = "✓" if elo == 1400 else "✗"
        logger.info(f"{i:2d}. {team:<20} -> {elo} {status}")
    
    # Test unranked international teams (should get 1300)
    logger.info("\n--- UNRANKED INTERNATIONAL TEAMS (Expected: 1300 ELO) ---")
    unranked_teams = ["Uganda", "Spain", "Bahrain", "Austria", "Canada", "Jersey", "Japan"]
    for team in unranked_teams:
        elo = get_starting_elo(team, is_international=True)
        status = "✓" if elo == 1300 else "✗"
        logger.info(f"    {team:<20} -> {elo} {status}")
    
    # Test league teams (should get 1500)
    logger.info("\n--- LEAGUE TEAMS (Expected: 1500 ELO) ---")
    league_teams = ["Mumbai Indians", "Chennai Super Kings", "Perth Scorchers", "Comilla Victorians"]
    for team in league_teams:
        elo = get_starting_elo(team, is_international=False)
        status = "✓" if elo == 1500 else "✗"
        logger.info(f"    {team:<20} -> {elo} {status}")
    
    # Test team name normalization with ranking
    logger.info("\n--- TEAM NAME NORMALIZATION TEST ---")
    test_cases = [
        ("Royal Challengers Bangalore", False, 1500),  # League team
        ("Royal Challengers Bengaluru", False, 1500),   # League team (different name, same team)
        ("India", True, 1500),                          # Top 10 international
        ("Papua New Guinea", True, 1400),               # Ranked 11-20
        ("Uganda", True, 1300),                         # Unranked international
    ]
    
    for team_name, is_international, expected_elo in test_cases:
        normalized = normalize_team_name(team_name)
        elo = get_starting_elo(team_name, is_international)
        status = "✓" if elo == expected_elo else "✗"
        context = "international" if is_international else "league"
        logger.info(f"    {team_name:<25} ({context}) -> {normalized:<15} -> {elo} {status}")

def verify_ranking_list():
    """Verify our ranking list looks correct"""
    logger.info("\n=== CURRENT INTERNATIONAL TEAMS RANKING ===")
    
    logger.info("Top 10 (1500 ELO):")
    for i, team in enumerate(INTERNATIONAL_TEAMS_RANKED[:10], 1):
        logger.info(f"  {i:2d}. {team}")
    
    logger.info("\nTeams 11-20 (1400 ELO):")
    for i, team in enumerate(INTERNATIONAL_TEAMS_RANKED[10:20], 11):
        logger.info(f"  {i:2d}. {team}")
    
    logger.info(f"\nAll other international teams get 1300 ELO")

if __name__ == "__main__":
    verify_ranking_list()
    test_tiered_elo_system()
