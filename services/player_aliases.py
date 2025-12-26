"""
Player Aliases Service

Shared utility for resolving player name aliases across the application.
The player_aliases table maps:
  - player_name: OLD name (used in legacy 'deliveries' table)
  - alias_name: NEW/canonical name (used in 'delivery_details' table)

Usage:
  from services.player_aliases import resolve_player_name, search_players_with_aliases
"""

from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


def resolve_player_name(name: str, db: Session) -> str:
    """
    Resolve a player name to its canonical form.
    
    If the input is an old/alias name, returns the canonical (new) name.
    If the input is already canonical or not found in aliases, returns as-is.
    
    Args:
        name: Player name to resolve (could be old or new format)
        db: Database session
        
    Returns:
        Canonical player name
    """
    if not name:
        return name
    
    try:
        # First check if input is an OLD name -> get NEW name
        query = text("""
            SELECT alias_name 
            FROM player_aliases 
            WHERE LOWER(player_name) = LOWER(:name)
            LIMIT 1
        """)
        result = db.execute(query, {"name": name}).fetchone()
        
        if result:
            logger.debug(f"Resolved alias: '{name}' -> '{result[0]}'")
            return result[0]
        
        # If not found as old name, check if it exists as a canonical name
        # (or in players table) - return as-is
        return name
        
    except Exception as e:
        logger.warning(f"Error resolving player name '{name}': {e}")
        return name


def get_canonical_name(name: str, db: Session) -> Optional[str]:
    """
    Get the canonical name for a player, checking both players table
    and aliases. Returns None if player not found anywhere.
    
    Args:
        name: Player name to look up
        db: Database session
        
    Returns:
        Canonical name if found, None otherwise
    """
    if not name:
        return None
    
    try:
        # Check if it's an old name in aliases
        alias_query = text("""
            SELECT alias_name 
            FROM player_aliases 
            WHERE LOWER(player_name) = LOWER(:name)
            LIMIT 1
        """)
        alias_result = db.execute(alias_query, {"name": name}).fetchone()
        
        if alias_result:
            return alias_result[0]
        
        # Check if name exists in players table (already canonical)
        players_query = text("""
            SELECT name 
            FROM players 
            WHERE LOWER(name) = LOWER(:name)
            LIMIT 1
        """)
        players_result = db.execute(players_query, {"name": name}).fetchone()
        
        if players_result:
            return players_result[0]
        
        return None
        
    except Exception as e:
        logger.warning(f"Error getting canonical name for '{name}': {e}")
        return None


def search_players_with_aliases(
    query: str, 
    db: Session, 
    limit: int = 10
) -> List[Dict]:
    """
    Search for players by name, including alias matches.
    Returns canonical names only (no duplicates).
    
    Searches:
    1. players.name (canonical names)
    2. player_aliases.player_name (old names) -> returns alias_name
    
    Results are ranked: exact match > prefix match > contains match
    
    Args:
        query: Search query string
        db: Database session
        limit: Maximum results to return
        
    Returns:
        List of dicts with 'name' (canonical) and 'type' ('player')
    """
    if not query or len(query.strip()) < 2:
        return []
    
    search_term = query.strip()
    search_lower = search_term.lower()
    
    try:
        # Search both players table and aliases, returning canonical names
        # Use UNION to combine and deduplicate
        search_query = text("""
            WITH all_matches AS (
                -- Direct matches from players table (canonical names)
                SELECT 
                    p.name as canonical_name,
                    p.name as matched_name,
                    CASE 
                        WHEN LOWER(p.name) = :exact THEN 1
                        WHEN LOWER(p.name) LIKE :prefix THEN 2
                        ELSE 3
                    END as relevance
                FROM players p
                WHERE LOWER(p.name) LIKE :pattern
                
                UNION
                
                -- Matches from aliases (old names -> canonical names)
                SELECT 
                    pa.alias_name as canonical_name,
                    pa.player_name as matched_name,
                    CASE 
                        WHEN LOWER(pa.player_name) = :exact THEN 1
                        WHEN LOWER(pa.player_name) LIKE :prefix THEN 2
                        ELSE 3
                    END as relevance
                FROM player_aliases pa
                WHERE LOWER(pa.player_name) LIKE :pattern
            ),
            -- Deduplicate by canonical name, keeping best relevance
            best_matches AS (
                SELECT 
                    canonical_name,
                    MIN(relevance) as best_relevance
                FROM all_matches
                GROUP BY canonical_name
            )
            SELECT 
                bm.canonical_name as name,
                'player' as type
            FROM best_matches bm
            ORDER BY bm.best_relevance, bm.canonical_name
            LIMIT :limit
        """)
        
        params = {
            "pattern": f"%{search_lower}%",
            "exact": search_lower,
            "prefix": f"{search_lower}%",
            "limit": limit
        }
        
        results = db.execute(search_query, params).fetchall()
        
        return [{"name": row.name, "type": row.type} for row in results]
        
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
        Dict mapping old_name -> new_name (canonical)
    """
    try:
        query = text("SELECT player_name, alias_name FROM player_aliases")
        result = db.execute(query).fetchall()
        return {row[0]: row[1] for row in result}
    except Exception as e:
        logger.warning(f"Error loading aliases map: {e}")
        return {}
