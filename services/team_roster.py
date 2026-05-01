"""
Team Roster Service

Provides current team rosters with fallback logic:
1. If team has recent IPL matches (last 30 days), discover players from batting_stats/bowling_stats
2. Otherwise, fall back to pre-season hardcoded rosters from ipl_rosters.py
"""

from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, timedelta
import logging

from services.teams import get_all_team_name_variations
from services.player_aliases import get_player_names

logger = logging.getLogger(__name__)


def _discover_roster_from_matches(
    team_name: str,
    db: Session,
    lookback_days: int = 30,
    day_or_night: Optional[str] = None,
) -> Optional[list]:
    """
    Discover team roster from recent match data (batting_stats + bowling_stats).
    Returns None if no recent matches found.
    """
    team_variations = get_all_team_name_variations(team_name)
    cutoff = date.today() - timedelta(days=lookback_days)

    # Check if team has recent matches
    check_query = text("""
        SELECT COUNT(*) FROM matches
        WHERE (team1 = ANY(:teams) OR team2 = ANY(:teams))
          AND date >= :cutoff
          AND competition = 'Indian Premier League'
          AND (:day_or_night IS NULL OR day_or_night = :day_or_night)
    """)
    count = db.execute(
        check_query,
        {"teams": team_variations, "cutoff": cutoff, "day_or_night": day_or_night},
    ).scalar()

    if not count:
        return None

    # Get unique players from batting and bowling stats in recent matches
    players_query = text("""
        WITH recent_match_ids AS (
            SELECT id FROM matches
            WHERE (team1 = ANY(:teams) OR team2 = ANY(:teams))
              AND date >= :cutoff
              AND competition = 'Indian Premier League'
              AND (:day_or_night IS NULL OR day_or_night = :day_or_night)
        ),
        batters AS (
            SELECT DISTINCT bs.player_name as name, 'batter' as source
            FROM batting_stats bs
            WHERE bs.match_id IN (SELECT id FROM recent_match_ids)
              AND bs.team = ANY(:teams)
        ),
        bowlers AS (
            SELECT DISTINCT bw.player_name as name, 'bowler' as source
            FROM bowling_stats bw
            WHERE bw.match_id IN (SELECT id FROM recent_match_ids)
              AND bw.team = ANY(:teams)
        ),
        combined AS (
            SELECT name,
                   CASE
                       WHEN name IN (SELECT name FROM batters) AND name IN (SELECT name FROM bowlers)
                       THEN 'all-rounder'
                       WHEN name IN (SELECT name FROM bowlers)
                       THEN 'bowler'
                       ELSE 'batter'
                   END as role
            FROM (
                SELECT name FROM batters
                UNION
                SELECT name FROM bowlers
            ) all_players
        )
        SELECT name, role FROM combined
        ORDER BY role, name
    """)

    rows = db.execute(
        players_query,
        {"teams": team_variations, "cutoff": cutoff, "day_or_night": day_or_night},
    ).fetchall()

    if not rows:
        return None

    return [{"name": row.name, "role": row.role} for row in rows]


def _get_static_roster(team_name: str) -> Optional[list]:
    """Get roster from hardcoded ipl_rosters.py file."""
    try:
        from ipl_rosters import get_ipl_roster, get_team_abbrev_from_name

        abbrev = get_team_abbrev_from_name(team_name)
        if not abbrev:
            return None

        roster_data = get_ipl_roster(abbrev)
        if not roster_data:
            return None

        return roster_data["players"]
    except ImportError:
        logger.warning("ipl_rosters.py not found - no static roster available")
        return None


def get_team_roster_service(
    team_name: str,
    db: Session,
    lookback_days: int = 30,
    day_or_night: Optional[str] = None,
) -> dict:
    """
    Get current team roster with fallback logic.

    Returns:
        {
            "team": team_name,
            "source": "match_data" | "pre_season",
            "players": [{"name": ..., "role": ..., "display_name": ...}],
            "role_summary": {"batter": N, "bowler": N, "all-rounder": N}
        }
    """
    # Try match data first
    players = _discover_roster_from_matches(
        team_name=team_name,
        db=db,
        lookback_days=lookback_days,
        day_or_night=day_or_night,
    )
    static_players = _get_static_roster(team_name)

    if players:
        source = "match_data"
        # Merge static roster players not already in match data (alias-aware dedup)
        if static_players:
            match_names_lower = {p["name"].lower() for p in players}
            for sp in static_players:
                names = get_player_names(sp["name"], db)
                legacy_lower = (names.get("legacy_name") or "").lower()
                details_lower = (names.get("details_name") or "").lower()
                sp_lower = sp["name"].lower()
                if (sp_lower not in match_names_lower
                        and legacy_lower not in match_names_lower
                        and details_lower not in match_names_lower):
                    players.append(sp)
            source = "match_data_plus_roster"
    elif static_players:
        players = static_players
        source = "pre_season"
    else:
        players = None

    if not players:
        return {
            "team": team_name,
            "source": "none",
            "players": [],
            "role_summary": {},
        }

    # Resolve display names
    enriched = []
    for p in players:
        names = get_player_names(p["name"], db)
        enriched.append({
            "name": names["legacy_name"],
            "display_name": names["details_name"],
            "role": p["role"],
        })

    # Role summary
    role_summary = {}
    for p in enriched:
        role_summary[p["role"]] = role_summary.get(p["role"], 0) + 1

    return {
        "team": team_name,
        "source": source,
        "players": enriched,
        "role_summary": role_summary,
    }
