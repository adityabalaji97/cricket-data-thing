"""
Delivery Data Service - Unified access to delivery data from both tables

Handles routing between deliveries and delivery_details tables based on date ranges.
The deliveries table has data up to 2025-11-27, while delivery_details has data
from 2015-01-01 onwards (including recent matches).

Usage:
    from services.delivery_data_service import get_deliveries_for_venue, get_deliveries_for_match
"""

from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date
import logging

try:
    from venue_standardization import VENUE_STANDARDIZATION
except Exception:  # pragma: no cover - defensive import fallback
    VENUE_STANDARDIZATION = {}

logger = logging.getLogger(__name__)

# Date boundary: delivery_details is most reliable from 2015+
DELIVERY_DETAILS_START_DATE = date(2015, 1, 1)

# Latest date in deliveries table (update this if the table gets refreshed)
DELIVERIES_LAST_DATE = date(2025, 11, 27)


_CANONICAL_TO_VENUE_ALIASES: Dict[str, set] = {}
for _alias, _canonical in (VENUE_STANDARDIZATION or {}).items():
    if not _canonical:
        continue
    _CANONICAL_TO_VENUE_ALIASES.setdefault(_canonical, set()).add(_alias)
    _CANONICAL_TO_VENUE_ALIASES[_canonical].add(_canonical)


def get_venue_aliases(venue: Optional[str]) -> List[str]:
    """Return canonical venue plus known aliases for cross-table matching."""
    if not venue or venue == "All Venues":
        return []

    canonical = VENUE_STANDARDIZATION.get(venue, venue)
    aliases = set(_CANONICAL_TO_VENUE_ALIASES.get(canonical, set()))
    aliases.add(canonical)
    aliases.add(venue)
    return sorted(a for a in aliases if a)


def should_use_delivery_details(start_date: Optional[date], end_date: Optional[date]) -> Dict[str, bool]:
    """
    Determine which table(s) to query based on date range.

    Returns:
        {
            'use_deliveries': bool,
            'use_delivery_details': bool,
            'deliveries_date_range': (start, end) or None,
            'delivery_details_date_range': (start, end) or None
        }
    """
    query_start = start_date or date(2005, 1, 1)
    query_end = end_date or date.today()

    result = {
        'use_deliveries': False,
        'use_delivery_details': False,
        'deliveries_date_range': None,
        'delivery_details_date_range': None
    }

    # If query is entirely before 2015, use only deliveries
    if query_end < DELIVERY_DETAILS_START_DATE:
        result['use_deliveries'] = True
        result['deliveries_date_range'] = (query_start, query_end)
        return result

    # If query is entirely after deliveries last date, use only delivery_details
    if query_start > DELIVERIES_LAST_DATE:
        result['use_delivery_details'] = True
        result['delivery_details_date_range'] = (query_start, query_end)
        return result

    # If query spans both ranges, use delivery_details (it has more complete data from 2015+)
    if query_start >= DELIVERY_DETAILS_START_DATE:
        result['use_delivery_details'] = True
        result['delivery_details_date_range'] = (query_start, query_end)
        return result

    # Query is before 2015, use deliveries
    result['use_deliveries'] = True
    result['deliveries_date_range'] = (query_start, min(query_end, date(2014, 12, 31)))

    # Also check if we need delivery_details for post-2015 portion
    if query_end >= DELIVERY_DETAILS_START_DATE:
        result['use_delivery_details'] = True
        result['delivery_details_date_range'] = (max(query_start, DELIVERY_DETAILS_START_DATE), query_end)

    return result


def build_venue_filter_deliveries(venue: str, params: Dict[str, Any]) -> str:
    """Build venue filter for deliveries table."""
    if venue and venue != "All Venues":
        params["venue_aliases"] = get_venue_aliases(venue)
        return "AND m.venue = ANY(:venue_aliases)"
    return ""


def build_venue_filter_delivery_details(venue: str, params: Dict[str, Any]) -> str:
    """Build venue filter for delivery_details table."""
    if venue and venue != "All Venues":
        params["venue_aliases"] = get_venue_aliases(venue)
        return "AND dd.ground = ANY(:venue_aliases)"
    return ""


