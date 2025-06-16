from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from typing import List
import logging

logger = logging.getLogger(__name__)

def get_batters_service(db: Session) -> List[str]:
    """
    Get list of all unique batters from the deliveries table.
    
    This function queries the deliveries table to get all unique batter names
    and returns them sorted alphabetically. It excludes null/empty values.
    
    Args:
        db: Database session
        
    Returns:
        List of batter names sorted alphabetically
        
    Raises:
        Exception: If database query fails
    """
    try:
        logger.info("Fetching all batters from deliveries table")
        
        query = text("""
            SELECT DISTINCT batter as name 
            FROM deliveries 
            WHERE batter IS NOT NULL 
            AND batter != ''
            ORDER BY batter
        """)
        
        result = db.execute(query).fetchall()
        
        # Extract names from result tuples and format for frontend
        batters = [row[0] for row in result]
        batters_formatted = [{"value": name, "label": name} for name in batters]
        
        logger.info(f"Found {len(batters_formatted)} unique batters")
        return batters_formatted
        
    except Exception as e:
        logger.error(f"Error fetching batters: {str(e)}")
        raise Exception(f"Database query failed: {str(e)}")

def get_bowlers_service(db: Session) -> List[str]:
    """
    Get list of all unique bowlers from the deliveries table.
    
    This function queries the deliveries table to get all unique bowler names
    and returns them sorted alphabetically. It excludes null/empty values.
    
    Args:
        db: Database session
        
    Returns:
        List of bowler names sorted alphabetically
        
    Raises:
        Exception: If database query fails
    """
    try:
        logger.info("Fetching all bowlers from deliveries table")
        
        query = text("""
            SELECT DISTINCT bowler as name 
            FROM deliveries 
            WHERE bowler IS NOT NULL 
            AND bowler != ''
            ORDER BY bowler
        """)
        
        result = db.execute(query).fetchall()
        
        # Extract names from result tuples and format for frontend
        bowlers = [row[0] for row in result]
        bowlers_formatted = [{"value": name, "label": name} for name in bowlers]
        
        logger.info(f"Found {len(bowlers_formatted)} unique bowlers")
        return bowlers_formatted
        
    except Exception as e:
        logger.error(f"Error fetching bowlers: {str(e)}")
        raise Exception(f"Database query failed: {str(e)}")
