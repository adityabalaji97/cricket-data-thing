#!/usr/bin/env python3
"""
Enhanced Match Loader

Enhanced version of loadMatches.py that integrates with player discovery
and populates all enhancement columns during initial data loading.

Features:
- Automatic player discovery and creation
- Population of all delivery enhancement columns during load
- Bulk optimization for large datasets
- Handles both new matches and backfill scenarios
- Integration with unified pipeline

Usage:
    python enhanced_loadMatches.py /path/to/json/files/
    python enhanced_loadMatches.py /path/to/single/match.json --single-file
    python enhanced_loadMatches.py /path/to/json/files/ --batch-size 50 --auto-create-players
"""

import json
import os
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import Match, Delivery, Player, Base
from database import get_database_connection
from player_discovery import PlayerDiscoveryService, PlayerInfo
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedMatchLoader:
    """Enhanced match loader with player discovery and column population"""
    
    def __init__(self, auto_create_players: bool = True, batch_size: int = 100):
        """
        Initialize the enhanced loader
        
        Args:
            auto_create_players: Whether to automatically create missing players
            batch_size: Number of matches to process in each batch
        """
        self.auto_create_players = auto_create_players
        self.batch_size = batch_size
        self.engine, self.SessionLocal = get_database_connection()
        
        # Initialize player discovery service
        self.player_discovery = PlayerDiscoveryService()
        
        # Cache for player data to avoid repeated queries
        self.player_cache: Dict[str, Dict[str, str]] = {}
        self.cache_loaded = False
    
    def _load_player_cache(self, session: Session) -> None:
        """Load all player data into memory cache for fast lookups"""
        if self.cache_loaded:
            return
            
        logger.info("Loading player cache...")
        
        # Query all players with relevant data
        players = session.query(Player.name, Player.batter_type, Player.bowler_type).all()
        
        for name, batter_type, bowler_type in players:
            self.player_cache[name] = {
                'batter_type': batter_type or 'unknown',
                'bowler_type': bowler_type or 'unknown'
            }
        
        logger.info(f"Loaded {len(self.player_cache)} players into cache")
        self.cache_loaded = True
    
    def _get_player_info(self, player_name: str) -> Dict[str, str]:
        """Get player info from cache"""
        return self.player_cache.get(player_name, {
            'batter_type': 'unknown',
            'bowler_type': 'unknown'
        })
    
    def _calculate_crease_combo(self, striker_type: str, non_striker_type: str) -> str:
        """Calculate crease combination"""
        if striker_type == 'unknown' or non_striker_type == 'unknown':
            return 'unknown'
        elif striker_type == 'RHB' and non_striker_type == 'RHB':
            return 'rhb_rhb'
        elif striker_type == 'LHB' and non_striker_type == 'LHB':
            return 'lhb_lhb'
        elif (striker_type == 'LHB' and non_striker_type == 'RHB') or \
             (striker_type == 'RHB' and non_striker_type == 'LHB'):
            return 'lhb_rhb'
        else:
            return 'unknown'
    
    def _calculate_ball_direction(self, striker_type: str, bowler_type: str) -> str:
        """Calculate ball direction"""
        if striker_type == 'unknown' or bowler_type == 'unknown':
            return 'unknown'
        elif (striker_type == 'RHB' and bowler_type in ('RO', 'LC')) or \
             (striker_type == 'LHB' and bowler_type in ('RL', 'LO')):
            return 'intoBatter'
        elif (striker_type == 'LHB' and bowler_type in ('RO', 'LC')) or \
             (striker_type == 'RHB' and bowler_type in ('RL', 'LO')):
            return 'awayFromBatter'
        else:
            return 'unknown'
    
    def ensure_players_exist(self, json_file: str, session: Session) -> int:
        """
        Ensure all players from match exist in players table
        
        Args:
            json_file: Path to JSON match file
            session: Database session
            
        Returns:
            Number of new players created
        """
        if not self.auto_create_players:
            return 0
            
        # Discover players from this file
        discovered_players = self.player_discovery.scan_single_file_for_players(json_file)
        
        # Find missing players
        missing_players = self.player_discovery.find_missing_players(discovered_players)
        
        if missing_players:
            logger.info(f"Creating {len(missing_players)} missing players from {Path(json_file).name}")
            created_count = self.player_discovery.create_placeholder_players(missing_players)
            
            # Update cache with new players
            for player_name in missing_players.keys():
                self.player_cache[player_name] = {
                    'batter_type': 'unknown',
                    'bowler_type': 'unknown'
                }
            
            return created_count
        
        return 0
    
    def create_enhanced_delivery(self, ball_data: dict, match_context: dict) -> Delivery:
        """
        Create delivery with all enhancement columns populated
        
        Args:
            ball_data: Ball data from JSON
            match_context: Match context information
            
        Returns:
            Delivery object with all columns populated
        """
        # Get player information
        striker_info = self._get_player_info(ball_data['batter'])
        non_striker_info = self._get_player_info(ball_data['non_striker'])
        bowler_info = self._get_player_info(ball_data['bowler'])
        
        # Create basic delivery
        delivery = Delivery(
            match_id=match_context['match_id'],
            innings=match_context['innings'],
            over=match_context['over'],
            ball=match_context['ball'],
            batter=ball_data['batter'],
            non_striker=ball_data['non_striker'],
            bowler=ball_data['bowler'],
            runs_off_bat=ball_data['runs']['batter'],
            extras=ball_data['runs'].get('extras', 0),
            wides=ball_data.get('extras', {}).get('wides', 0),
            noballs=ball_data.get('extras', {}).get('noballs', 0),
            byes=ball_data.get('extras', {}).get('byes', 0),
            legbyes=ball_data.get('extras', {}).get('legbyes', 0),
            penalty=ball_data.get('extras', {}).get('penalty', 0),
            batting_team=match_context['batting_team'],
            bowling_team=match_context['bowling_team'],
            # Populate enhancement columns during creation
            striker_batter_type=striker_info['batter_type'],
            non_striker_batter_type=non_striker_info['batter_type'],
            bowler_type=bowler_info['bowler_type']
        )
        
        # Calculate derived columns
        delivery.crease_combo = self._calculate_crease_combo(
            delivery.striker_batter_type, 
            delivery.non_striker_batter_type
        )
        delivery.ball_direction = self._calculate_ball_direction(
            delivery.striker_batter_type,
            delivery.bowler_type
        )
        
        # Handle wickets
        if 'wickets' in ball_data:
            wicket = ball_data['wickets'][0]
            delivery.wicket_type = wicket['kind']
            delivery.player_dismissed = wicket['player_out']
            if 'fielders' in wicket and wicket['fielders']:
                delivery.fielder = wicket['fielders'][0].get('name')
        
        return delivery
    
    def load_match_with_enhanced_columns(self, json_file: str, session: Session) -> bool:
        """
        Load a single match with all enhancement columns populated
        
        Args:
            json_file: Path to JSON match file
            session: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(json_file) as f:
                data = json.load(f)
            
            match_id = Path(json_file).stem
            
            # Check if match already exists
            existing_match = session.query(Match).filter(Match.id == match_id).first()
            if existing_match:
                logger.info(f"Match {match_id} already exists, skipping...")
                return True
            
            # Ensure players exist first
            new_players_created = self.ensure_players_exist(json_file, session)
            if new_players_created > 0:
                # Reload cache if new players were created
                self.cache_loaded = False
                self._load_player_cache(session)
            
            # Create match record
            info = data['info']
            is_international = info.get('team_type') == 'international'
            match_type = 'international' if is_international else 'league'
            competition = 'T20I' if is_international else info.get('event', {}).get('name')
            
            match = Match(
                id=match_id,
                date=datetime.strptime(info['dates'][0], '%Y-%m-%d'),
                venue=info.get('venue'),
                city=info.get('city'),
                event_name=info.get('event', {}).get('name'),
                event_match_number=info.get('event', {}).get('match_number'),
                team1=info['teams'][0],
                team2=info['teams'][1],
                toss_winner=info.get('toss', {}).get('winner'),
                toss_decision=info.get('toss', {}).get('decision'),
                winner=info.get('outcome', {}).get('winner'),
                outcome=info.get('outcome', {}),
                player_of_match=info.get('player_of_match', [None])[0] if info.get('player_of_match') else None,
                overs=info.get('overs'),
                balls_per_over=info.get('balls_per_over'),
                match_type=match_type,
                competition=competition
            )
            
            # Calculate derived match fields
            if match.toss_winner:
                if match.toss_decision == 'bat':
                    match.bat_first = match.toss_winner
                    match.bowl_first = match.team2 if match.toss_winner == match.team1 else match.team1
                else:
                    match.bowl_first = match.toss_winner
                    match.bat_first = match.team2 if match.toss_winner == match.team1 else match.team1
                
                match.win_toss_win_match = match.toss_winner == match.winner
                if match.winner:
                    match.won_batting_first = match.bat_first == match.winner
                    match.won_fielding_first = match.bowl_first == match.winner
            
            # Insert match record first
            session.add(match)
            session.flush()  # Get the ID but don't commit yet
            
            # Process deliveries with enhancement columns
            deliveries = []
            for innings_num, innings in enumerate(data['innings'], 1):
                batting_team = innings['team']
                bowling_team = info['teams'][0] if batting_team == info['teams'][1] else info['teams'][1]
                
                for over in innings['overs']:
                    for ball_num, ball in enumerate(over['deliveries'], 1):
                        match_context = {
                            'match_id': match_id,
                            'innings': innings_num,
                            'over': over['over'],
                            'ball': ball_num,
                            'batting_team': batting_team,
                            'bowling_team': bowling_team
                        }
                        
                        delivery = self.create_enhanced_delivery(ball, match_context)
                        deliveries.append(delivery)
            
            # Bulk insert deliveries
            session.bulk_save_objects(deliveries)
            session.commit()
            
            logger.info(f"✅ Successfully processed match {match_id} with {len(deliveries)} deliveries")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error processing match {json_file}: {e}")
            raise
    
    def get_existing_match_ids(self, session: Session) -> Set[str]:
        """Get all existing match IDs from database"""
        existing_ids = session.query(Match.id).all()
        return {match_id[0] for match_id in existing_ids}
    
    def process_matches_batch(self, json_files: List[Path], session: Session) -> List[Tuple[str, str]]:
        """
        Process a batch of matches
        
        Args:
            json_files: List of JSON files to process
            session: Database session
            
        Returns:
            List of (filename, error) tuples for failed matches
        """
        errors = []
        
        for json_file in tqdm(json_files, desc="Processing batch"):
            try:
                success = self.load_match_with_enhanced_columns(str(json_file), session)
                if not success:
                    errors.append((str(json_file), "Failed to load"))
            except Exception as e:
                errors.append((str(json_file), str(e)))
                logger.error(f"Error processing {json_file}: {e}")
                continue
        
        return errors
    
    def process_matches(self, input_path: str) -> Dict[str, int]:
        """
        Process single file or directory of JSON match files
        
        Args:
            input_path: Path to JSON file or directory
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"🚀 Starting enhanced match processing: {input_path}")
        
        session = self.SessionLocal()
        stats = {
            'total_files': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'new_players_created': 0
        }
        
        try:
            # Load player cache
            self._load_player_cache(session)
            
            path = Path(input_path)
            if path.is_file() and path.suffix == '.json':
                # Single file processing
                stats['total_files'] = 1
                match_id = path.stem
                existing_ids = self.get_existing_match_ids(session)
                
                if match_id in existing_ids:
                    logger.info(f"Match {match_id} already exists, skipping...")
                    stats['skipped'] = 1
                else:
                    success = self.load_match_with_enhanced_columns(str(path), session)
                    if success:
                        stats['processed'] = 1
                    else:
                        stats['errors'] = 1
                        
            elif path.is_dir():
                # Directory processing with optimization
                json_files = list(path.glob('*.json'))
                stats['total_files'] = len(json_files)
                
                if not json_files:
                    logger.warning(f"No JSON files found in {input_path}")
                    return stats
                
                logger.info(f"Found {len(json_files)} JSON files")
                
                # Get existing match IDs
                logger.info("Checking existing matches...")
                existing_ids = self.get_existing_match_ids(session)
                logger.info(f"Found {len(existing_ids)} existing matches in database")
                
                # Filter out existing matches
                files_to_process = []
                for json_file in json_files:
                    match_id = json_file.stem
                    if match_id not in existing_ids:
                        files_to_process.append(json_file)
                    else:
                        stats['skipped'] += 1
                
                logger.info(f"Processing {len(files_to_process)} new matches (skipping {stats['skipped']} existing)")
                
                if not files_to_process:
                    logger.info("No new matches to process!")
                    return stats
                
                # Process in batches
                all_errors = []
                for i in range(0, len(files_to_process), self.batch_size):
                    batch = files_to_process[i:i + self.batch_size]
                    batch_num = i // self.batch_size + 1
                    total_batches = (len(files_to_process) + self.batch_size - 1) // self.batch_size
                    
                    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} matches)")
                    
                    batch_errors = self.process_matches_batch(batch, session)
                    all_errors.extend(batch_errors)
                    
                    # Update stats
                    batch_processed = len(batch) - len(batch_errors)
                    stats['processed'] += batch_processed
                    stats['errors'] += len(batch_errors)
                
                # Report errors
                if all_errors:
                    logger.error(f"\n❌ Errors encountered:")
                    for file, error in all_errors[:10]:  # Show first 10 errors
                        logger.error(f"  {Path(file).name}: {error}")
                    if len(all_errors) > 10:
                        logger.error(f"  ... and {len(all_errors) - 10} more errors")
                
            else:
                raise ValueError(f"Invalid input path: {input_path}")
            
            # Final statistics
            logger.info(f"\n📊 Processing Summary:")
            logger.info(f"  Total files: {stats['total_files']}")
            logger.info(f"  Processed: {stats['processed']}")
            logger.info(f"  Skipped (existing): {stats['skipped']}")
            logger.info(f"  Errors: {stats['errors']}")
            
            if stats['errors'] == 0:
                logger.info("🎉 All files processed successfully!")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in main processing: {e}")
            raise
        finally:
            session.close()
    
    def bulk_insert_approach(self, input_path: str) -> Dict[str, int]:
        """
        Ultra-fast bulk insert approach for initial loads
        
        Args:
            input_path: Directory containing JSON files
            
        Returns:
            Processing statistics
        """
        logger.info(f"🚀 Starting bulk insert processing: {input_path}")
        
        session = self.SessionLocal()
        stats = {
            'total_files': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }
        
        try:
            # Load player cache
            self._load_player_cache(session)
            
            path = Path(input_path)
            if not path.is_dir():
                raise ValueError("Bulk insert only works with directories")
            
            json_files = list(path.glob('*.json'))
            stats['total_files'] = len(json_files)
            
            if not json_files:
                logger.warning(f"No JSON files found in {input_path}")
                return stats
            
            # Get existing IDs
            existing_ids = self.get_existing_match_ids(session)
            logger.info(f"Found {len(existing_ids)} existing matches")
            
            # Prepare bulk data
            matches_to_insert = []
            deliveries_to_insert = []
            files_processed = []
            
            logger.info("Preparing bulk data...")
            for json_file in tqdm(json_files, desc="Preparing data"):
                match_id = json_file.stem
                if match_id in existing_ids:
                    stats['skipped'] += 1
                    continue
                
                try:
                    # Auto-create players if needed
                    if self.auto_create_players:
                        self.ensure_players_exist(str(json_file), session)
                    
                    with open(json_file) as f:
                        data = json.load(f)
                    
                    files_processed.append(json_file)
                    
                    # Prepare match record
                    info = data['info']
                    is_international = info.get('team_type') == 'international'
                    match_type = 'international' if is_international else 'league'
                    competition = 'T20I' if is_international else info.get('event', {}).get('name')
                    
                    match_dict = {
                        'id': match_id,
                        'date': datetime.strptime(info['dates'][0], '%Y-%m-%d'),
                        'venue': info.get('venue'),
                        'city': info.get('city'),
                        'event_name': info.get('event', {}).get('name'),
                        'event_match_number': info.get('event', {}).get('match_number'),
                        'team1': info['teams'][0],
                        'team2': info['teams'][1],
                        'toss_winner': info.get('toss', {}).get('winner'),
                        'toss_decision': info.get('toss', {}).get('decision'),
                        'winner': info.get('outcome', {}).get('winner'),
                        'outcome': info.get('outcome', {}),
                        'player_of_match': info.get('player_of_match', [None])[0] if info.get('player_of_match') else None,
                        'overs': info.get('overs'),
                        'balls_per_over': info.get('balls_per_over'),
                        'match_type': match_type,
                        'competition': competition
                    }
                    
                    # Calculate derived fields
                    if match_dict['toss_winner']:
                        if match_dict['toss_decision'] == 'bat':
                            match_dict['bat_first'] = match_dict['toss_winner']
                            match_dict['bowl_first'] = match_dict['team2'] if match_dict['toss_winner'] == match_dict['team1'] else match_dict['team1']
                        else:
                            match_dict['bowl_first'] = match_dict['toss_winner']
                            match_dict['bat_first'] = match_dict['team2'] if match_dict['toss_winner'] == match_dict['team1'] else match_dict['team1']
                        
                        match_dict['win_toss_win_match'] = match_dict['toss_winner'] == match_dict['winner']
                        if match_dict['winner']:
                            match_dict['won_batting_first'] = match_dict['bat_first'] == match_dict['winner']
                            match_dict['won_fielding_first'] = match_dict['bowl_first'] == match_dict['winner']
                    
                    matches_to_insert.append(match_dict)
                    
                    # Prepare delivery records with enhancement columns
                    for innings_num, innings in enumerate(data['innings'], 1):
                        batting_team = innings['team']
                        bowling_team = info['teams'][0] if batting_team == info['teams'][1] else info['teams'][1]
                        
                        for over in innings['overs']:
                            for ball_num, ball in enumerate(over['deliveries'], 1):
                                # Get player info for enhancement columns
                                striker_info = self._get_player_info(ball['batter'])
                                non_striker_info = self._get_player_info(ball['non_striker'])
                                bowler_info = self._get_player_info(ball['bowler'])
                                
                                delivery_dict = {
                                    'match_id': match_id,
                                    'innings': innings_num,
                                    'over': over['over'],
                                    'ball': ball_num,
                                    'batter': ball['batter'],
                                    'non_striker': ball['non_striker'],
                                    'bowler': ball['bowler'],
                                    'runs_off_bat': ball['runs']['batter'],
                                    'extras': ball['runs'].get('extras', 0),
                                    'wides': ball.get('extras', {}).get('wides', 0),
                                    'noballs': ball.get('extras', {}).get('noballs', 0),
                                    'byes': ball.get('extras', {}).get('byes', 0),
                                    'legbyes': ball.get('extras', {}).get('legbyes', 0),
                                    'penalty': ball.get('extras', {}).get('penalty', 0),
                                    'batting_team': batting_team,
                                    'bowling_team': bowling_team,
                                    # Enhancement columns
                                    'striker_batter_type': striker_info['batter_type'],
                                    'non_striker_batter_type': non_striker_info['batter_type'],
                                    'bowler_type': bowler_info['bowler_type']
                                }
                                
                                # Calculate derived columns
                                delivery_dict['crease_combo'] = self._calculate_crease_combo(
                                    striker_info['batter_type'], 
                                    non_striker_info['batter_type']
                                )
                                delivery_dict['ball_direction'] = self._calculate_ball_direction(
                                    striker_info['batter_type'],
                                    bowler_info['bowler_type']
                                )
                                
                                # Handle wickets
                                if 'wickets' in ball:
                                    wicket = ball['wickets'][0]
                                    delivery_dict['wicket_type'] = wicket['kind']
                                    delivery_dict['player_dismissed'] = wicket['player_out']
                                    if 'fielders' in wicket and wicket['fielders']:
                                        delivery_dict['fielder'] = wicket['fielders'][0].get('name')
                                
                                deliveries_to_insert.append(delivery_dict)
                
                except Exception as e:
                    logger.error(f"Error preparing {json_file}: {e}")
                    stats['errors'] += 1
                    continue
            
            logger.info(f"Prepared {len(matches_to_insert)} matches and {len(deliveries_to_insert)} deliveries")
            
            if matches_to_insert:
                # Bulk insert matches
                logger.info("Bulk inserting matches...")
                session.bulk_insert_mappings(Match, matches_to_insert)
                session.commit()
                
                # Bulk insert deliveries
                logger.info("Bulk inserting deliveries...")
                session.bulk_insert_mappings(Delivery, deliveries_to_insert)
                session.commit()
                
                stats['processed'] = len(matches_to_insert)
                logger.info(f"✅ Successfully bulk inserted {len(matches_to_insert)} matches!")
            
            return stats
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error in bulk processing: {e}")
            raise
        finally:
            session.close()


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced cricket match loader with player discovery')
    parser.add_argument('input_path', help='Path to JSON file or directory of JSON files')
    parser.add_argument('--single-file', action='store_true', 
                       help='Process single file (auto-detected if path is file)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for processing (default: 100)')
    parser.add_argument('--no-auto-create-players', action='store_true',
                       help='Disable automatic player creation')
    parser.add_argument('--bulk-insert', action='store_true',
                       help='Use ultra-fast bulk insert method')
    
    args = parser.parse_args()
    
    # Initialize loader
    loader = EnhancedMatchLoader(
        auto_create_players=not args.no_auto_create_players,
        batch_size=args.batch_size
    )
    
    try:
        if args.bulk_insert:
            stats = loader.bulk_insert_approach(args.input_path)
        else:
            stats = loader.process_matches(args.input_path)
        
        # Print final summary
        print(f"\n🎉 Enhanced loading completed!")
        print(f"  Files processed: {stats['processed']}")
        print(f"  Files skipped: {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