def build_competition_filter_deliveries(
    leagues: List[str],
    include_international: bool,
    top_teams: Optional[int],
    params: Dict[str, Any]
) -> str:
    """Build competition filter for deliveries table."""
    from models import INTERNATIONAL_TEAMS_RANKED

    competition_conditions = []

    if leagues and len(leagues) > 0:
        # Specific leagues selected
        competition_conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
    else:
        # All leagues selected — include all league/franchise matches
        competition_conditions.append("m.match_type = 'league'")

    if include_international:
        if top_teams:
            top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            params["top_teams"] = top_team_list
            competition_conditions.append(
                "(m.match_type = 'international' AND m.team1 = ANY(:top_teams) AND m.team2 = ANY(:top_teams))"
            )
        else:
            competition_conditions.append("m.match_type = 'international'")

    if competition_conditions:
        return "AND (" + " OR ".join(competition_conditions) + ")"
    return "AND 1=1"


def build_competition_filter_delivery_details(
    leagues: List[str],
    include_international: bool,
    top_teams: Optional[int],
    params: Dict[str, Any]
) -> str:
    """Build competition filter for delivery_details table."""
    from models import INTERNATIONAL_TEAMS_RANKED

    competition_conditions = []

    if leagues and len(leagues) > 0:
        # Specific leagues selected
        competition_conditions.append("dd.competition = ANY(:leagues)")
    else:
        # All leagues selected — include all non-T20I (franchise/league) matches
        competition_conditions.append("dd.competition != 'T20I'")

    if include_international:
        if top_teams:
            top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            params["top_teams"] = top_team_list
            competition_conditions.append(
                "(dd.competition = 'T20I' AND dd.team_bat = ANY(:top_teams) AND dd.team_bowl = ANY(:top_teams))"
            )
        else:
            competition_conditions.append("dd.competition = 'T20I'")

    if competition_conditions:
        return "AND (" + " OR ".join(competition_conditions) + ")"
    return "AND 1=1"


def get_match_totals_from_deliveries(
    venue: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    top_teams: Optional[int],
    db: Session
) -> Dict[str, Any]:
    """
    Get match totals and statistics from deliveries table.
    Returns aggregated match statistics for venue analysis.
    """
    params = {
        "venue": venue if venue and venue != "All Venues" else None,
        "start_date": start_date,
        "end_date": end_date,
        "leagues": leagues
    }

    venue_filter = build_venue_filter_deliveries(venue, params)
    competition_filter = build_competition_filter_deliveries(leagues, include_international, top_teams, params)

    query = f"""
        WITH match_totals AS (
            SELECT
                m.id,
                m.won_batting_first,
                m.won_fielding_first,
                d.innings,
                SUM(d.runs_off_bat + d.extras) as total_runs
            FROM matches m
            JOIN deliveries d ON m.id = d.match_id
            WHERE 1=1
                {venue_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                {competition_filter}
            GROUP BY m.id, m.won_batting_first, m.won_fielding_first, d.innings
        ),
        filtered_matches AS (
            SELECT *
            FROM matches m
            WHERE 1=1
                {venue_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                {competition_filter}
        )
        SELECT
            COUNT(DISTINCT fm.id) as total_matches,
            COUNT(DISTINCT CASE WHEN fm.won_batting_first THEN fm.id END) as batting_first_wins,
            COUNT(DISTINCT CASE WHEN fm.won_fielding_first THEN fm.id END) as batting_second_wins,
            MAX(CASE WHEN mt.innings = 1 THEN mt.total_runs END) as highest_total,
            MIN(CASE WHEN mt.innings = 1 THEN mt.total_runs END) as lowest_total,
            ROUND(AVG(CASE WHEN mt.innings = 1 THEN mt.total_runs END)::numeric, 2) as average_first_innings,
            ROUND(AVG(CASE WHEN mt.innings = 2 THEN mt.total_runs END)::numeric, 2) as average_second_innings,
            MAX(CASE WHEN fm.won_fielding_first AND mt.innings = 1 THEN mt.total_runs END) as highest_total_chased,
            MIN(CASE WHEN fm.won_batting_first AND mt.innings = 1 THEN mt.total_runs END) as lowest_total_defended,
            ROUND(AVG(CASE WHEN fm.won_batting_first AND mt.innings = 1 THEN mt.total_runs END)::numeric, 2) as average_winning_score,
            ROUND(AVG(CASE WHEN fm.won_fielding_first AND mt.innings = 1 THEN mt.total_runs END)::numeric, 2) as average_chasing_score
        FROM filtered_matches fm
        LEFT JOIN match_totals mt ON fm.id = mt.id
    """

    result = db.execute(text(query), params).fetchone()

    if not result or not result.total_matches:
        return None

    return {
        'total_matches': result.total_matches or 0,
        'batting_first_wins': result.batting_first_wins or 0,
        'batting_second_wins': result.batting_second_wins or 0,
        'highest_total': result.highest_total or 0,
        'lowest_total': result.lowest_total or 0,
        'average_first_innings': float(result.average_first_innings or 0),
        'average_second_innings': float(result.average_second_innings or 0),
        'highest_total_chased': result.highest_total_chased or 0,
        'lowest_total_defended': result.lowest_total_defended or 0,
        'average_winning_score': float(result.average_winning_score or 0),
        'average_chasing_score': float(result.average_chasing_score or 0)
    }


