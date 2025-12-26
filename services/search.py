from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import date, timedelta
import logging
import random

from services.player_aliases import (
    resolve_to_legacy_name,
    get_player_names,
    search_players_with_aliases
)

logger = logging.getLogger(__name__)

# Default parameters for searches
def get_default_params():
    today = date.today()
    return {
        "start_date": date(today.year - 1, 1, 1),  # Jan 1 of previous year
        "end_date": today,
        "leagues": [],
        "include_international": True,
        "top_teams": 20
    }


def search_entities(query: str, db: Session, limit: int = 10) -> List[Dict]:
    """
    Unified search across players, teams, and venues.
    Returns results ranked by relevance (exact > prefix > contains).
    
    Player search includes alias matching - searching "Virat Kohli" 
    will find "V Kohli" and show "Virat Kohli" as display name.
    Returns both legacy_name (for routing) and display_name (for UI).
    """
    if not query or len(query.strip()) < 2:
        return []
    
    search_term = query.strip()
    search_lower = search_term.lower()
    
    try:
        # Search players with alias support (returns deduplicated with both names)
        players = search_players_with_aliases(query, db, limit)
        
        # Search teams - use subquery
        team_query = text("""
            SELECT name, type FROM (
                SELECT DISTINCT batting_team as name, 'team' as type
                FROM batting_stats
                WHERE LOWER(batting_team) LIKE :search_pattern
                UNION
                SELECT DISTINCT bowling_team as name, 'team' as type
                FROM bowling_stats
                WHERE LOWER(bowling_team) LIKE :search_pattern
            ) t
            ORDER BY name
            LIMIT :limit
        """)
        
        # Search venues - use subquery
        venue_query = text("""
            SELECT name, type FROM (
                SELECT DISTINCT venue as name, 'venue' as type
                FROM matches
                WHERE venue IS NOT NULL 
                AND LOWER(venue) LIKE :search_pattern
            ) v
            ORDER BY 
                CASE 
                    WHEN LOWER(name) = :exact THEN 1
                    WHEN LOWER(name) LIKE :prefix THEN 2
                    ELSE 3
                END,
                name
            LIMIT :limit
        """)
        
        params = {
            "search_pattern": f"%{search_lower}%",
            "exact": search_lower,
            "prefix": f"{search_lower}%",
            "limit": limit
        }
        
        teams = db.execute(team_query, params).fetchall()
        venues = db.execute(venue_query, params).fetchall()
        
        # Combine and format results
        results = []
        
        # Players already formatted from search_players_with_aliases
        # Each has: name, display_name, details_name, type
        results.extend(players)
        
        for row in teams:
            results.append({
                "name": row.name, 
                "display_name": row.name,
                "type": row.type
            })
        for row in venues:
            results.append({
                "name": row.name, 
                "display_name": row.name,
                "type": row.type
            })
        
        # Sort combined results by relevance (using display_name for matching)
        def relevance_key(item):
            # Use display_name for relevance scoring
            name_lower = item.get("display_name", item["name"]).lower()
            if name_lower == search_lower:
                return (0, item.get("display_name", item["name"]))
            elif name_lower.startswith(search_lower):
                return (1, item.get("display_name", item["name"]))
            else:
                return (2, item.get("display_name", item["name"]))
        
        results.sort(key=relevance_key)
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error in search_entities: {str(e)}")
        raise


def get_random_entity(db: Session) -> Dict:
    """
    Get a random entity (player, team, or venue) for 'I'm Feeling Lucky'.
    """
    try:
        entity_type = random.choice(["player", "team", "venue"])
        
        if entity_type == "player":
            query = text("""
                SELECT name FROM players 
                ORDER BY RANDOM() 
                LIMIT 1
            """)
        elif entity_type == "team":
            query = text("""
                SELECT name FROM (
                    SELECT DISTINCT batting_team as name FROM batting_stats
                ) teams
                ORDER BY RANDOM() 
                LIMIT 1
            """)
        else:  # venue
            query = text("""
                SELECT name FROM (
                    SELECT DISTINCT venue as name FROM matches WHERE venue IS NOT NULL
                ) venues
                ORDER BY RANDOM() 
                LIMIT 1
            """)
        
        result = db.execute(query).fetchone()
        
        if result:
            if entity_type == "player":
                # Get both names for players
                names = get_player_names(result.name, db)
                return {
                    "name": names["legacy_name"],
                    "display_name": names["details_name"],
                    "details_name": names["details_name"],
                    "type": entity_type
                }
            return {"name": result.name, "display_name": result.name, "type": entity_type}
        
        # Fallback if no result
        return {"name": "V Kohli", "display_name": "Virat Kohli", "type": "player"}
        
    except Exception as e:
        logger.error(f"Error in get_random_entity: {str(e)}")
        raise


