#!/usr/bin/env python3
"""
Script to normalize league names in the database based on mappings and aliases.
This script will:
1. Standardize all league names in the database
2. Update matches competition field to use consistent naming

Usage:
python fix_league_names.py
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Database connection string
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://username:password@localhost:5432/cricket_data")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Maps for league standardization
LEAGUES_MAPPING = { 
    "Indian Premier League": "IPL",
    "Big Bash League": "BBL", 
    "Pakistan Super League": "PSL",
    "Caribbean Premier League": "CPL",
    "SA20": "SA20",
    "International League T20": "ILT20",
    "Bangladesh Premier League": "BPL",
    "Lanka Premier League": "LPL",
    "Major League Cricket": "MLC"
}

# Additional mapping for leagues with name changes over time
LEAGUE_ALIASES = {
    "HRV Cup": "Super Smash",
    "HRV Twenty20": "Super Smash",
    "NatWest T20 Blast": "Vitality Blast",
    "Vitality Blast Men": "Vitality Blast"
}

def create_db_connection():
    """Create and return a database connection"""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        sys.exit(1)

def get_league_standard_name(league_name):
    """Get standardized league name based on mappings and aliases"""
    # First check if it's a league alias (renamed league)
    if league_name in LEAGUE_ALIASES:
        return LEAGUE_ALIASES[league_name]
    
    # Check if it's an abbreviation that needs to be expanded
    # Create a reverse mapping from abbreviation to full name
    reverse_mapping = {abbrev: full_name for full_name, abbrev in LEAGUES_MAPPING.items()}
    if league_name in reverse_mapping:
        # For database consistency, we'll use the full name
        return reverse_mapping[league_name]
    
    # Keep the full name or return original if not found in mappings
    return league_name

def print_league_stats(session):
    """Print statistics about leagues in the database"""
    query = text("""
        SELECT competition, match_type, COUNT(*) as match_count 
        FROM matches 
        WHERE competition IS NOT NULL 
        GROUP BY competition, match_type
        ORDER BY match_type, competition
    """)
    
    results = session.execute(query).fetchall()
    
    logger.info("Current league stats in database:")
    for row in results:
        if row[1] == 'league':  # Only show leagues, not internationals
            logger.info(f"  {row[0]}: {row[2]} matches")
    
    return results

def normalize_league_names(session):
    """Update all league names in the database to use standardized names"""
    # First get all leagues in the database
    leagues_query = text("""
        SELECT DISTINCT competition 
        FROM matches 
        WHERE match_type = 'league' AND competition IS NOT NULL
    """)
    
    leagues = [row[0] for row in session.execute(leagues_query).fetchall()]
    logger.info(f"Found {len(leagues)} distinct league names in database")
    
    # Build mapping from current league names to standardized names
    standardization_map = {}
    for league in leagues:
        standard_name = get_league_standard_name(league)
        if standard_name != league:
            standardization_map[league] = standard_name
    
    # Print the mapping for confirmation
    if standardization_map:
        logger.info("Will standardize the following league names:")
        for old_name, new_name in standardization_map.items():
            logger.info(f"  {old_name} -> {new_name}")
    else:
        logger.info("No league names need standardization")
        return
    
    # Confirm with user
    confirmation = input("\nProceed with these changes? (yes/no): ")
    if confirmation.lower() != 'yes':
        logger.info("Aborted by user.")
        return
    
    # Update each league name that needs to be standardized
    for old_name, new_name in standardization_map.items():
        update_query = text("""
            UPDATE matches
            SET competition = :new_name
            WHERE competition = :old_name AND match_type = 'league'
        """)
        
        result = session.execute(update_query, {"old_name": old_name, "new_name": new_name})
        logger.info(f"Updated {result.rowcount} matches from '{old_name}' to '{new_name}'")
    
    # Commit the changes
    session.commit()
    logger.info("All league names have been standardized")

def main():
    """Main function"""
    logger.info("Starting league name standardization")
    
    # Create database connection
    session = create_db_connection()
    
    try:
        # Print current league stats
        logger.info("Before standardization:")
        print_league_stats(session)
        
        # Normalize league names
        normalize_league_names(session)
        
        # Print updated league stats
        logger.info("\nAfter standardization:")
        print_league_stats(session)
        
    except Exception as e:
        logger.error(f"Error during standardization: {e}")
        session.rollback()
    finally:
        session.close()
    
    logger.info("League name standardization completed")

if __name__ == "__main__":
    main()