def get_match_totals_from_delivery_details(
    venue: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    top_teams: Optional[int],
    db: Session
) -> Dict[str, Any]:
    """
    Get match totals and statistics from delivery_details table.
    Returns aggregated match statistics for venue analysis.
    """
    params = {
        "venue": venue if venue and venue != "All Venues" else None,
        "start_date": start_date,
        "end_date": end_date,
        "leagues": leagues
    }

    venue_filter = build_venue_filter_delivery_details(venue, params)
    competition_filter = build_competition_filter_delivery_details(leagues, include_international, top_teams, params)

    query = f"""
        WITH match_totals AS (
            SELECT
                dd.p_match as match_id,
                m.won_batting_first,
                m.won_fielding_first,
                dd.inns as innings,
                SUM(dd.score) as total_runs
            FROM delivery_details dd
            JOIN matches m ON dd.p_match = m.id
            WHERE 1=1
                {venue_filter}
                AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
                AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
                {competition_filter}
            GROUP BY dd.p_match, m.won_batting_first, m.won_fielding_first, dd.inns
        ),
        filtered_matches AS (
            SELECT DISTINCT dd.p_match as id, m.won_batting_first, m.won_fielding_first
            FROM delivery_details dd
            JOIN matches m ON dd.p_match = m.id
            WHERE 1=1
                {venue_filter}
                AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
                AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
                {competition_filter}
        )
        SELECT
            COUNT(DISTINCT fm.id) as total_matches,
            COUNT(DISTINCT CASE WHEN fm.won_batting_first THEN fm.id END) as batting_first_wins,
            COUNT(DISTINCT CASE WHEN fm.won_fielding_first THEN fm.id END) as batting_second_wins,
            MAX(CASE WHEN mt.innings = 1 THEN mt.total_runs END) as highest_total,
            MIN(CASE WHEN mt.innings = 1 THEN mt.total_runs END) as lowest_total,
            ROUND(AVG(CASE WHEN mt.innings = 1 THEN mt.total_runs END)::numeric, 2) as average_first_innings,
            ROUND(AVG(CASE WHEN mt.innings = 2 THEN mt.total_runs END)::numeric, 2) as average_second_innings,
            MAX(CASE WHEN fm.won_fielding_first AND mt.innings = 1 THEN mt.total_runs END) as highest_total_chased,
            MIN(CASE WHEN fm.won_batting_first AND mt.innings = 1 THEN mt.total_runs END) as lowest_total_defended,
            ROUND(AVG(CASE WHEN fm.won_batting_first AND mt.innings = 1 THEN mt.total_runs END)::numeric, 2) as average_winning_score,
            ROUND(AVG(CASE WHEN fm.won_fielding_first AND mt.innings = 1 THEN mt.total_runs END)::numeric, 2) as average_chasing_score
        FROM filtered_matches fm
        LEFT JOIN match_totals mt ON fm.id = mt.match_id
    """

    result = db.execute(text(query), params).fetchone()

    if not result or not result.total_matches:
        return None

    return {
        'total_matches': result.total_matches or 0,
        'batting_first_wins': result.batting_first_wins or 0,
        'batting_second_wins': result.batting_second_wins or 0,
        'highest_total': result.highest_total or 0,
        'lowest_total': result.lowest_total or 0,
        'average_first_innings': float(result.average_first_innings or 0),
        'average_second_innings': float(result.average_second_innings or 0),
        'highest_total_chased': result.highest_total_chased or 0,
        'lowest_total_defended': result.lowest_total_defended or 0,
        'average_winning_score': float(result.average_winning_score or 0),
        'average_chasing_score': float(result.average_chasing_score or 0)
    }


