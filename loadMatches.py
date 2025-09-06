# load_matches.py - Optimized version
import json
import os
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from models import Match, Delivery, Base
from database import get_database_connection
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_existing_match_ids(session: Session) -> set:
    """Get all existing match IDs from database in a single query"""
    existing_ids = session.query(Match.id).all()
    return {match_id[0] for match_id in existing_ids}

def load_match_json(json_file_path: str, session: Session) -> None:
    """Load a single match JSON file - assumes match doesn't exist"""
    with open(json_file_path) as f:
        data = json.load(f)
    
    match_id = Path(json_file_path).stem

    try:
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

        # Insert match record first and commit
        session.add(match)
        session.commit()
        
        # Now process deliveries
        deliveries = []
        for innings_num, innings in enumerate(data['innings'], 1):
            batting_team = innings['team']
            bowling_team = info['teams'][0] if batting_team == info['teams'][1] else info['teams'][1]
            
            for over in innings['overs']:
                for ball_num, ball in enumerate(over['deliveries'], 1):
                    delivery = Delivery(
                        match_id=match_id,
                        innings=innings_num,
                        over=over['over'],
                        ball=ball_num,
                        batter=ball['batter'],
                        non_striker=ball['non_striker'],
                        bowler=ball['bowler'],
                        runs_off_bat=ball['runs']['batter'],
                        extras=ball['runs'].get('extras', 0),
                        wides=ball.get('extras', {}).get('wides', 0),
                        noballs=ball.get('extras', {}).get('noballs', 0),
                        byes=ball.get('extras', {}).get('byes', 0),
                        legbyes=ball.get('extras', {}).get('legbyes', 0),
                        penalty=ball.get('extras', {}).get('penalty', 0),
                        batting_team=batting_team,
                        bowling_team=bowling_team
                    )
                    
                    if 'wickets' in ball:
                        wicket = ball['wickets'][0]
                        delivery.wicket_type = wicket['kind']
                        delivery.player_dismissed = wicket['player_out']
                        if 'fielders' in wicket and wicket['fielders']:
                            delivery.fielder = wicket['fielders'][0].get('name')
                    
                    deliveries.append(delivery)
        
        session.bulk_save_objects(deliveries)
        session.commit()
        logger.info(f"Successfully processed match {match_id}")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing match {match_id}: {e}")
        raise

def process_matches_batch(json_files: list, existing_ids: set, session: Session) -> list:
    """Process a batch of matches that don't exist in database"""
    errors = []
    
    for json_file in tqdm(json_files, desc="Processing batch"):
        try:
            load_match_json(str(json_file), session)
        except Exception as e:
            errors.append((str(json_file), str(e)))
            logger.error(f"Error processing {json_file}: {e}")
            continue
    
    return errors

def process_matches(input_path: str, batch_size: int = 100) -> None:
    """Process single file or directory of JSON match files with optimizations"""
    # Get database connection
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()

    try:
        path = Path(input_path)
        if path.is_file() and path.suffix == '.json':
            # Single file - check if exists first
            match_id = path.stem
            existing_ids = get_existing_match_ids(session)
            if match_id in existing_ids:
                logger.info(f"Match {match_id} already exists, skipping...")
                return
            load_match_json(str(path), session)
            
        elif path.is_dir():
            # Directory of files - optimized approach
            json_files = list(path.glob('*.json'))
            logger.info(f"Found {len(json_files)} JSON files to process")
            
            # Get all existing match IDs in one query
            logger.info("Checking existing matches in database...")
            existing_ids = get_existing_match_ids(session)
            logger.info(f"Found {len(existing_ids)} existing matches in database")
            
            # Filter out files that already exist
            files_to_process = []
            skipped_count = 0
            
            for json_file in json_files:
                match_id = json_file.stem
                if match_id not in existing_ids:
                    files_to_process.append(json_file)
                else:
                    skipped_count += 1
            
            logger.info(f"Skipping {skipped_count} matches that already exist")
            logger.info(f"Processing {len(files_to_process)} new matches")
            
            if not files_to_process:
                logger.info("No new matches to process!")
                return
            
            # Process in batches to manage memory and transactions
            all_errors = []
            for i in range(0, len(files_to_process), batch_size):
                batch = files_to_process[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(files_to_process) + batch_size - 1)//batch_size}")
                
                batch_errors = process_matches_batch(batch, existing_ids, session)
                all_errors.extend(batch_errors)
            
            # Print error summary
            if all_errors:
                logger.error("\nErrors encountered:")
                for file, error in all_errors:
                    logger.error(f"{file}: {error}")
                logger.error(f"\nTotal errors: {len(all_errors)} out of {len(files_to_process)} files")
            else:
                logger.info("\nAll files processed successfully!")
                
        else:
            raise ValueError(f"Invalid input path: {input_path}")

    except Exception as e:
        logger.error(f"Error in main processing: {e}")
        raise
    finally:
        session.close()

# Alternative approach using bulk operations for even better performance
def process_matches_bulk_insert(input_path: str) -> None:
    """Ultra-fast bulk insert approach - processes all at once"""
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        path = Path(input_path)
        if not path.is_dir():
            raise ValueError("Bulk insert only works with directories")
            
        json_files = list(path.glob('*.json'))
        logger.info(f"Found {len(json_files)} JSON files for bulk processing")
        
        # Get existing IDs
        existing_ids = get_existing_match_ids(session)
        logger.info(f"Found {len(existing_ids)} existing matches")
        
        # Prepare bulk data
        matches_to_insert = []
        deliveries_to_insert = []
        files_to_process = []
        
        for json_file in tqdm(json_files, desc="Preparing data"):
            match_id = json_file.stem
            if match_id in existing_ids:
                continue
                
            try:
                with open(json_file) as f:
                    data = json.load(f)
                
                files_to_process.append(json_file)
                
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
                
                # Prepare delivery records
                for innings_num, innings in enumerate(data['innings'], 1):
                    batting_team = innings['team']
                    bowling_team = info['teams'][0] if batting_team == info['teams'][1] else info['teams'][1]
                    
                    for over in innings['overs']:
                        for ball_num, ball in enumerate(over['deliveries'], 1):
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
                                'bowling_team': bowling_team
                            }
                            
                            if 'wickets' in ball:
                                wicket = ball['wickets'][0]
                                delivery_dict['wicket_type'] = wicket['kind']
                                delivery_dict['player_dismissed'] = wicket['player_out']
                                if 'fielders' in wicket and wicket['fielders']:
                                    delivery_dict['fielder'] = wicket['fielders'][0].get('name')
                            
                            deliveries_to_insert.append(delivery_dict)
                            
            except Exception as e:
                logger.error(f"Error preparing {json_file}: {e}")
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
            
            logger.info(f"Successfully bulk inserted {len(matches_to_insert)} matches!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error in bulk processing: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    # Choose your approach:
    
    # Option 1: Optimized with batching (recommended for most cases)
    process_matches("/Users/adityabalaji/Desktop/CricketDataViz/t20s_male_json-2/")
    
    # Option 2: Ultra-fast bulk insert (for initial loads or when you're sure about data quality)
    # process_matches_bulk_insert("/Users/adityabalaji/Desktop/CricketDataViz/t20s_male_json-2/")