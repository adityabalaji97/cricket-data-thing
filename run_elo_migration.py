#!/usr/bin/env python3
"""
Database migration script to add ELO rating columns to matches table
"""

import logging
from database import get_session
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_elo_migration():
    """Add ELO rating columns to matches table"""
    session = next(get_session())
    
    try:
        logger.info("Starting ELO schema migration...")
        
        # Check if columns already exist
        result = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'matches' 
            AND column_name IN ('team1_elo', 'team2_elo')
        """)).fetchall()
        
        existing_columns = [row.column_name for row in result]
        
        if 'team1_elo' in existing_columns and 'team2_elo' in existing_columns:
            logger.info("ELO columns already exist. Migration not needed.")
            return
        
        # Add ELO columns
        logger.info("Adding team1_elo column...")
        session.execute(text("ALTER TABLE matches ADD COLUMN team1_elo INTEGER"))
        
        logger.info("Adding team2_elo column...")
        session.execute(text("ALTER TABLE matches ADD COLUMN team2_elo INTEGER"))
        
        # Add indexes for performance
        logger.info("Creating indexes...")
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_matches_team1_elo ON matches(team1_elo)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_matches_team2_elo ON matches(team2_elo)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_matches_date_id ON matches(date, id)"))
        
        # Add comments
        session.execute(text("COMMENT ON COLUMN matches.team1_elo IS 'ELO rating of team1 before this match'"))
        session.execute(text("COMMENT ON COLUMN matches.team2_elo IS 'ELO rating of team2 before this match'"))
        
        session.commit()
        logger.info("ELO schema migration completed successfully!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during migration: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    run_elo_migration()
