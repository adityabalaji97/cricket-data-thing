from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import date, timedelta
import logging
import random
import math

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


def get_player_doppelgangers(
    player_name: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_matches: int = 10,
    top_n: int = 5,
    role: Optional[str] = None
) -> Dict:
    """
    Find most similar and dissimilar players using role-aware, normalized player-level metrics.
    Similarity is based on Euclidean distance over z-scored batting/bowling feature vectors.
    """
    defaults = get_default_params()
    start = start_date or defaults["start_date"]
    end = end_date or defaults["end_date"]

    names = get_player_names(player_name, db)
    resolved_name = names["legacy_name"]
    requested_role = role.lower().strip() if role else None
    valid_roles = {"batter", "bowler", "all_rounder"}
    if requested_role and requested_role not in valid_roles:
        return {
            "found": False,
            "error": f"Invalid role '{role}'. Expected one of: batter, bowler, all_rounder"
        }

    params = {"start_date": start, "end_date": end}

    batting_query = text("""
        SELECT
            bs.striker AS player_name,
            COUNT(DISTINCT bs.match_id) AS batting_matches,
            COALESCE(SUM(bs.runs), 0) AS batting_runs,
            COALESCE(SUM(bs.balls_faced), 0) AS batting_balls,
            COALESCE(SUM(bs.dots), 0) AS batting_dots,
            COALESCE(SUM(bs.fours), 0) AS fours,
            COALESCE(SUM(bs.sixes), 0) AS sixes,
            COALESCE(SUM(bs.wickets), 0) AS dismissals,
            COALESCE(SUM(bs.pp_runs), 0) AS pp_runs,
            COALESCE(SUM(bs.pp_balls), 0) AS pp_balls,
            COALESCE(SUM(bs.pp_dots), 0) AS pp_dots,
            COALESCE(SUM(bs.pp_boundaries), 0) AS pp_boundaries,
            COALESCE(SUM(bs.middle_runs), 0) AS middle_runs,
            COALESCE(SUM(bs.middle_balls), 0) AS middle_balls,
            COALESCE(SUM(bs.middle_dots), 0) AS middle_dots,
            COALESCE(SUM(bs.middle_boundaries), 0) AS middle_boundaries,
            COALESCE(SUM(bs.death_runs), 0) AS death_runs,
            COALESCE(SUM(bs.death_balls), 0) AS death_balls,
            COALESCE(SUM(bs.death_dots), 0) AS death_dots,
            COALESCE(SUM(bs.death_boundaries), 0) AS death_boundaries
        FROM batting_stats bs
        JOIN matches m ON bs.match_id = m.id
        WHERE m.date >= :start_date AND m.date <= :end_date
        GROUP BY bs.striker
    """)

    bowling_query = text("""
        SELECT
            bw.bowler AS player_name,
            COUNT(DISTINCT bw.match_id) AS bowling_matches,
            COALESCE(SUM(bw.runs_conceded), 0) AS runs_conceded,
            COALESCE(SUM(bw.wickets), 0) AS wickets,
            COALESCE(SUM(bw.dots), 0) AS bowling_dots,
            COALESCE(SUM(
                CAST(
                    FLOOR(COALESCE(bw.overs, 0)) * 6 +
                    ROUND((COALESCE(bw.overs, 0) - FLOOR(COALESCE(bw.overs, 0))) * 10)
                AS INTEGER)
            ), 0) AS bowling_balls,
            COALESCE(SUM(bw.pp_runs), 0) AS pp_runs,
            COALESCE(SUM(bw.pp_dots), 0) AS pp_dots,
            COALESCE(SUM(
                CAST(
                    FLOOR(COALESCE(bw.pp_overs, 0)) * 6 +
                    ROUND((COALESCE(bw.pp_overs, 0) - FLOOR(COALESCE(bw.pp_overs, 0))) * 10)
                AS INTEGER)
            ), 0) AS pp_balls,
            COALESCE(SUM(bw.middle_runs), 0) AS middle_runs,
            COALESCE(SUM(bw.middle_dots), 0) AS middle_dots,
            COALESCE(SUM(
                CAST(
                    FLOOR(COALESCE(bw.middle_overs, 0)) * 6 +
                    ROUND((COALESCE(bw.middle_overs, 0) - FLOOR(COALESCE(bw.middle_overs, 0))) * 10)
                AS INTEGER)
            ), 0) AS middle_balls,
            COALESCE(SUM(bw.death_runs), 0) AS death_runs,
            COALESCE(SUM(bw.death_dots), 0) AS death_dots,
            COALESCE(SUM(
                CAST(
                    FLOOR(COALESCE(bw.death_overs, 0)) * 6 +
                    ROUND((COALESCE(bw.death_overs, 0) - FLOOR(COALESCE(bw.death_overs, 0))) * 10)
                AS INTEGER)
            ), 0) AS death_balls
        FROM bowling_stats bw
        JOIN matches m ON bw.match_id = m.id
        WHERE m.date >= :start_date AND m.date <= :end_date
        GROUP BY bw.bowler
    """)

    batting_rows = db.execute(batting_query, params).fetchall()
    bowling_rows = db.execute(bowling_query, params).fetchall()

    player_map: Dict[str, Dict[str, Any]] = {}

    def _get_player_record(name: str) -> Dict[str, Any]:
        if name not in player_map:
            player_map[name] = {
                "player_name": name,
                "batting": {},
                "bowling": {}
            }
        return player_map[name]

    for row in batting_rows:
        rec = _get_player_record(row.player_name)
        rec["batting"] = dict(row._mapping)

    for row in bowling_rows:
        rec = _get_player_record(row.player_name)
        rec["bowling"] = dict(row._mapping)

    batting_metric_defs = [
        {"key": "batting_average", "label": "Bat Avg", "higher_is_better": True},
        {"key": "batting_strike_rate", "label": "Bat SR", "higher_is_better": True},
        {"key": "batting_dot_percentage", "label": "Bat Dot%", "higher_is_better": False},
        {"key": "batting_boundary_percentage", "label": "Bat Bnd%", "higher_is_better": True},
        {"key": "pp_strike_rate", "label": "PP SR", "higher_is_better": True},
        {"key": "middle_strike_rate", "label": "Mid SR", "higher_is_better": True},
        {"key": "death_strike_rate", "label": "Death SR", "higher_is_better": True},
        {"key": "pp_boundary_percentage", "label": "PP Bnd%", "higher_is_better": True},
        {"key": "middle_boundary_percentage", "label": "Mid Bnd%", "higher_is_better": True},
        {"key": "death_boundary_percentage", "label": "Death Bnd%", "higher_is_better": True},
    ]
    bowling_metric_defs = [
        {"key": "bowling_economy", "label": "Econ", "higher_is_better": False},
        {"key": "bowling_strike_rate", "label": "Bowl SR", "higher_is_better": False},
        {"key": "bowling_dot_percentage", "label": "Bowl Dot%", "higher_is_better": True},
        {"key": "pp_economy", "label": "PP Econ", "higher_is_better": False},
        {"key": "middle_economy", "label": "Mid Econ", "higher_is_better": False},
        {"key": "death_economy", "label": "Death Econ", "higher_is_better": False},
        {"key": "pp_dot_percentage", "label": "PP Dot%", "higher_is_better": True},
        {"key": "middle_dot_percentage", "label": "Mid Dot%", "higher_is_better": True},
        {"key": "death_dot_percentage", "label": "Death Dot%", "higher_is_better": True},
    ]

    def _pct(num: float, den: float) -> float:
        return (num * 100.0 / den) if den else 0.0

    def _rate_per_100(num: float, den: float) -> float:
        return (num * 100.0 / den) if den else 0.0

    def _economy(runs: float, balls: float) -> float:
        return (runs * 6.0 / balls) if balls else 0.0

    def _strike_rate_bowling(balls: float, wickets: float) -> float:
        return (balls / wickets) if wickets else 0.0

    def _batting_metrics(b: Dict[str, Any]) -> Dict[str, float]:
        runs = float(b.get("batting_runs") or 0)
        balls = float(b.get("batting_balls") or 0)
        dots = float(b.get("batting_dots") or 0)
        boundaries = float((b.get("fours") or 0) + (b.get("sixes") or 0))
        dismissals = float(b.get("dismissals") or 0)
        pp_runs = float(b.get("pp_runs") or 0)
        pp_balls = float(b.get("pp_balls") or 0)
        pp_boundaries = float(b.get("pp_boundaries") or 0)
        middle_runs = float(b.get("middle_runs") or 0)
        middle_balls = float(b.get("middle_balls") or 0)
        middle_boundaries = float(b.get("middle_boundaries") or 0)
        death_runs = float(b.get("death_runs") or 0)
        death_balls = float(b.get("death_balls") or 0)
        death_boundaries = float(b.get("death_boundaries") or 0)

        return {
            "batting_average": round((runs / dismissals) if dismissals else 0.0, 3),
            "batting_strike_rate": round(_rate_per_100(runs, balls), 3),
            "batting_dot_percentage": round(_pct(dots, balls), 3),
            "batting_boundary_percentage": round(_pct(boundaries, balls), 3),
            "pp_strike_rate": round(_rate_per_100(pp_runs, pp_balls), 3),
            "middle_strike_rate": round(_rate_per_100(middle_runs, middle_balls), 3),
            "death_strike_rate": round(_rate_per_100(death_runs, death_balls), 3),
            "pp_boundary_percentage": round(_pct(pp_boundaries, pp_balls), 3),
            "middle_boundary_percentage": round(_pct(middle_boundaries, middle_balls), 3),
            "death_boundary_percentage": round(_pct(death_boundaries, death_balls), 3),
        }

    def _bowling_metrics(bw: Dict[str, Any]) -> Dict[str, float]:
        runs = float(bw.get("runs_conceded") or 0)
        wickets = float(bw.get("wickets") or 0)
        balls = float(bw.get("bowling_balls") or 0)
        dots = float(bw.get("bowling_dots") or 0)
        pp_runs = float(bw.get("pp_runs") or 0)
        pp_balls = float(bw.get("pp_balls") or 0)
        pp_dots = float(bw.get("pp_dots") or 0)
        middle_runs = float(bw.get("middle_runs") or 0)
        middle_balls = float(bw.get("middle_balls") or 0)
        middle_dots = float(bw.get("middle_dots") or 0)
        death_runs = float(bw.get("death_runs") or 0)
        death_balls = float(bw.get("death_balls") or 0)
        death_dots = float(bw.get("death_dots") or 0)

        return {
            "bowling_economy": round(_economy(runs, balls), 3),
            "bowling_strike_rate": round(_strike_rate_bowling(balls, wickets), 3),
            "bowling_dot_percentage": round(_pct(dots, balls), 3),
            "pp_economy": round(_economy(pp_runs, pp_balls), 3),
            "middle_economy": round(_economy(middle_runs, middle_balls), 3),
            "death_economy": round(_economy(death_runs, death_balls), 3),
            "pp_dot_percentage": round(_pct(pp_dots, pp_balls), 3),
            "middle_dot_percentage": round(_pct(middle_dots, middle_balls), 3),
            "death_dot_percentage": round(_pct(death_dots, death_balls), 3),
        }

    def _classify_role(batting_matches: int, bowling_matches: int) -> str:
        total_matches = max(batting_matches, bowling_matches)
        if total_matches > 0 and bowling_matches >= 8:
            if batting_matches >= 0.4 * total_matches and bowling_matches >= 0.4 * total_matches:
                return "all_rounder"
        if bowling_matches >= batting_matches and bowling_matches >= 8:
            return "bowler"
        if batting_matches >= (2 * bowling_matches) or bowling_matches < 8:
            return "batter"
        return "all_rounder"

    players = []
    for name, rec in player_map.items():
        batting = rec.get("batting") or {}
        bowling = rec.get("bowling") or {}
        batting_matches = int(batting.get("batting_matches") or 0)
        bowling_matches = int(bowling.get("bowling_matches") or 0)
        total_matches = max(batting_matches, bowling_matches)
        if total_matches == 0:
            continue

        player_role = _classify_role(batting_matches, bowling_matches)
        batting_metrics = _batting_metrics(batting)
        bowling_metrics = _bowling_metrics(bowling)
        combined_metrics = {**batting_metrics, **bowling_metrics}

        players.append({
            "player_name": name,
            "batting_matches": batting_matches,
            "bowling_matches": bowling_matches,
            "matches": total_matches,
            "player_role": player_role,
            "batting_metrics": batting_metrics,
            "bowling_metrics": bowling_metrics,
            "all_rounder_metrics": combined_metrics,
        })

    target_any = next((p for p in players if p["player_name"] == resolved_name), None)
    if not target_any:
        return {
            "found": False,
            "error": f"Player '{player_name}' not found in player pool for selected date range",
            "player_pool_size": len(players)
        }

    comparison_role = requested_role or target_any["player_role"]

    def _qualifies_for_pool(p: Dict[str, Any], pool_role: str) -> bool:
        if pool_role == "batter":
            # Batter-mode comparisons should include pure batters and all-rounders
            # if they have enough batting sample size.
            return p["batting_matches"] >= min_matches
        if pool_role == "bowler":
            # Bowler-mode comparisons should include pure bowlers and all-rounders
            # if they have enough bowling sample size.
            return p["bowling_matches"] >= min_matches
        # All-rounder-mode remains role-strict and requires volume on both sides.
        if p["player_role"] != "all_rounder":
            return False
        return p["matches"] >= min_matches and p["bowling_matches"] >= 8 and p["batting_matches"] >= max(1, int(math.ceil(0.4 * p["matches"])))

    role_metric_defs = {
        "batter": batting_metric_defs,
        "bowler": bowling_metric_defs,
        "all_rounder": batting_metric_defs + bowling_metric_defs,
    }
    metric_key_to_def = {m["key"]: m for m in role_metric_defs[comparison_role]}

    role_metric_field = {
        "batter": "batting_metrics",
        "bowler": "bowling_metrics",
        "all_rounder": "all_rounder_metrics",
    }[comparison_role]

    candidate_pool = [p for p in players if _qualifies_for_pool(p, comparison_role)]
    target = next((p for p in candidate_pool if p["player_name"] == resolved_name), None)
    if not target:
        return {
            "found": False,
            "error": f"Player '{player_name}' not found in qualified {comparison_role} pool",
            "player_role": target_any["player_role"],
            "comparison_role": comparison_role,
            "qualified_players": len(candidate_pool)
        }

    feature_names = [m["key"] for m in role_metric_defs[comparison_role]]
    zscore_stats = {}
    percentile_stats = {}
    for feature in feature_names:
        vals = [float(p[role_metric_field][feature]) for p in candidate_pool]
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(variance)
        zscore_stats[feature] = {"mean": mean, "std": std if std > 0 else 1.0}
        percentile_stats[feature] = {
            "values": vals,
            "mean": round(mean, 3)
        }

    all_rounder_weight = math.sqrt(0.5)

    def _zscore_vector(player_record: Dict[str, Any]) -> List[float]:
        vec = []
        for f in feature_names:
            raw = float(player_record[role_metric_field][f])
            z = (raw - zscore_stats[f]["mean"]) / zscore_stats[f]["std"]
            if comparison_role == "all_rounder":
                z *= all_rounder_weight
            vec.append(z)
        return vec

    def _percentile(feature: str, raw_value: float) -> float:
        vals = percentile_stats[feature]["values"]
        metric_def = metric_key_to_def[feature]
        better_count = 0
        equal_count = 0
        for v in vals:
            if metric_def["higher_is_better"]:
                if v < raw_value:
                    better_count += 1
                elif v == raw_value:
                    equal_count += 1
            else:
                if v > raw_value:
                    better_count += 1
                elif v == raw_value:
                    equal_count += 1
        # Mid-rank percentile where higher is always better after direction adjustment
        return round(((better_count + (equal_count * 0.5)) * 100.0) / max(len(vals), 1), 1)

    def _build_radar_metrics(player_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        metrics = player_record[role_metric_field]
        return [
            {
                "metric": metric_def["label"],
                "key": metric_def["key"],
                "percentile": _percentile(metric_def["key"], float(metrics[metric_def["key"]])),
                "raw_value": round(float(metrics[metric_def["key"]]), 3),
                "league_avg": percentile_stats[metric_def["key"]]["mean"],
                "higher_is_better": metric_def["higher_is_better"],
            }
            for metric_def in role_metric_defs[comparison_role]
        ]

    target_vec = _zscore_vector(target)
    scored = []
    for p in candidate_pool:
        if p["player_name"] == resolved_name:
            continue
        vec = _zscore_vector(p)
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(target_vec, vec)))
        scored.append({
            "player_name": p["player_name"],
            "distance": round(distance, 4),
            "matches": p["matches"],
            "batting_matches": p["batting_matches"],
            "bowling_matches": p["bowling_matches"],
            "player_role": p["player_role"],
            "metrics": p[role_metric_field],
            "radar_metrics": _build_radar_metrics(p),
        })

    scored.sort(key=lambda x: x["distance"])
    similar = scored[:top_n]
    dissimilar = list(reversed(scored[-top_n:])) if scored else []

    league_averages = {
        metric_def["key"]: {
            "label": metric_def["label"],
            "value": percentile_stats[metric_def["key"]]["mean"],
            "higher_is_better": metric_def["higher_is_better"],
        }
        for metric_def in role_metric_defs[comparison_role]
    }

    return {
        "found": True,
        "player_name": resolved_name,
        "display_name": names["details_name"],
        "date_range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "min_matches": min_matches,
        "player_role": target_any["player_role"],
        "comparison_role": comparison_role,
        "role_overridden": bool(requested_role),
        "feature_space": feature_names,
        "qualified_players": len(candidate_pool),
        "target_metrics": target[role_metric_field],
        "target_radar_metrics": _build_radar_metrics(target),
        "league_averages": league_averages,
        "most_similar": similar,
        "most_dissimilar": dissimilar
    }