def get_player_profile(
    player_name: str, 
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict:
    """
    Get unified player profile with both batting and bowling career stats.
    Uses default date range if not specified.
    
    Supports player aliases - if a new name (from delivery_details) is provided,
    it will be resolved to the legacy name for querying.
    
    Returns both legacy_name and details_name for routing flexibility.
    """
    defaults = get_default_params()
    start = start_date or defaults["start_date"]
    end = end_date or defaults["end_date"]
    
    try:
        # Get both name formats
        names = get_player_names(player_name, db)
        legacy_name = names["legacy_name"]
        details_name = names["details_name"]
        
        # Use legacy name for querying players/deliveries/batting_stats/bowling_stats
        resolved_name = legacy_name
        
        # Get player info
        player_info_query = text("""
            SELECT name, batter_type, bowler_type
            FROM players
            WHERE name = :player_name
        """)
        player_info = db.execute(player_info_query, {"player_name": resolved_name}).fetchone()
        
        if not player_info:
            return {"error": f"Player '{player_name}' not found", "found": False}
        
        # Get batting career stats
        batting_query = text("""
            SELECT
                COUNT(DISTINCT bs.match_id) as matches,
                COUNT(DISTINCT bs.match_id) as innings,
                COALESCE(SUM(bs.runs), 0) as runs,
                COALESCE(SUM(bs.balls_faced), 0) as balls_faced,
                COALESCE(SUM(bs.fours), 0) as fours,
                COALESCE(SUM(bs.sixes), 0) as sixes,
                COALESCE(SUM(bs.dots), 0) as dots,
                COUNT(CASE WHEN bs.runs >= 50 AND bs.runs < 100 THEN 1 END) as fifties,
                COUNT(CASE WHEN bs.runs >= 100 THEN 1 END) as hundreds,
                COUNT(CASE WHEN bs.wickets > 0 THEN 1 END) as dismissals,
                MAX(bs.runs) as highest_score
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = :player_name
            AND m.date >= :start_date
            AND m.date <= :end_date
        """)
        
        batting_stats = db.execute(batting_query, {
            "player_name": resolved_name,
            "start_date": start,
            "end_date": end
        }).fetchone()
        
        # Get bowling career stats
        bowling_query = text("""
            WITH legal_balls AS (
                SELECT 
                    COUNT(*) as total_legal_balls
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.bowler = :player_name
                AND d.wides = 0 AND d.noballs = 0
                AND m.date >= :start_date
                AND m.date <= :end_date
            )
            SELECT
                COUNT(DISTINCT bs.match_id) as matches,
                COALESCE(SUM(bs.runs_conceded), 0) as runs_conceded,
                COALESCE(SUM(bs.wickets), 0) as wickets,
                COALESCE(SUM(bs.dots), 0) as dots,
                lb.total_legal_balls as balls_bowled,
                COUNT(CASE WHEN bs.wickets >= 3 AND bs.wickets < 5 THEN 1 END) as three_wickets,
                COUNT(CASE WHEN bs.wickets >= 5 THEN 1 END) as five_wickets,
                MAX(bs.wickets) as best_wickets
            FROM bowling_stats bs
            JOIN matches m ON bs.match_id = m.id
            CROSS JOIN legal_balls lb
            WHERE bs.bowler = :player_name
            AND m.date >= :start_date
            AND m.date <= :end_date
            GROUP BY lb.total_legal_balls
        """)
        
        bowling_stats = db.execute(bowling_query, {
            "player_name": resolved_name,
            "start_date": start,
            "end_date": end
        }).fetchone()
        
        # Get recent teams
        recent_teams_query = text("""
            SELECT DISTINCT batting_team as team
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = :player_name
            AND m.date >= :start_date
            ORDER BY team
            LIMIT 5
        """)
        recent_teams = db.execute(recent_teams_query, {
            "player_name": resolved_name,
            "start_date": start
        }).fetchall()
        
        # Calculate derived batting stats
        batting_runs = batting_stats.runs or 0
        batting_balls = batting_stats.balls_faced or 0
        batting_dismissals = batting_stats.dismissals or 0
        batting_dots = batting_stats.dots or 0
        
        batting_average = round(batting_runs / batting_dismissals, 2) if batting_dismissals > 0 else 0
        batting_strike_rate = round((batting_runs * 100) / batting_balls, 2) if batting_balls > 0 else 0
        batting_dot_pct = round((batting_dots * 100) / batting_balls, 2) if batting_balls > 0 else 0
        
        # Calculate derived bowling stats
        bowling_runs = bowling_stats.runs_conceded if bowling_stats else 0
        bowling_balls = bowling_stats.balls_bowled if bowling_stats else 0
        bowling_wickets = bowling_stats.wickets if bowling_stats else 0
        bowling_dots = bowling_stats.dots if bowling_stats else 0
        
        bowling_average = round(bowling_runs / bowling_wickets, 2) if bowling_wickets > 0 else 0
        bowling_strike_rate = round(bowling_balls / bowling_wickets, 2) if bowling_wickets > 0 else 0
        bowling_economy = round((bowling_runs * 6) / bowling_balls, 2) if bowling_balls > 0 else 0
        bowling_dot_pct = round((bowling_dots * 100) / bowling_balls, 2) if bowling_balls > 0 else 0
        
        # Determine player role
        has_batting = batting_stats.matches > 0 if batting_stats else False
        has_bowling = bowling_stats and bowling_stats.matches and bowling_stats.matches > 0
        
        if has_batting and has_bowling:
            role = "all-rounder"
        elif has_batting:
            role = "batter"
        elif has_bowling:
            role = "bowler"
        else:
            role = "unknown"
        
        # Return BOTH names for routing flexibility
        return {
            "found": True,
            "player_name": legacy_name,  # For /player, /bowler routes (queries deliveries)
            "display_name": details_name,  # For UI display
            "details_name": details_name,  # For delivery_details queries
            "player_info": {
                "batter_type": player_info.batter_type,
                "bowler_type": player_info.bowler_type,
                "role": role,
                "recent_teams": [t.team for t in recent_teams]
            },
            "date_range": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat()
            },
            "batting": {
                "has_stats": has_batting,
                "matches": batting_stats.matches or 0,
                "innings": batting_stats.innings or 0,
                "runs": batting_runs,
                "balls_faced": batting_balls,
                "average": batting_average,
                "strike_rate": batting_strike_rate,
                "highest_score": batting_stats.highest_score or 0,
                "fifties": batting_stats.fifties or 0,
                "hundreds": batting_stats.hundreds or 0,
                "fours": batting_stats.fours or 0,
                "sixes": batting_stats.sixes or 0,
                "dot_percentage": batting_dot_pct
            },
            "bowling": {
                "has_stats": has_bowling,
                "matches": bowling_stats.matches if bowling_stats else 0,
                "balls": bowling_balls,
                "overs": round(bowling_balls / 6, 1) if bowling_balls else 0,
                "runs_conceded": bowling_runs,
                "wickets": bowling_wickets,
                "average": bowling_average,
                "strike_rate": bowling_strike_rate,
                "economy": bowling_economy,
                "best_wickets": bowling_stats.best_wickets if bowling_stats else 0,
                "three_wickets": bowling_stats.three_wickets if bowling_stats else 0,
                "five_wickets": bowling_stats.five_wickets if bowling_stats else 0,
                "dot_percentage": bowling_dot_pct
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_player_profile: {str(e)}")
        raise