def get_venue_match_stats(
    venue: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    top_teams: Optional[int],
    db: Session
) -> Dict[str, Any]:
    """
    Get venue match statistics, automatically routing to correct table(s) based on date range.

    This is the main entry point for venue statistics. It handles dual-table logic internally.
    """
    routing = should_use_delivery_details(start_date, end_date)

    logger.info(f"Venue stats routing: {routing}")

    # Try delivery_details first (has most recent data)
    if routing['use_delivery_details']:
        dd_start, dd_end = routing['delivery_details_date_range']
        result = get_match_totals_from_delivery_details(
            venue, dd_start, dd_end, leagues, include_international, top_teams, db
        )
        if result:
            return result

    # Fall back to deliveries if delivery_details had no data
    if routing['use_deliveries']:
        d_start, d_end = routing['deliveries_date_range']
        result = get_match_totals_from_deliveries(
            venue, d_start, d_end, leagues, include_international, top_teams, db
        )
        if result:
            return result

    # No data found
    return None


def get_venue_phase_stats(
    venue: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    top_teams: Optional[int],
    db: Session
) -> Dict[str, Any]:
    """
    Get phase-wise statistics for a venue.

    Returns stats for batting first wins and chasing wins across different phases.
    """
    def _empty_stats() -> Dict[str, Any]:
        return {
            'batting_first_wins': {},
            'chasing_wins': {}
        }

    def _process_phase_results(phase_results) -> Dict[str, Any]:
        phase_wise_stats = _empty_stats()

        for stat in phase_results:
            # Only use innings 1 data for phase stats (represents first innings performance)
            if stat.innings != 1:
                continue

            if stat.batting_first_runs is not None:
                phase_wise_stats['batting_first_wins'][stat.phase] = {
                    'runs_per_innings': float(stat.batting_first_runs),
                    'wickets_per_innings': float(stat.batting_first_wickets or 0),
                    'balls_per_innings': float(stat.batting_first_balls or 0)
                }

            if stat.chasing_runs is not None:
                phase_wise_stats['chasing_wins'][stat.phase] = {
                    'runs_per_innings': float(stat.chasing_runs),
                    'wickets_per_innings': float(stat.chasing_wickets or 0),
                    'balls_per_innings': float(stat.chasing_balls or 0)
                }

        return phase_wise_stats

    def _run_phase_query(
        *,
        source: str,
        source_start_date: Optional[date],
        source_end_date: Optional[date]
    ):
        params = {
            "venue": venue if venue and venue != "All Venues" else None,
            "start_date": source_start_date,
            "end_date": source_end_date,
            "leagues": leagues
        }

        if source == "delivery_details":
            venue_filter = build_venue_filter_delivery_details(venue, params)
            competition_filter = build_competition_filter_delivery_details(
                leagues, include_international, top_teams, params
            )
            phase_query = text(f"""
                WITH phase_stats AS (
                    SELECT
                        dd.inns as innings,
                        dd.p_match as match_id,
                        m.won_batting_first,
                        m.won_fielding_first,
                        CASE
                            WHEN dd.over < 6 THEN 'powerplay'
                            WHEN dd.over >= 6 AND dd.over < 10 THEN 'middle1'
                            WHEN dd.over >= 10 AND dd.over < 15 THEN 'middle2'
                            ELSE 'death'
                        END as phase,
                        SUM(dd.score) as runs,
                        COUNT(*) as balls,
                        SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets
                    FROM delivery_details dd
                    JOIN matches m ON dd.p_match = m.id
                    WHERE 1=1
                        {venue_filter}
                        AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
                        AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
                        {competition_filter}
                    GROUP BY dd.inns, dd.p_match, m.won_batting_first, m.won_fielding_first, phase
                ),
                innings_stats AS (
                    SELECT
                        innings,
                        phase,
                        ROUND(AVG(runs)::numeric, 2) as runs_per_innings,
                        ROUND(AVG(wickets)::numeric, 2) as wickets_per_innings,
                        ROUND(AVG(balls)::numeric, 2) as balls_per_innings,
                        COUNT(*) as total_innings
                    FROM phase_stats
                    GROUP BY innings, phase
                ),
                batting_first_stats AS (
                    SELECT
                        innings,
                        phase,
                        ROUND(AVG(runs)::numeric, 2) as runs_per_innings,
                        ROUND(AVG(wickets)::numeric, 2) as wickets_per_innings,
                        ROUND(AVG(balls)::numeric, 2) as balls_per_innings
                    FROM phase_stats
                    WHERE won_batting_first = true
                    GROUP BY innings, phase
                ),
                chasing_stats AS (
                    SELECT
                        innings,
                        phase,
                        ROUND(AVG(runs)::numeric, 2) as runs_per_innings,
                        ROUND(AVG(wickets)::numeric, 2) as wickets_per_innings,
                        ROUND(AVG(balls)::numeric, 2) as balls_per_innings
                    FROM phase_stats
                    WHERE won_fielding_first = true
                    GROUP BY innings, phase
                )
                SELECT
                    i.innings,
                    i.phase,
                    i.runs_per_innings,
                    i.wickets_per_innings,
                    i.balls_per_innings,
                    b.runs_per_innings as batting_first_runs,
                    b.wickets_per_innings as batting_first_wickets,
                    b.balls_per_innings as batting_first_balls,
                    c.runs_per_innings as chasing_runs,
                    c.wickets_per_innings as chasing_wickets,
                    c.balls_per_innings as chasing_balls
                FROM innings_stats i
                LEFT JOIN batting_first_stats b ON i.innings = b.innings AND i.phase = b.phase
                LEFT JOIN chasing_stats c ON i.innings = c.innings AND i.phase = c.phase
                ORDER BY i.innings,
                    CASE i.phase
                        WHEN 'powerplay' THEN 1
                        WHEN 'middle1' THEN 2
                        WHEN 'middle2' THEN 3
                        WHEN 'death' THEN 4
                    END
            """)
        else:
            venue_filter = build_venue_filter_deliveries(venue, params)
            competition_filter = build_competition_filter_deliveries(
                leagues, include_international, top_teams, params
            )
            phase_query = text(f"""
        WITH phase_stats AS (
            SELECT
                d.innings,
                d.match_id,
                m.won_batting_first,
                m.won_fielding_first,
                CASE
                    WHEN d.over < 6 THEN 'powerplay'
                    WHEN d.over >= 6 AND d.over < 10 THEN 'middle1'
                    WHEN d.over >= 10 AND d.over < 15 THEN 'middle2'
                    ELSE 'death'
                END as phase,
                SUM(d.runs_off_bat + d.extras) as runs,
                COUNT(*) as balls,
                SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END) as wickets
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE 1=1
                {venue_filter}
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                {competition_filter}
            GROUP BY d.innings, d.match_id, m.won_batting_first, m.won_fielding_first, phase
        ),
        innings_stats AS (
            SELECT
                innings,
                phase,
                ROUND(AVG(runs)::numeric, 2) as runs_per_innings,
                ROUND(AVG(wickets)::numeric, 2) as wickets_per_innings,
                ROUND(AVG(balls)::numeric, 2) as balls_per_innings,
                COUNT(*) as total_innings
            FROM phase_stats
            GROUP BY innings, phase
        ),
        batting_first_stats AS (
            SELECT
                innings,
                phase,
                ROUND(AVG(runs)::numeric, 2) as runs_per_innings,
                ROUND(AVG(wickets)::numeric, 2) as wickets_per_innings,
                ROUND(AVG(balls)::numeric, 2) as balls_per_innings
            FROM phase_stats
            WHERE won_batting_first = true
            GROUP BY innings, phase
        ),
        chasing_stats AS (
            SELECT
                innings,
                phase,
                ROUND(AVG(runs)::numeric, 2) as runs_per_innings,
                ROUND(AVG(wickets)::numeric, 2) as wickets_per_innings,
                ROUND(AVG(balls)::numeric, 2) as balls_per_innings
            FROM phase_stats
            WHERE won_fielding_first = true
            GROUP BY innings, phase
        )
        SELECT
            i.innings,
            i.phase,
            i.runs_per_innings,
            i.wickets_per_innings,
            i.balls_per_innings,
            b.runs_per_innings as batting_first_runs,
            b.wickets_per_innings as batting_first_wickets,
            b.balls_per_innings as batting_first_balls,
            c.runs_per_innings as chasing_runs,
            c.wickets_per_innings as chasing_wickets,
            c.balls_per_innings as chasing_balls
        FROM innings_stats i
        LEFT JOIN batting_first_stats b ON i.innings = b.innings AND i.phase = b.phase
        LEFT JOIN chasing_stats c ON i.innings = c.innings AND i.phase = c.phase
        ORDER BY i.innings,
            CASE i.phase
                WHEN 'powerplay' THEN 1
                WHEN 'middle1' THEN 2
                WHEN 'middle2' THEN 3
                WHEN 'death' THEN 4
            END
    """)
        return db.execute(phase_query, params).fetchall()

    try:
        routing = should_use_delivery_details(start_date, end_date)
        logger.info(f"Venue phase stats routing: {routing}")

        if routing['use_delivery_details']:
            dd_start, dd_end = routing['delivery_details_date_range']
            phase_results = _run_phase_query(
                source="delivery_details",
                source_start_date=dd_start,
                source_end_date=dd_end
            )
            if phase_results:
                return _process_phase_results(phase_results)

        if routing['use_deliveries']:
            d_start, d_end = routing['deliveries_date_range']
            phase_results = _run_phase_query(
                source="deliveries",
                source_start_date=d_start,
                source_end_date=d_end
            )
            if phase_results:
                return _process_phase_results(phase_results)

        return _empty_stats()

    except Exception as e:
        logger.error(f"Error getting phase stats: {e}", exc_info=True)
        return _empty_stats()


