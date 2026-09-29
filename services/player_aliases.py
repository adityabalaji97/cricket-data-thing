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
from typing import Any, Optional, List, Dict
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


def expand_name_group(names: List[str], db: Session) -> List[str]:
    """
    Every stored spelling of the given players: the inputs, their canonical names, and every
    name aliased to those canonical names.

    One hop was not enough once a feed changed spelling: "V Suryavanshi" (legacy),
    "Vaibhav Suryavanshi" and "Vaibhav Sooryavanshi" (both delivery_details) all alias to one
    canonical name, and from any one of them the others are two hops away. We only step
    input -> canonical -> members, never member -> other canonical, so an ambiguous legacy
    name ("A Shukla" -> Arpit and Ayush) is not chained into unrelated players.
    """
    names = [n for n in (names or []) if n]
    if not names:
        return []
    try:
        rows = db.execute(text("""
            WITH canon AS (
                SELECT alias_name AS c FROM player_aliases
                WHERE LOWER(alias_name) = ANY(:lowered) OR LOWER(player_name) = ANY(:lowered)
            )
            SELECT c FROM canon
            UNION
            SELECT player_name FROM player_aliases WHERE alias_name IN (SELECT c FROM canon)
        """), {"lowered": [n.lower() for n in names]}).scalars().all()
        return list(dict.fromkeys([*names, *[r for r in rows if r]]))
    except Exception as e:
        logger.warning(f"Error expanding name group for {names}: {e}")
        return names


def get_player_names(name: str, db: Session) -> Dict[str, Any]:
    """
    Legacy and details names for a player, plus every stored spelling.

    Returns:
        {"legacy_name": "V Kohli", "details_name": "Virat Kohli", "all_names": [...]}
        legacy_name is the Cricsheet-style form ("V Kohli") where one exists; details_name is the
        canonical full name. If no alias exists, all are the input.
    """
    if not name:
        return {"legacy_name": name, "details_name": name, "all_names": [name] if name else []}

    try:
        canonical = db.execute(text("""
            SELECT alias_name FROM player_aliases
            WHERE LOWER(alias_name) = LOWER(:name) OR LOWER(player_name) = LOWER(:name)
            ORDER BY (LOWER(alias_name) = LOWER(:name)) DESC, alias_name
            LIMIT 1
        """), {"name": name}).scalar()
        if not canonical:
            return {"legacy_name": name, "details_name": name, "all_names": [name]}
        members = db.execute(text("""
            SELECT player_name FROM player_aliases WHERE alias_name = :canonical
            -- Prefer the initials form ("V Kohli") as the legacy name: that is how the legacy
            -- tables spell it; a spelling-variant alias ("Vaibhav Suryavanshi") is not legacy.
            ORDER BY (player_name ~ '^[A-Z]+ ') DESC, player_name
        """), {"canonical": canonical}).scalars().all()
        legacy = name if (name != canonical and name in members) else (members[0] if members else name)
        return {"legacy_name": legacy, "details_name": canonical,
                "all_names": list(dict.fromkeys([name, canonical, *members]))}

    except Exception as e:
        logger.warning(f"Error getting player names for '{name}': {e}")
        return {"legacy_name": name, "details_name": name, "all_names": [name]}


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

        if not results and len(search_lower) >= 4:
            search_words = [w for w in search_lower.split() if len(w) >= 2]
            word_sim_clauses = " + ".join(
                f"(SELECT MAX(similarity(w, :w{i})) FROM unnest(string_to_array(LOWER(best_name), ' ')) AS w)"
                for i in range(len(search_words))
            ) if search_words else "0"
            trgm_query = text(f"""
                WITH trgm_matches AS (
                    SELECT
                        p.name as legacy_name,
                        COALESCE(pa.alias_name, p.name) as display_name,
                        GREATEST(
                            similarity(LOWER(p.name), :search),
                            similarity(LOWER(COALESCE(pa.alias_name, '')), :search)
                        ) as sim_score
                    FROM players p
                    LEFT JOIN player_aliases pa ON p.name = pa.player_name
                    WHERE similarity(LOWER(p.name), :search) > 0.3
                       OR similarity(LOWER(COALESCE(pa.alias_name, '')), :search) > 0.3

                    UNION

                    SELECT
                        pa.player_name as legacy_name,
                        pa.alias_name as display_name,
                        similarity(LOWER(pa.alias_name), :search) as sim_score
                    FROM player_aliases pa
                    WHERE similarity(LOWER(pa.alias_name), :search) > 0.3
                ),
                deduplicated AS (
                    SELECT
                        legacy_name,
                        display_name,
                        MAX(sim_score) as best_score
                    FROM trgm_matches
                    GROUP BY legacy_name, display_name
                ),
                scored AS (
                    SELECT
                        legacy_name,
                        display_name,
                        best_score,
                        LOWER(display_name) as best_name
                    FROM deduplicated
                )
                SELECT legacy_name, display_name
                FROM scored
                ORDER BY ({word_sim_clauses}) DESC, best_score DESC, display_name
                LIMIT :limit
            """)
            word_params = {f"w{i}": w for i, w in enumerate(search_words)}
            word_params["search"] = search_lower
            word_params["limit"] = limit
            results = db.execute(trgm_query, word_params).fetchall()

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
    """All stored spellings of these players (see expand_name_group)."""
    return expand_name_group(names, db)


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


