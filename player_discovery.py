#!/usr/bin/env python3
"""
Player Discovery Service

Automatically discovers missing players from JSON files and creates
placeholder entries in the players table.
"""

import json
import os
from pathlib import Path
from typing import Dict, Set, List, Optional, NamedTuple
from dataclasses import dataclass
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_database_connection
from models import Player, teams_mapping, INTERNATIONAL_TEAMS_RANKED
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PlayerInfo:
    """Information discovered about a player from JSON files"""
    name: str
    appears_as: List[str]  # ['batter', 'bowler', 'both']
    team_countries: Set[str]  # Teams they've played for
    match_count: int
    ball_count: int
    likely_nationality: Optional[str] = None

class PlayerDiscoveryService:
    """Service to discover and create missing player entries"""
    
    def __init__(self):
        """Initialize the player discovery service"""
        self.engine, self.SessionLocal = get_database_connection()
        
        # Create nationality inference mappings
        self.team_to_nationality = self._create_team_nationality_mapping()
        
    def _create_team_nationality_mapping(self) -> Dict[str, str]:
        """Create mapping from team names to nationalities (international teams only)"""
        mapping = {}
        
        # International teams only (direct mapping)
        for team in INTERNATIONAL_TEAMS_RANKED:
            mapping[team] = team
            
        return mapping
    
    def scan_json_files_for_players(self, json_directory: str) -> Dict[str, PlayerInfo]:
        """
        Scan all JSON files in directory and extract player information
        
        Args:
            json_directory: Path to directory containing JSON match files
            
        Returns:
            Dictionary mapping player names to PlayerInfo objects
        """
        logger.info(f"Scanning JSON files in {json_directory} for players...")
        
        discovered_players = defaultdict(lambda: PlayerInfo(
            name="", appears_as=[], team_countries=set(), 
            match_count=0, ball_count=0
        ))
        
        json_path = Path(json_directory)
        if not json_path.exists():
            raise ValueError(f"Directory {json_directory} does not exist")
            
        json_files = list(json_path.glob('*.json'))
        logger.info(f"Found {len(json_files)} JSON files to scan")
        
        for json_file in json_files:
            try:
                self._scan_single_file(json_file, discovered_players)
            except Exception as e:
                logger.error(f"Error scanning {json_file}: {e}")
                continue
                
        # Convert defaultdict to regular dict and infer nationalities
        result = {}
        for player_name, info in discovered_players.items():
            info.name = player_name
            info.likely_nationality = self._infer_nationality(info.team_countries)
            result[player_name] = info
            
        logger.info(f"Discovered {len(result)} unique players across all files")
        return result
    
    def _scan_single_file(self, json_file: Path, discovered_players: defaultdict) -> None:
        """Scan a single JSON file and update discovered_players"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            # Get team information
            teams = data['info']['teams']
            
            # Track players by role in this match
            match_batters = set()
            match_bowlers = set()
            ball_count = 0
            
            # Scan all deliveries
            for innings in data['innings']:
                batting_team = innings['team']
                bowling_team = teams[0] if batting_team == teams[1] else teams[1]
                
                for over in innings['overs']:
                    for ball in over['deliveries']:
                        ball_count += 1
                        
                        # Extract players from delivery
                        batter = ball['batter']
                        non_striker = ball['non_striker'] 
                        bowler = ball['bowler']
                        
                        # Update player info
                        match_batters.update([batter, non_striker])
                        match_bowlers.add(bowler)
                        
                        # Track team associations
                        discovered_players[batter].team_countries.add(batting_team)
                        discovered_players[non_striker].team_countries.add(batting_team)
                        discovered_players[bowler].team_countries.add(bowling_team)
                        
                        # Update ball counts
                        discovered_players[batter].ball_count += 1
                        discovered_players[non_striker].ball_count += 1
                        discovered_players[bowler].ball_count += 1
            
            # Update match counts and roles
            for player in match_batters:
                discovered_players[player].match_count += 1
                if 'batter' not in discovered_players[player].appears_as:
                    discovered_players[player].appears_as.append('batter')
                    
            for player in match_bowlers:
                discovered_players[player].match_count += 1
                if 'bowler' not in discovered_players[player].appears_as:
                    discovered_players[player].appears_as.append('bowler')
                    
            # Mark players who both bat and bowl
            for player in match_batters.intersection(match_bowlers):
                if 'both' not in discovered_players[player].appears_as:
                    discovered_players[player].appears_as.append('both')
                    
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            raise
    
    def _infer_nationality(self, team_countries: Set[str]) -> Optional[str]:
        """Infer player nationality based on teams they've played for (international teams only)"""
        if not team_countries:
            return None
            
        # Check for international teams only (highest confidence)
        for team in team_countries:
            if team in INTERNATIONAL_TEAMS_RANKED:
                return team
                
        # No international team found - return None rather than guessing from league teams
        return None
    
    def find_missing_players(self, discovered_players: Dict[str, PlayerInfo]) -> Dict[str, PlayerInfo]:
        """
        Compare discovered players with database and find missing ones
        
        Args:
            discovered_players: Dictionary of players found in JSON files
            
        Returns:
            Dictionary of players that don't exist in the database
        """
        logger.info("Checking for missing players in database...")
        
        session = self.SessionLocal()
        try:
            # Get all existing player names from database
            existing_names = session.query(Player.name).all()
            existing_names_set = {name[0] for name in existing_names}
            
            logger.info(f"Found {len(existing_names_set)} existing players in database")
            
            # Find missing players
            missing_players = {}
            for player_name, info in discovered_players.items():
                if player_name not in existing_names_set:
                    missing_players[player_name] = info
                    
            logger.info(f"Found {len(missing_players)} missing players")
            return missing_players
            
        finally:
            session.close()
    
    def create_placeholder_players(self, missing_players: Dict[str, PlayerInfo]) -> int:
        """
        Create placeholder entries for missing players
        
        Args:
            missing_players: Dictionary of missing players to create
            
        Returns:
            Number of players successfully created
        """
        if not missing_players:
            logger.info("No missing players to create")
            return 0
            
        logger.info(f"Creating {len(missing_players)} placeholder players...")
        
        session = self.SessionLocal()
        try:
            players_to_insert = []
            
            for player_name, info in missing_players.items():
                player = Player(
                    name=player_name,
                    nationality=info.likely_nationality,
                    # Set default values for auto-discovered players
                    batting_hand='unknown',  # Will be updated later if discovered
                    bowling_type='unknown',  # Will be updated later if discovered
                    batter_type='unknown',
                    bowler_type='unknown',
                    bowl_hand='unknown',
                    bowl_type='unknown',
                    league_teams=','.join(sorted(info.team_countries)) if info.team_countries else None
                )
                players_to_insert.append(player)
            
            # Bulk insert for efficiency
            session.bulk_save_objects(players_to_insert)
            session.commit()
            
            logger.info(f"Successfully created {len(players_to_insert)} placeholder players")
            return len(players_to_insert)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating placeholder players: {e}")
            raise
        finally:
            session.close()
    
    def generate_missing_players_report(self, missing_players: Dict[str, PlayerInfo]) -> str:
        """
        Generate a detailed report of missing players
        
        Args:
            missing_players: Dictionary of missing players
            
        Returns:
            Formatted report string
        """
        if not missing_players:
            return "No missing players found."
            
        report_lines = [
            "Missing Players Discovery Report",
            "=" * 40,
            f"Total missing players: {len(missing_players)}",
            ""
        ]
        
        # Group by nationality for better organization
        by_nationality = defaultdict(list)
        for name, info in missing_players.items():
            nationality = info.likely_nationality or "Unknown"
            by_nationality[nationality].append((name, info))
        
        for nationality, players in sorted(by_nationality.items()):
            report_lines.append(f"{nationality}: {len(players)} players")
            for name, info in sorted(players, key=lambda x: x[1].match_count, reverse=True):
                roles = "/".join(info.appears_as)
                teams = ", ".join(sorted(info.team_countries))
                report_lines.append(
                    f"  - {name} ({roles}) - {info.match_count} matches, "
                    f"{info.ball_count} balls - Teams: {teams}"
                )
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def scan_single_file_for_players(self, json_file: str) -> Dict[str, PlayerInfo]:
        """
        Scan a single JSON file for players (used by enhanced_loadMatches.py)
        
        Args:
            json_file: Path to single JSON file
            
        Returns:
            Dictionary of players found in the file
        """
        discovered_players = defaultdict(lambda: PlayerInfo(
            name="", appears_as=[], team_countries=set(), 
            match_count=0, ball_count=0
        ))
        
        self._scan_single_file(Path(json_file), discovered_players)
        
        # Convert to regular dict and infer nationalities
        result = {}
        for player_name, info in discovered_players.items():
            info.name = player_name
            info.likely_nationality = self._infer_nationality(info.team_countries)
            result[player_name] = info
            
        return result
    
    def validate_player_completeness(self) -> Dict[str, int]:
        """
        Validate current player data completeness
        
        Returns:
            Dictionary with completeness statistics
        """
        session = self.SessionLocal()
        try:
            # Query player statistics
            result = session.execute(text("""
                SELECT 
                    COUNT(*) as total_players,
                    COUNT(CASE WHEN nationality IS NOT NULL THEN 1 END) as with_nationality,
                    COUNT(CASE WHEN batting_hand != 'unknown' THEN 1 END) as with_batting_hand,
                    COUNT(CASE WHEN bowling_type != 'unknown' THEN 1 END) as with_bowling_type,
                    COUNT(CASE WHEN nationality IS NULL OR nationality = 'unknown' THEN 1 END) as need_review
                FROM players
            """)).fetchone()
            
            return {
                'total_players': result.total_players,
                'with_nationality': result.with_nationality,
                'with_batting_hand': result.with_batting_hand,
                'with_bowling_type': result.with_bowling_type,
                'need_manual_review': result.need_review
            }
        finally:
            session.close()

if __name__ == "__main__":
    """
    Command-line interface for player discovery
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Discover missing players from JSON files')
    parser.add_argument('json_directory', help='Directory containing JSON match files')
    parser.add_argument('--create', action='store_true', 
                       help='Create placeholder entries for missing players')
    parser.add_argument('--report-only', action='store_true',
                       help='Generate report without creating players')
    
    args = parser.parse_args()
    
    # Initialize service
    service = PlayerDiscoveryService()
    
    # Discover players
    discovered = service.scan_json_files_for_players(args.json_directory)
    missing = service.find_missing_players(discovered)
    
    # Generate report
    report = service.generate_missing_players_report(missing)
    print(report)
    
    # Create players if requested
    if args.create and not args.report_only:
        created_count = service.create_placeholder_players(missing)
        print(f"\nCreated {created_count} placeholder players")
    elif not args.report_only:
        print("\nTo create these players, run with --create flag")