def get_doppelganger_leaderboard(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_batting_innings: int = 25,
    min_bowling_balls: int = 240,
    top_n_pairs: int = 10,
    max_players_per_role: int = 300
) -> Dict[str, Any]:
    """
    Global doppelganger leaderboard across qualified batters and bowlers.

    Filters are restricted to:
    - top 5 franchise leagues
    - internationals involving top 10 ranked teams (both teams in top-10)
    """
    from models import INTERNATIONAL_TEAMS_RANKED

    defaults = get_default_params()
    start = start_date or defaults["start_date"]
    end = end_date or defaults["end_date"]

    top_leagues = ["IPL", "BBL", "PSL", "CPL", "SA20"]
    top_teams = INTERNATIONAL_TEAMS_RANKED[:10]

    params = {
        "start_date": start,
        "end_date": end,
        "top_leagues": top_leagues,
        "top_teams": top_teams,
    }

    competition_filter = """
        AND (
            (m.match_type = 'league' AND m.competition = ANY(:top_leagues))
            OR
            (m.match_type = 'international' AND m.team1 = ANY(:top_teams) AND m.team2 = ANY(:top_teams))
        )
    """

    batting_query = text(f"""
        SELECT
            bs.striker AS player_name,
            COUNT(*) AS batting_innings,
            COUNT(DISTINCT bs.match_id) AS batting_matches,
            COALESCE(SUM(bs.runs), 0) AS batting_runs,
            COALESCE(SUM(bs.balls_faced), 0) AS batting_balls,
            COALESCE(SUM(bs.dots), 0) AS batting_dots,
            COALESCE(SUM(bs.fours), 0) AS fours,
            COALESCE(SUM(bs.sixes), 0) AS sixes,
            COALESCE(SUM(bs.wickets), 0) AS dismissals,
            COALESCE(SUM(bs.pp_runs), 0) AS pp_runs,
            COALESCE(SUM(bs.pp_balls), 0) AS pp_balls,
            COALESCE(SUM(bs.pp_dots), 0) AS pp_dots,
            COALESCE(SUM(bs.pp_boundaries), 0) AS pp_boundaries,
            COALESCE(SUM(bs.middle_runs), 0) AS middle_runs,
            COALESCE(SUM(bs.middle_balls), 0) AS middle_balls,
            COALESCE(SUM(bs.middle_dots), 0) AS middle_dots,
            COALESCE(SUM(bs.middle_boundaries), 0) AS middle_boundaries,
            COALESCE(SUM(bs.death_runs), 0) AS death_runs,
            COALESCE(SUM(bs.death_balls), 0) AS death_balls,
            COALESCE(SUM(bs.death_dots), 0) AS death_dots,
            COALESCE(SUM(bs.death_boundaries), 0) AS death_boundaries
        FROM batting_stats bs
        JOIN matches m ON bs.match_id = m.id
        WHERE m.date >= :start_date AND m.date <= :end_date
        {competition_filter}
        GROUP BY bs.striker
    """)

    bowling_query = text(f"""
        SELECT
            bw.bowler AS player_name,
            COUNT(*) AS bowling_innings,
            COUNT(DISTINCT bw.match_id) AS bowling_matches,
            COALESCE(SUM(bw.runs_conceded), 0) AS runs_conceded,
            COALESCE(SUM(bw.wickets), 0) AS wickets,
            COALESCE(SUM(bw.dots), 0) AS bowling_dots,
            COALESCE(SUM(
                CAST(
                    FLOOR(COALESCE(bw.overs, 0)) * 6 +
                    ROUND((COALESCE(bw.overs, 0) - FLOOR(COALESCE(bw.overs, 0))) * 10)
                AS INTEGER)
            ), 0) AS bowling_balls,
            COALESCE(SUM(bw.pp_runs), 0) AS pp_runs,
            COALESCE(SUM(bw.pp_dots), 0) AS pp_dots,
            COALESCE(SUM(
                CAST(
                    FLOOR(COALESCE(bw.pp_overs, 0)) * 6 +
                    ROUND((COALESCE(bw.pp_overs, 0) - FLOOR(COALESCE(bw.pp_overs, 0))) * 10)
                AS INTEGER)
            ), 0) AS pp_balls,
            COALESCE(SUM(bw.middle_runs), 0) AS middle_runs,
            COALESCE(SUM(bw.middle_dots), 0) AS middle_dots,
            COALESCE(SUM(
                CAST(
                    FLOOR(COALESCE(bw.middle_overs, 0)) * 6 +
                    ROUND((COALESCE(bw.middle_overs, 0) - FLOOR(COALESCE(bw.middle_overs, 0))) * 10)
                AS INTEGER)
            ), 0) AS middle_balls,
            COALESCE(SUM(bw.death_runs), 0) AS death_runs,
            COALESCE(SUM(bw.death_dots), 0) AS death_dots,
            COALESCE(SUM(
                CAST(
                    FLOOR(COALESCE(bw.death_overs, 0)) * 6 +
                    ROUND((COALESCE(bw.death_overs, 0) - FLOOR(COALESCE(bw.death_overs, 0))) * 10)
                AS INTEGER)
            ), 0) AS death_balls
        FROM bowling_stats bw
        JOIN matches m ON bw.match_id = m.id
        WHERE m.date >= :start_date AND m.date <= :end_date
        {competition_filter}
        GROUP BY bw.bowler
    """)

    batting_rows = db.execute(batting_query, params).fetchall()
    bowling_rows = db.execute(bowling_query, params).fetchall()

    def _pct(num: float, den: float) -> float:
        return (num * 100.0 / den) if den else 0.0

    def _rate_per_100(num: float, den: float) -> float:
        return (num * 100.0 / den) if den else 0.0

    def _economy(runs: float, balls: float) -> float:
        return (runs * 6.0 / balls) if balls else 0.0

    def _bowling_sr(balls: float, wickets: float) -> float:
        return (balls / wickets) if wickets else 0.0

    batting_metric_defs = [
        "batting_average",
        "batting_strike_rate",
        "batting_dot_percentage",
        "batting_boundary_percentage",
        "pp_strike_rate",
        "middle_strike_rate",
        "death_strike_rate",
        "pp_boundary_percentage",
        "middle_boundary_percentage",
        "death_boundary_percentage",
    ]
    bowling_metric_defs = [
        "bowling_economy",
        "bowling_strike_rate",
        "bowling_dot_percentage",
        "pp_economy",
        "middle_economy",
        "death_economy",
        "pp_dot_percentage",
        "middle_dot_percentage",
        "death_dot_percentage",
    ]

    batters: List[Dict[str, Any]] = []
    for row in batting_rows:
        innings = int(row.batting_innings or 0)
        if innings < min_batting_innings:
            continue
        runs = float(row.batting_runs or 0)
        balls = float(row.batting_balls or 0)
        dots = float(row.batting_dots or 0)
        boundaries = float((row.fours or 0) + (row.sixes or 0))
        dismissals = float(row.dismissals or 0)
        metrics = {
            "batting_average": round((runs / dismissals) if dismissals else 0.0, 3),
            "batting_strike_rate": round(_rate_per_100(runs, balls), 3),
            "batting_dot_percentage": round(_pct(dots, balls), 3),
            "batting_boundary_percentage": round(_pct(boundaries, balls), 3),
            "pp_strike_rate": round(_rate_per_100(float(row.pp_runs or 0), float(row.pp_balls or 0)), 3),
            "middle_strike_rate": round(_rate_per_100(float(row.middle_runs or 0), float(row.middle_balls or 0)), 3),
            "death_strike_rate": round(_rate_per_100(float(row.death_runs or 0), float(row.death_balls or 0)), 3),
            "pp_boundary_percentage": round(_pct(float(row.pp_boundaries or 0), float(row.pp_balls or 0)), 3),
            "middle_boundary_percentage": round(_pct(float(row.middle_boundaries or 0), float(row.middle_balls or 0)), 3),
            "death_boundary_percentage": round(_pct(float(row.death_boundaries or 0), float(row.death_balls or 0)), 3),
        }
        batters.append({
            "player_name": row.player_name,
            "innings": innings,
            "matches": int(row.batting_matches or 0),
            "balls": int(row.batting_balls or 0),
            "metrics": metrics,
        })

    bowlers: List[Dict[str, Any]] = []
    for row in bowling_rows:
        balls = int(row.bowling_balls or 0)
        if balls < min_bowling_balls:
            continue
        wickets = float(row.wickets or 0)
        metrics = {
            "bowling_economy": round(_economy(float(row.runs_conceded or 0), float(balls)), 3),
            "bowling_strike_rate": round(_bowling_sr(float(balls), wickets), 3),
            "bowling_dot_percentage": round(_pct(float(row.bowling_dots or 0), float(balls)), 3),
            "pp_economy": round(_economy(float(row.pp_runs or 0), float(row.pp_balls or 0)), 3),
            "middle_economy": round(_economy(float(row.middle_runs or 0), float(row.middle_balls or 0)), 3),
            "death_economy": round(_economy(float(row.death_runs or 0), float(row.death_balls or 0)), 3),
            "pp_dot_percentage": round(_pct(float(row.pp_dots or 0), float(row.pp_balls or 0)), 3),
            "middle_dot_percentage": round(_pct(float(row.middle_dots or 0), float(row.middle_balls or 0)), 3),
            "death_dot_percentage": round(_pct(float(row.death_dots or 0), float(row.death_balls or 0)), 3),
        }
        bowlers.append({
            "player_name": row.player_name,
            "innings": int(row.bowling_innings or 0),
            "matches": int(row.bowling_matches or 0),
            "balls": balls,
            "wickets": int(row.wickets or 0),
            "metrics": metrics,
        })

    def _build_pair_leaderboard(pool: List[Dict[str, Any]], feature_names: List[str], role_label: str) -> Dict[str, Any]:
        if len(pool) < 2:
            return {
                "role": role_label,
                "qualified_players": len(pool),
                "most_similar": [],
                "most_dissimilar": [],
                "feature_space": feature_names,
                "warning": "Not enough qualified players"
            }

        # Keep computation bounded on very broad ranges/cutoffs.
        if len(pool) > max_players_per_role:
            pool = sorted(pool, key=lambda p: (p["matches"], p["balls"]), reverse=True)[:max_players_per_role]
            warning = f"Capped pool to top {max_players_per_role} players by volume for performance"
        else:
            warning = None

        stats = {}
        for feature in feature_names:
            vals = [float(p["metrics"][feature]) for p in pool]
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals)
            std = math.sqrt(variance)
            stats[feature] = {"mean": mean, "std": std if std > 0 else 1.0}

        vectors = {}
        for p in pool:
            vectors[p["player_name"]] = [
                (float(p["metrics"][f]) - stats[f]["mean"]) / stats[f]["std"]
                for f in feature_names
            ]

        indexed = {p["player_name"]: p for p in pool}
        pairs = []
        for i in range(len(pool)):
            p1 = pool[i]
            v1 = vectors[p1["player_name"]]
            for j in range(i + 1, len(pool)):
                p2 = pool[j]
                v2 = vectors[p2["player_name"]]
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
                pairs.append({
                    "player1": p1["player_name"],
                    "player2": p2["player_name"],
                    "distance": round(dist, 4),
                    "player1_matches": p1["matches"],
                    "player2_matches": p2["matches"],
                    "player1_innings": p1["innings"],
                    "player2_innings": p2["innings"],
                    "player1_balls": p1["balls"],
                    "player2_balls": p2["balls"],
                })

        pairs.sort(key=lambda x: x["distance"])
        return {
            "role": role_label,
            "qualified_players": len(pool),
            "feature_space": feature_names,
            "most_similar": pairs[:top_n_pairs],
            "most_dissimilar": list(reversed(pairs[-top_n_pairs:])),
            "warning": warning,
        }

    batter_board = _build_pair_leaderboard(batters, batting_metric_defs, "batter")
    bowler_board = _build_pair_leaderboard(bowlers, bowling_metric_defs, "bowler")

    return {
        "success": True,
        "date_range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "filters": {
            "top_leagues": top_leagues,
            "top_international_teams": top_teams,
            "min_batting_innings": min_batting_innings,
            "min_bowling_balls": min_bowling_balls,
            "top_n_pairs": top_n_pairs,
        },
        "batters": batter_board,
        "bowlers": bowler_board,
    }