# =========================================================================================
# Canonical-name SQL, for grouping
# =========================================================================================
# The stats tables are written by two ingest paths with different naming conventions --
# statsProcessor.py writes Cricsheet style ("V Kohli"), sync_stats_from_dd.py writes full names
# ("Virat Kohli") -- so the same player has rows under both. Grouping on the raw name therefore
# splits a player in two. This CTE maps either spelling onto one canonical name so the
# aggregation merges in SQL, where it can actually sum, rather than being relabelled afterwards.

ALIAS_MAP_CTE = """
    alias_map AS (
        SELECT DISTINCT ON (name_key) name_key, canonical_name
        FROM (
            -- A canonical name maps to itself. Priority 0 so that if a name is BOTH somebody's
            -- canonical name and somebody else's legacy form, being canonical wins.
            SELECT LOWER(alias_name) AS name_key, alias_name AS canonical_name, 0 AS priority
            FROM player_aliases
            WHERE alias_name IS NOT NULL

            UNION ALL

            -- Legacy form maps to the canonical name, but only where the mapping is
            -- unambiguous. 39 legacy names map to several full names and some of those are
            -- genuinely different people -- "A Shukla" is both Arpit and Ayush Shukla -- so
            -- collapsing them would merge two careers into one. Those are left unmapped, which
            -- keeps them split exactly as they are today rather than confidently wrong.
            SELECT LOWER(pa.player_name) AS name_key, pa.alias_name AS canonical_name, 1 AS priority
            FROM player_aliases pa
            JOIN (
                SELECT player_name
                FROM player_aliases
                WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
                GROUP BY player_name
                HAVING COUNT(DISTINCT alias_name) = 1
            ) unambiguous ON unambiguous.player_name = pa.player_name
            WHERE pa.player_name IS NOT NULL AND pa.alias_name IS NOT NULL
        ) mapped
        -- DISTINCT ON without ORDER BY returns an arbitrary row, which would make results vary
        -- between runs for no reason. Order so the choice is deterministic.
        ORDER BY name_key, priority, canonical_name
    )
"""


# A join-able source of unambiguous legacy -> canonical pairs, for the older call sites that
# already reference `<alias>.alias_name` and only need the fan-out removed. `player_aliases` has
# no uniqueness on either column, so joining it directly multiplies rows -- and therefore
# double-counts every aggregate -- for the 39 legacy names that map to several full names.
# Those same names are excluded here rather than arbitrarily collapsed, for the reason given
# in ALIAS_MAP_CTE.
UNAMBIGUOUS_ALIASES = """(
            SELECT pa.player_name, pa.alias_name
            FROM player_aliases pa
            JOIN (
                SELECT player_name
                FROM player_aliases
                WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
                GROUP BY player_name
                HAVING COUNT(DISTINCT alias_name) = 1
            ) unambiguous ON unambiguous.player_name = pa.player_name
        )"""


def canonical_name_sql(name_column: str, alias: str = "am") -> str:
    """The expression to select and group by, in place of the raw name column.

    Falls back to the stored name when there is no mapping -- players with no alias, and the
    ambiguous ones we deliberately skip.
    """
    return f"COALESCE({alias}.canonical_name, {name_column})"


def alias_map_join_sql(name_column: str, alias: str = "am") -> str:
    """The join that attaches the canonical name.

    LEFT JOIN against the deduplicated CTE, never against player_aliases directly: that table
    has no uniqueness on either column, so a bare join fans out rows wherever a name has more
    than one alias and silently double-counts every aggregate.
    """
    return f"LEFT JOIN alias_map {alias} ON LOWER({name_column}) = {alias}.name_key"
