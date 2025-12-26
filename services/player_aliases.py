"""
Player Aliases Service

Shared utility for resolving player name aliases across the application.
The player_aliases table maps:
  - player_name: OLD/legacy name (used in 'players', 'deliveries', 'batting_stats', 'bowling_stats')
  - alias_name: NEW/readable name (used in 'delivery_details')

Usage:
  from services.player_aliases import resolve_to_legacy_name, search_players_with_aliases
"""

from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


def resolve_to_legacy_name(name: str, db: Session) -> str:
    """
    Resolve any player name to the LEGACY format (used in players/deliveries tables).
    
    If input is a new name (from delivery_details), returns the old name.
    If input is already legacy or not found in aliases, returns as-is.
    
    Args:
        name: Player name (could be old or new format)
        db: Database session
        
    Returns:
        Legacy player name for use with players/deliveries/batting_stats/bowling_stats
    """
    if not name:
        return name
    
    try:
        # Check if input is a NEW name (alias_name) -> get OLD name (player_name)
        query = text("""
            SELECT player_name 
            FROM player_aliases 
            WHERE LOWER(alias_name) = LOWER(:name)
            LIMIT 1
        """)
        result = db.execute(query, {"name": name}).fetchone()
        
        if result:
            logger.debug(f"Resolved to legacy: '{name}' -> '{result[0]}'")
            return result[0]
        
        # Not found as new name - assume it's already legacy or not aliased
        return name
        
    except Exception as e:
        logger.warning(f"Error resolving to legacy name '{name}': {e}")
        return name


def resolve_to_details_name(name: str, db: Session) -> str:
    """
    Resolve any player name to the DETAILS format (used in delivery_details table).
    
    If input is a legacy name (from players/deliveries), returns the new name.
    If input is already new or not found in aliases, returns as-is.
    
    Args:
        name: Player name (could be old or new format)
        db: Database session
        
    Returns:
        Details player name for use with delivery_details
    """
    if not name:
        return name
    
    try:
        # Check if input is an OLD name (player_name) -> get NEW name (alias_name)
        query = text("""
            SELECT alias_name 
            FROM player_aliases 
            WHERE LOWER(player_name) = LOWER(:name)
            LIMIT 1
        """)
        result = db.execute(query, {"name": name}).fetchone()
        
        if result:
            logger.debug(f"Resolved to details: '{name}' -> '{result[0]}'")
            return result[0]
        
        # Not found as old name - assume it's already new or not aliased
        return name
        
    except Exception as e:
        logger.warning(f"Error resolving to details name '{name}': {e}")
        return name


def get_player_names(name: str, db: Session) -> Dict[str, str]:
    """
    Get both legacy and details names for a player.
    
    Args:
        name: Any known name for the player
        db: Database session
        
    Returns:
        {"legacy_name": "V Kohli", "details_name": "Virat Kohli"}
        If no alias exists, both will be the same as input.
    """
    if not name:
        return {"legacy_name": name, "details_name": name}
    
    try:
        # First try: input is a NEW name (alias_name)
        query1 = text("""
            SELECT player_name, alias_name 
            FROM player_aliases 
            WHERE LOWER(alias_name) = LOWER(:name)
            LIMIT 1
        """)
        result = db.execute(query1, {"name": name}).fetchone()
        
        if result:
            return {"legacy_name": result[0], "details_name": result[1]}
        
        # Second try: input is an OLD name (player_name)
        query2 = text("""
            SELECT player_name, alias_name 
            FROM player_aliases 
            WHERE LOWER(player_name) = LOWER(:name)
            LIMIT 1
        """)
        result = db.execute(query2, {"name": name}).fetchone()
        
        if result:
            return {"legacy_name": result[0], "details_name": result[1]}
        
        # No alias found - player uses same name everywhere
        return {"legacy_name": name, "details_name": name}
        
    except Exception as e:
        logger.warning(f"Error getting player names for '{name}': {e}")
        return {"legacy_name": name, "details_name": name}