def get_match_scores_from_deliveries(
    match_ids: List[str],
    db: Session
) -> Dict[str, Dict[int, str]]:
    """
    Get match scores (runs/wickets) from deliveries table.

    Args:
        match_ids: List of match IDs to get scores for
        db: Database session

    Returns:
        Dict mapping match_id to innings scores:
        {
            'match_123': {1: '186/5', 2: '187/3'},
            ...
        }
    """
    if not match_ids:
        return {}

    query = text("""
        SELECT
            match_id,
            innings,
            CONCAT(
                COALESCE(SUM(runs_off_bat + extras), 0),
                '/',
                COALESCE(COUNT(CASE WHEN wicket_type IS NOT NULL THEN 1 END), 0)
            ) as score
        FROM deliveries
        WHERE match_id = ANY(:match_ids)
        GROUP BY match_id, innings
        ORDER BY match_id, innings
    """)

    result = db.execute(query, {'match_ids': match_ids}).fetchall()

    scores = {}
    for row in result:
        if row[0] not in scores:
            scores[row[0]] = {}
        scores[row[0]][row[1]] = row[2]

    return scores


def get_match_scores_from_delivery_details(
    match_ids: List[str],
    db: Session
) -> Dict[str, Dict[int, str]]:
    """
    Get match scores (runs/wickets) from delivery_details table.

    Args:
        match_ids: List of match IDs to get scores for
        db: Database session

    Returns:
        Dict mapping match_id to innings scores:
        {
            'match_123': {1: '186/5', 2: '187/3'},
            ...
        }
    """
    if not match_ids:
        return {}

    query = text("""
        SELECT
            p_match as match_id,
            inns as innings,
            CONCAT(
                COALESCE(SUM(score), 0),
                '/',
                COALESCE(COUNT(CASE WHEN out = 'true' THEN 1 END), 0)
            ) as score
        FROM delivery_details
        WHERE p_match = ANY(:match_ids)
        GROUP BY p_match, inns
        ORDER BY p_match, inns
    """)

    result = db.execute(query, {'match_ids': match_ids}).fetchall()

    scores = {}
    for row in result:
        if row[0] not in scores:
            scores[row[0]] = {}
        scores[row[0]][row[1]] = row[2]

    return scores


def get_match_scores(
    match_ids: List[str],
    start_date: Optional[date],
    end_date: Optional[date],
    db: Session
) -> Dict[str, Dict[int, str]]:
    """
    Get match scores with automatic dual-table routing.

    Args:
        match_ids: List of match IDs to get scores for
        start_date: Optional date filter for routing decision
        end_date: Optional date filter for routing decision
        db: Database session

    Returns:
        Dict mapping match_id to innings scores
    """
    if not match_ids:
        return {}

    routing = should_use_delivery_details(start_date, end_date)

    # Try delivery_details first for recent data
    if routing['use_delivery_details']:
        scores = get_match_scores_from_delivery_details(match_ids, db)
        if scores:
            return scores

    # Fall back to deliveries
    if routing['use_deliveries'] or not routing['use_delivery_details']:
        scores = get_match_scores_from_deliveries(match_ids, db)
        if scores:
            return scores

    return {}