def search_players_with_aliases(
    query: str, 
    db: Session, 
    limit: int = 10
) -> List[Dict]:
    """
    Search for players by name, including alias matches.
    Returns DEDUPLICATED results with both legacy and details names.
    
    - Shows readable name (details_name) for display
    - Includes legacy_name for routing to existing profile pages
    
    Args:
        query: Search query string
        db: Database session
        limit: Maximum results to return
        
    Returns:
        List of dicts: {
            "name": legacy_name (for routing),
            "display_name": readable name (for UI),
            "details_name": delivery_details name,
            "type": "player"
        }
    """
    if not query or len(query.strip()) < 2:
        return []
    
    search_term = query.strip()
    search_lower = search_term.lower()
    
    try:
        # Strategy:
        # 1. Search players table for legacy names
        # 2. Search player_aliases for both old and new name matches
        # 3. Deduplicate by grouping aliased players together
        # 4. Return both names for each unique player
        
        search_query = text("""
            WITH player_matches AS (
                -- Search in players table (legacy names)
                SELECT 
                    p.name as legacy_name,
                    COALESCE(pa.alias_name, p.name) as display_name,
                    CASE 
                        WHEN LOWER(p.name) = :exact THEN 1
                        WHEN LOWER(p.name) LIKE :prefix THEN 2
                        ELSE 3
                    END as relevance
                FROM players p
                LEFT JOIN player_aliases pa ON p.name = pa.player_name
                WHERE LOWER(p.name) LIKE :pattern
                   OR LOWER(COALESCE(pa.alias_name, '')) LIKE :pattern
                
                UNION
                
                -- Search directly in aliases for new name matches
                SELECT 
                    pa.player_name as legacy_name,
                    pa.alias_name as display_name,
                    CASE 
                        WHEN LOWER(pa.alias_name) = :exact THEN 1
                        WHEN LOWER(pa.alias_name) LIKE :prefix THEN 2
                        ELSE 3
                    END as relevance
                FROM player_aliases pa
                WHERE LOWER(pa.alias_name) LIKE :pattern
            ),
            -- Deduplicate by legacy_name (the unique identifier)
            deduplicated AS (
                SELECT 
                    legacy_name,
                    display_name,
                    MIN(relevance) as best_relevance
                FROM player_matches
                GROUP BY legacy_name, display_name
            )
            SELECT 
                legacy_name,
                display_name
            FROM deduplicated
            ORDER BY best_relevance, display_name
            LIMIT :limit
        """)
        
        params = {
            "pattern": f"%{search_lower}%",
            "exact": search_lower,
            "prefix": f"{search_lower}%",
            "limit": limit
        }
        
        results = db.execute(search_query, params).fetchall()
        
        return [
            {
                "name": row.legacy_name,  # For routing to /player, /bowler
                "display_name": row.display_name,  # For UI display
                "details_name": row.display_name,  # For delivery_details queries
                "type": "player"
            } 
            for row in results
        ]
        
    except Exception as e:
        logger.error(f"Error in search_players_with_aliases: {e}")
        return []


def get_all_name_variants(names: List[str], db: Session) -> List[str]:
    """
    Get all variants (old and new) of player names for querying.
    Useful when querying tables that might have either format.
    
    Args:
        names: List of player names (can be old or new format)
        db: Database session
        
    Returns:
        List of all name variants (original + aliases)
    """
    if not names:
        return []
    
    all_variants = set(names)  # Start with originals
    
    try:
        # Get old names for any new names provided
        new_to_old_query = text("""
            SELECT alias_name, player_name 
            FROM player_aliases 
            WHERE alias_name = ANY(:names)
        """)
        new_to_old = db.execute(new_to_old_query, {"names": names}).fetchall()
        
        for row in new_to_old:
            all_variants.add(row[0])  # alias_name (new)
            all_variants.add(row[1])  # player_name (old)
        
        # Get new names for any old names provided
        old_to_new_query = text("""
            SELECT player_name, alias_name 
            FROM player_aliases 
            WHERE player_name = ANY(:names)
        """)
        old_to_new = db.execute(old_to_new_query, {"names": names}).fetchall()
        
        for row in old_to_new:
            all_variants.add(row[0])  # player_name (old)
            all_variants.add(row[1])  # alias_name (new)
        
    except Exception as e:
        logger.warning(f"Error getting name variants: {e}")
    
    return list(all_variants)


def load_aliases_map(db: Session) -> Dict[str, str]:
    """
    Load all player aliases into a dict for efficient bulk lookups.
    
    Returns:
        Dict mapping old_name -> new_name
    """
    try:
        query = text("SELECT player_name, alias_name FROM player_aliases")
        result = db.execute(query).fetchall()
        return {row[0]: row[1] for row in result}
    except Exception as e:
        logger.warning(f"Error loading aliases map: {e}")
        return {}
