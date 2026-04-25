"""
Query Builder Service - Using delivery_details table

This service provides flexible querying of ball-by-ball cricket data
with support for filtering, grouping, and aggregation.
"""

from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import date
from models import teams_mapping, INTERNATIONAL_TEAMS_RANKED
from services.delivery_data_service import get_venue_aliases
from services.bowler_types import PACE_TYPES as ALL_KNOWN_PACE_TYPES, SPIN_TYPES as ALL_KNOWN_SPIN_TYPES
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# DUAL TABLE CONFIGURATION
# =============================================================================

# Date boundary: delivery_details starts from 2015-01-01
DELIVERY_DETAILS_START_DATE = date(2015, 1, 1)

# Columns only available in delivery_details (2015+)
ADVANCED_COLUMNS = {
    'line', 'length', 'shot', 'control', 'wagon_zone', 'wagon_x', 'wagon_y',
    'bat_hand'
}

# Columns available in both tables (can be queried across full date range)
COMMON_COLUMNS = {
    'venue', 'competition', 'year', 'batting_team', 'bowling_team',
    'batter', 'bowler', 'innings', 'phase', 'match_id', 'country',
    'dismissal'
}

# Columns that exist in both but have different coverage
# crease_combo: ~91% in delivery_details, lower in deliveries
PARTIAL_COLUMNS = {'crease_combo'}

# Bowl-style sets used to infer bowl_kind when the column is NULL.
# Include legacy aliases (RO/RL/LO/LC, etc.) via shared bowler-types mapping.
SPIN_STYLES = set(ALL_KNOWN_SPIN_TYPES) | {"SLO", "OS", "RAS", "SLW"}
PACE_STYLES = set(ALL_KNOWN_PACE_TYPES)

# Canonicalize legacy short-hands to modern style labels used across the app.
LEGACY_BOWL_STYLE_CANONICAL_MAP = {
    "RO": "OB",    # Right-arm offbreak
    "RL": "LB",    # Right-arm legbreak
    "LO": "SLA",   # Left-arm orthodox spin
    "LC": "LWS",   # Left-arm chinaman / wrist-spin
    "NAN": "UNKNOWN",
    "-": "UNKNOWN",
}

VALID_QUERY_MODES = {"delivery", "batting_stats", "bowling_stats"}
VALID_MATCH_OUTCOMES = {"win", "loss", "tie", "no_result"}
VALID_TOSS_DECISIONS = {"bat", "field"}
MATCH_CONTEXT_GROUP_BY_COLUMNS = {"match_outcome", "chase_outcome", "toss_decision", "toss_match_outcome"}

# Team names are canonicalised at write-time by team_standardization.py
# (see standardize_teams()), so the query layer can compare directly. The
# CASE-based normaliser this used to emit was 8.7K chars per call and
# was the dominant cost in match_outcome / chase_outcome filters.
TEAM_CANONICAL_MAP: Dict[str, str] = {}
for full_name, abbrev in teams_mapping.items():
    TEAM_CANONICAL_MAP[full_name.lower()] = abbrev.lower()
    TEAM_CANONICAL_MAP[abbrev.lower()] = abbrev.lower()


def _sql_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def get_team_canonical_sql(column_expr: str) -> str:
    return f"LOWER(COALESCE({column_expr}, ''))"


def get_match_outcome_sql(
    batting_team_expr: str,
    bowling_team_expr: str,
    winner_expr: str,
    outcome_json_expr: str
) -> str:
    winner_canonical = get_team_canonical_sql(winner_expr)
    batting_canonical = get_team_canonical_sql(batting_team_expr)
    bowling_canonical = get_team_canonical_sql(bowling_team_expr)

    return f"""(
        CASE
            WHEN LOWER(COALESCE({outcome_json_expr}->>'result', '')) = 'tie' THEN 'tie'
            WHEN LOWER(COALESCE({outcome_json_expr}->>'result', '')) = 'no result' THEN 'no_result'
            WHEN COALESCE({winner_expr}, '') = '' THEN 'no_result'
            WHEN {winner_canonical} = {batting_canonical} THEN 'win'
            WHEN {winner_canonical} = {bowling_canonical} THEN 'loss'
            ELSE 'no_result'
        END
    )"""


def get_chase_outcome_sql(innings_expr: str, match_outcome_sql: str) -> str:
    return f"(CASE WHEN {innings_expr} = 2 THEN {match_outcome_sql} ELSE NULL END)"


def get_toss_match_outcome_sql(
    toss_winner_expr: str,
    winner_expr: str,
    outcome_json_expr: str
) -> str:
    """Match outcome from the toss-winning team's perspective."""
    toss_canonical = get_team_canonical_sql(toss_winner_expr)
    winner_canonical = get_team_canonical_sql(winner_expr)
    return f"""(
        CASE
            WHEN LOWER(COALESCE({outcome_json_expr}->>'result', '')) = 'tie' THEN 'tie'
            WHEN LOWER(COALESCE({outcome_json_expr}->>'result', '')) = 'no result' THEN 'no_result'
            WHEN COALESCE({toss_winner_expr}, '') = '' THEN 'no_result'
            WHEN COALESCE({winner_expr}, '') = '' THEN 'no_result'
            WHEN {winner_canonical} = {toss_canonical} THEN 'win'
            ELSE 'loss'
        END
    )"""


def get_legacy_bowler_style_sql() -> str:
    """
    Build normalized legacy bowler style from delivery + players fallback sources.
    Precedence: deliveries.bowler_type -> players.bowler_type -> players.bowling_type -> players.bowl_type.
    """
    style_source_sql = """
        COALESCE(
            NULLIF(TRIM(d.bowler_type), ''),
            NULLIF(TRIM(p.bowler_type), ''),
            NULLIF(TRIM(p.bowling_type), ''),
            NULLIF(TRIM(p.bowl_type), '')
        )
    """
    normalized_style_sql = f"UPPER({style_source_sql})"
    canonical_cases = " ".join(
        f"WHEN {normalized_style_sql} = {_sql_quote(raw)} THEN {_sql_quote(canonical)}"
        for raw, canonical in LEGACY_BOWL_STYLE_CANONICAL_MAP.items()
    )
    return f"""(
        CASE
            WHEN {normalized_style_sql} IS NULL OR {normalized_style_sql} = '' THEN NULL
            {canonical_cases}
            ELSE {normalized_style_sql}
        END
    )"""


def get_legacy_bowl_kind_sql(legacy_bowler_style_sql: Optional[str] = None) -> str:
    """
    Classify legacy bowl kind from normalized style code.
    Unknown/missing styles are intentionally mapped to 'mixture/unknown'.
    """
    normalized_style_sql = legacy_bowler_style_sql or get_legacy_bowler_style_sql()
    spin_styles_sql = ", ".join(_sql_quote(v) for v in sorted(SPIN_STYLES))
    pace_styles_sql = ", ".join(_sql_quote(v) for v in sorted(PACE_STYLES))
    return f"""(
        CASE
            WHEN {normalized_style_sql} IN ({spin_styles_sql}) THEN 'spin bowler'
            WHEN {normalized_style_sql} IN ({pace_styles_sql}) THEN 'pace bowler'
            ELSE 'mixture/unknown'
        END
    )"""


def match_context_requested(
    match_outcome: List[str],
    is_chase: Optional[bool],
    chase_outcome: List[str],
    toss_decision: List[str],
    group_by: List[str],
) -> bool:
    if match_outcome or chase_outcome or toss_decision or is_chase is not None:
        return True
    return bool(set(group_by or []) & MATCH_CONTEXT_GROUP_BY_COLUMNS)


def validate_mode_filters(
    query_mode: str,
    bat_hand: Optional[str],
    bowl_style: List[str],
    bowl_kind: List[str],
    crease_combo: List[str],
    line: List[str],
    length: List[str],
    shot: List[str],
    control: Optional[int],
    wagon_zone: List[int],
    dismissal: List[str],
    over_min: Optional[int],
    over_max: Optional[int],
) -> None:
    if query_mode == "delivery":
        return

    unsupported = []
    if bat_hand:
        unsupported.append("bat_hand")
    if bowl_style:
        unsupported.append("bowl_style")
    if bowl_kind:
        unsupported.append("bowl_kind")
    if crease_combo:
        unsupported.append("crease_combo")
    if line:
        unsupported.append("line")
    if length:
        unsupported.append("length")
    if shot:
        unsupported.append("shot")
    if control is not None:
        unsupported.append("control")
    if wagon_zone:
        unsupported.append("wagon_zone")
    if dismissal:
        unsupported.append("dismissal")
    if over_min is not None:
        unsupported.append("over_min")
    if over_max is not None:
        unsupported.append("over_max")

    if unsupported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported filters for query_mode={query_mode}: {unsupported}"
        )


def validate_wicket_filters(
    query_mode: str,
    min_wickets: Optional[int],
    max_wickets: Optional[int],
) -> None:
    if min_wickets is None and max_wickets is None:
        return
    if query_mode not in ("bowling_stats", "delivery"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported filters for query_mode={query_mode}: ['min_wickets', 'max_wickets']",
        )
    if min_wickets is not None and max_wickets is not None and min_wickets > max_wickets:
        raise HTTPException(
            status_code=400,
            detail="min_wickets cannot be greater than max_wickets",
        )


def analyze_query_requirements(
    start_date: Optional[date],
    end_date: Optional[date],
    group_by: List[str],
    filters_used: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze query to determine which tables to use.
    
    Returns:
        {
            'use_legacy': bool,           # Should query deliveries table (pre-2015)
            'use_new': bool,              # Should query delivery_details table (2015+)
            'advanced_columns_used': set, # Advanced columns in query
            'warnings': list,             # User-facing warnings
            'legacy_date_range': tuple,   # (start, end) for legacy query
            'new_date_range': tuple,      # (start, end) for new query
        }
    """
    result = {
        'use_legacy': False,
        'use_new': False,
        'advanced_columns_used': set(),
        'warnings': [],
        'legacy_date_range': None,
        'new_date_range': None,
    }
    
    # Check which advanced columns are used (in group_by or filters)
    columns_in_query = set(group_by) if group_by else set()
    for key, value in filters_used.items():
        if value is not None and (isinstance(value, list) and len(value) > 0 or not isinstance(value, list)):
            columns_in_query.add(key)
    
    advanced_used = columns_in_query & ADVANCED_COLUMNS
    result['advanced_columns_used'] = advanced_used
    
    # Determine date ranges
    query_start = start_date or date(2005, 1, 1)  # Default to earliest data
    query_end = end_date or date.today()
    
    has_pre_2015 = query_start < DELIVERY_DETAILS_START_DATE
    has_post_2015 = query_end >= DELIVERY_DETAILS_START_DATE
    
    # If advanced columns used, we can only query delivery_details (2015+)
    if advanced_used:
        result['use_new'] = True
        result['use_legacy'] = False
        
        # Adjust date range to 2015+ only
        effective_start = max(query_start, DELIVERY_DETAILS_START_DATE)
        result['new_date_range'] = (effective_start, query_end)
        
        # Warn if user requested pre-2015 data but we can't provide it
        if has_pre_2015:
            result['warnings'].append(
                f"Columns {list(advanced_used)} are only available from 2015 onwards. "
                f"Data before 2015 is excluded from results."
            )
    else:
        # No advanced columns - can query both tables
        if has_post_2015:
            result['use_new'] = True
            new_start = max(query_start, DELIVERY_DETAILS_START_DATE)
            result['new_date_range'] = (new_start, query_end)
        
        if has_pre_2015:
            result['use_legacy'] = True
            legacy_end = min(query_end, date(2014, 12, 31))
            result['legacy_date_range'] = (query_start, legacy_end)

    # bowl_style/bowl_kind are supported on legacy data via inferred classification.
    inferred_legacy_columns_used = columns_in_query & {'bowl_style', 'bowl_kind'}
    if result['use_legacy'] and inferred_legacy_columns_used:
        result['warnings'].append(
            "Legacy bowl classification is inferred using deliveries.bowler_type "
            "with players-table fallback; unknown styles are grouped as mixture/unknown."
        )

    return result


def get_player_name_variants(player_names: List[str], db, direction: str = 'new_to_old') -> Dict[str, List[str]]:
    """
    Get player name variants using the player_aliases table.
    
    Args:
        player_names: List of player names to look up
        db: Database session
        direction: 'new_to_old' (delivery_details -> deliveries) or 'old_to_new'
    
    Returns:
        Dict mapping each input name to list of all variants (including itself)
    """
    if not player_names:
        return {}
    
    result = {name: [name] for name in player_names}  # Start with self
    
    try:
        if direction == 'new_to_old':
            # Looking up: given new name (alias_name), find old name (player_name)
            query = text("""
                SELECT alias_name, player_name 
                FROM player_aliases 
                WHERE alias_name = ANY(:names)
            """)
        else:
            # Looking up: given old name (player_name), find new name (alias_name)
            query = text("""
                SELECT player_name, alias_name 
                FROM player_aliases 
                WHERE player_name = ANY(:names)
            """)
        
        aliases = db.execute(query, {'names': player_names}).fetchall()
        
        for row in aliases:
            input_name = row[0]
            variant_name = row[1]
            if input_name in result:
                if variant_name not in result[input_name]:
                    result[input_name].append(variant_name)
    except Exception as e:
        logger.warning(f"Error fetching player aliases: {e}")
    
    return result


def get_all_player_variants(player_names: List[str], db) -> List[str]:
    """
    Get all variants of player names for querying legacy table.
    Returns flat list of all names (original + aliases).
    """
    if not player_names:
        return []

    variants = get_player_name_variants(player_names, db, direction='new_to_old')
    all_names = set()
    for name, name_variants in variants.items():
        all_names.update(name_variants)

    return list(all_names)


def _expand_player_names(player_names: List[str], db) -> List[str]:
    """
    Expand player names to include both legacy and delivery_details variants.
    Checks both directions so either name format works as input.
    """
    if not player_names or not db:
        return player_names

    all_names = set(player_names)
    try:
        # old_to_new: "YS Samra" -> "Yuvraj Samra"
        old_to_new = get_player_name_variants(player_names, db, direction='old_to_new')
        for variants in old_to_new.values():
            all_names.update(variants)
        # new_to_old: "Yuvraj Samra" -> "YS Samra"
        new_to_old = get_player_name_variants(player_names, db, direction='new_to_old')
        for variants in new_to_old.values():
            all_names.update(variants)
    except Exception as e:
        logger.warning(f"Error expanding player names: {e}")

    return list(all_names)


# =============================================================================
# LEGACY TABLE (deliveries) COLUMN MAPPING
# =============================================================================

def get_legacy_grouping_columns_map():
    """Map user-friendly group_by values to deliveries table column names."""
    legacy_bowler_style_sql = get_legacy_bowler_style_sql()
    legacy_bowl_kind_sql = get_legacy_bowl_kind_sql(legacy_bowler_style_sql)
    match_outcome_sql = get_match_outcome_sql(
        batting_team_expr="d.batting_team",
        bowling_team_expr="d.bowling_team",
        winner_expr="m.winner",
        outcome_json_expr="m.outcome",
    )
    chase_outcome_sql = get_chase_outcome_sql("d.innings", match_outcome_sql)

    return {
        # Location
        "venue": "m.venue",
        "country": "NULL",  # Not available in legacy
        
        # Match identifiers
        "match_id": "d.match_id",
        "competition": "m.competition",
        "year": "EXTRACT(YEAR FROM m.date)",
        
        # Teams
        "batting_team": "d.batting_team",
        "bowling_team": "d.bowling_team",
        
        # Players
        "batter": "d.batter",
        "bowler": "d.bowler",
        # Canonicalize legacy short-form names via player_aliases. pa_*
        # joins are conditionally added by query_legacy_grouped.
        "non_striker": "COALESCE(pa_ns.alias_name, d.non_striker)",
        # Bidirectional pair: (Kohli, ABD) and (ABD, Kohli) collapse to one row.
        "partnership": (
            "(LEAST("
            "COALESCE(pa_bat.alias_name, d.batter, ''), "
            "COALESCE(pa_ns.alias_name, d.non_striker, '')"
            ") || ' & ' || GREATEST("
            "COALESCE(pa_bat.alias_name, d.batter, ''), "
            "COALESCE(pa_ns.alias_name, d.non_striker, '')"
            "))"
        ),
        # Wired by the bat_pos CTE in query_legacy_grouped.
        "batting_position": "bp.pos",

        # Innings/Phase
        "innings": "d.innings",
        "phase": "CASE WHEN d.over < 6 THEN 'powerplay' WHEN d.over < 15 THEN 'middle' ELSE 'death' END",
        
        # Batter attributes (partial coverage in legacy)
        "bat_hand": "NULL",  # Not available
        "striker_batter_type": "d.striker_batter_type",  # Backward-compatible alias
        "non_striker_batter_type": "d.non_striker_batter_type",  # Backward-compatible alias
        # Normalize crease_combo: swap RHB_LHB -> LHB_RHB and lowercase
        "crease_combo": "LOWER(CASE WHEN d.crease_combo = 'RHB_LHB' THEN 'LHB_RHB' ELSE d.crease_combo END)",
        "ball_direction": "d.ball_direction",  # Backward-compatible alias
        
        # Bowler attributes
        "bowl_style": legacy_bowler_style_sql,
        "bowl_kind": legacy_bowl_kind_sql,
        
        # Delivery details - NOT available in legacy, return NULL
        "line": "NULL",
        "length": "NULL",
        "shot": "NULL",
        "control": "NULL",
        "wagon_zone": "NULL",
        "dismissal": "d.wicket_type",
        # Match context
        "match_outcome": match_outcome_sql,
        "chase_outcome": chase_outcome_sql,
        "toss_decision": "LOWER(COALESCE(m.toss_decision, ''))",
        "toss_match_outcome": get_toss_match_outcome_sql("m.toss_winner", "m.winner", "m.outcome"),
    }


def build_legacy_where_clause(
    venue, start_date, end_date, leagues, teams, batting_teams, bowling_teams,
    players, batters, bowlers, bowl_style, bowl_kind, crease_combo, dismissal, innings, over_min, over_max,
    match_outcome, is_chase, chase_outcome, toss_decision,
    include_international, top_teams, group_by, base_params, db
):
    """Build dynamic WHERE clause for legacy deliveries table."""
    conditions = ["1=1"]
    params = base_params.copy()
    
    # Venue filter
    if venue:
        params["venue_aliases"] = get_venue_aliases(venue)
        conditions.append("m.venue = ANY(:venue_aliases)")
    
    # Date filters
    if start_date:
        conditions.append("m.date >= :start_date")
        params["start_date"] = start_date
    
    if end_date:
        conditions.append("m.date <= :end_date")
        params["end_date"] = end_date
    
    # Competition filters (leagues and/or international)
    # These should be OR'd together - a delivery can be from a league OR international
    competition_conditions = []
    
    if leagues:
        expanded_leagues = expand_league_abbreviations(leagues)
        competition_conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
        params["leagues"] = expanded_leagues
    
    if include_international:
        if top_teams:
            top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            competition_conditions.append("(m.match_type = 'international' AND m.team1 = ANY(:top_teams) AND m.team2 = ANY(:top_teams))")
            params["top_teams"] = top_team_list
        else:
            competition_conditions.append("m.match_type = 'international'")
    
    # Combine competition conditions with OR
    if competition_conditions:
        conditions.append("(" + " OR ".join(competition_conditions) + ")")
    
    # Team filters
    team_conditions = []
    
    if teams:
        team_variations = []
        for team in teams:
            team_variations.extend(get_all_team_name_variations(team))
        team_conditions.append("(d.batting_team = ANY(:teams) OR d.bowling_team = ANY(:teams))")
        params["teams"] = team_variations
    
    if batting_teams:
        batting_variations = []
        for team in batting_teams:
            batting_variations.extend(get_all_team_name_variations(team))
        team_conditions.append("d.batting_team = ANY(:batting_teams)")
        params["batting_teams"] = batting_variations
    
    if bowling_teams:
        bowling_variations = []
        for team in bowling_teams:
            bowling_variations.extend(get_all_team_name_variations(team))
        team_conditions.append("d.bowling_team = ANY(:bowling_teams)")
        params["bowling_teams"] = bowling_variations
    
    if team_conditions:
        conditions.append("(" + " AND ".join(team_conditions) + ")")
    
    # Player filters - need to expand with aliases for legacy table
    if players:
        player_variants = get_all_player_variants(players, db)
        conditions.append("(d.batter = ANY(:players) OR d.bowler = ANY(:players))")
        params["players"] = player_variants
    
    if batters:
        batter_variants = get_all_player_variants(batters, db)
        conditions.append("d.batter = ANY(:batters)")
        params["batters"] = batter_variants
    
    if bowlers:
        bowler_variants = get_all_player_variants(bowlers, db)
        conditions.append("d.bowler = ANY(:bowlers)")
        params["bowlers"] = bowler_variants

    legacy_bowler_style_sql = get_legacy_bowler_style_sql()
    legacy_bowl_kind_sql = get_legacy_bowl_kind_sql(legacy_bowler_style_sql)

    if bowl_style:
        normalized_styles = []
        for value in bowl_style:
            token = str(value).strip().upper()
            if not token:
                continue
            normalized_styles.append(LEGACY_BOWL_STYLE_CANONICAL_MAP.get(token, token))
        params["bowl_style"] = sorted(set(normalized_styles))
        conditions.append(f"{legacy_bowler_style_sql} = ANY(:bowl_style)")

    if bowl_kind:
        params["bowl_kind"] = [str(v).strip().lower() for v in bowl_kind if str(v).strip()]
        conditions.append(f"LOWER({legacy_bowl_kind_sql}) = ANY(:bowl_kind)")
    
    # Crease combo filter (partial coverage in legacy)
    if crease_combo:
        expanded_crease = []
        for combo in crease_combo:
            expanded_crease.append(combo)
            if combo == "LHB_RHB":
                expanded_crease.append("RHB_LHB")
            elif combo == "RHB_LHB":
                expanded_crease.append("LHB_RHB")
        conditions.append("d.crease_combo = ANY(:crease_combo)")
        params["crease_combo"] = list(set(expanded_crease))

    if dismissal:
        conditions.append("d.wicket_type = ANY(:dismissal)")
        params["dismissal"] = dismissal

    match_outcome_sql = get_match_outcome_sql(
        batting_team_expr="d.batting_team",
        bowling_team_expr="d.bowling_team",
        winner_expr="m.winner",
        outcome_json_expr="m.outcome",
    )
    chase_outcome_sql = get_chase_outcome_sql("d.innings", match_outcome_sql)

    if match_outcome:
        conditions.append(f"{match_outcome_sql} = ANY(:match_outcome)")
        params["match_outcome"] = match_outcome

    if is_chase is True:
        conditions.append("d.innings = 2")
    elif is_chase is False:
        conditions.append("d.innings != 2")

    if chase_outcome:
        conditions.append("d.innings = 2")
        conditions.append(f"{chase_outcome_sql} = ANY(:chase_outcome)")
        params["chase_outcome"] = chase_outcome

    if toss_decision:
        conditions.append("LOWER(COALESCE(m.toss_decision, '')) = ANY(:toss_decision)")
        params["toss_decision"] = toss_decision

    # Grouping by dismissal should only include wicket deliveries
    if group_by and "dismissal" in group_by:
        conditions.append("d.wicket_type IS NOT NULL AND d.wicket_type != ''")
    
    # Match context filters
    if innings:
        conditions.append("d.innings = :innings")
        params["innings"] = innings
    
    if over_min is not None:
        conditions.append("d.over >= :over_min")
        params["over_min"] = over_min
    
    if over_max is not None:
        conditions.append("d.over <= :over_max")
        params["over_max"] = over_max
    
    where_clause = "WHERE " + " AND ".join(conditions)
    return where_clause, params


def query_legacy_ungrouped(where_clause, params, limit, offset, db):
    """Query legacy deliveries table for individual records."""
    legacy_bowler_style_sql = get_legacy_bowler_style_sql()
    legacy_bowl_kind_sql = get_legacy_bowl_kind_sql(legacy_bowler_style_sql)
    
    main_query = f"""
        SELECT 
            d.match_id,
            d.innings,
            d.over,
            d.ball,
            d.batter,
            d.bowler,
            d.runs_off_bat,
            d.runs_off_bat + d.extras as total_runs,
            d.batting_team,
            d.bowling_team,
            NULL as bat_hand,
            {legacy_bowler_style_sql} as bowl_style,
            {legacy_bowl_kind_sql} as bowl_kind,
            LOWER(CASE WHEN d.crease_combo = 'RHB_LHB' THEN 'LHB_RHB' ELSE d.crease_combo END) as crease_combo,
            NULL as line,
            NULL as length,
            NULL as shot,
            NULL as control,
            NULL as wagon_x,
            NULL as wagon_y,
            NULL as wagon_zone,
            d.wicket_type,
            m.venue,
            m.date,
            m.competition,
            EXTRACT(YEAR FROM m.date)::int as year,
            NULL as outcome
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        LEFT JOIN players p ON p.name = d.bowler
        {where_clause}
        ORDER BY m.date DESC, d.over, d.ball
        LIMIT :limit
        OFFSET :offset
    """
    
    result = db.execute(text(main_query), params).fetchall()
    
    formatted_results = []
    for row in result:
        formatted_results.append({
            "match_id": row[0],
            "innings": row[1],
            "over": row[2],
            "ball": row[3],
            "batter": row[4],
            "bowler": row[5],
            "runs_off_bat": row[6],
            "total_runs": row[7],
            "batting_team": row[8],
            "bowling_team": row[9],
            "bat_hand": row[10],
            "bowl_style": row[11],
            "bowl_kind": row[12],
            "crease_combo": row[13],
            "line": row[14],
            "length": row[15],
            "shot": row[16],
            "control": row[17],
            "wagon_x": row[18],
            "wagon_y": row[19],
            "wagon_zone": row[20],
            "wicket_type": row[21],
            "venue": row[22],
            "date": row[23].isoformat() if row[23] else None,
            "competition": row[24],
            "year": row[25],
            "outcome": row[26]
        })
    
    # Count total
    count_query = f"""
        SELECT COUNT(*) 
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        LEFT JOIN players p ON p.name = d.bowler
        {where_clause}
    """
    count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
    total_count = db.execute(text(count_query), count_params).scalar()
    
    return formatted_results, total_count


def query_legacy_grouped(where_clause, params, group_by, db, has_batter_filters=False, total_balls_override=None):
    """
    Query legacy deliveries table for grouped/aggregated results.
    Returns fully calculated results matching the new table format.
    """
    grouping_columns = get_legacy_grouping_columns_map()
    
    # Build GROUP BY clause
    group_columns = []
    select_columns = []
    
    for col in group_by:
        db_column = grouping_columns.get(col, "NULL")
        group_columns.append(db_column)
        select_columns.append(f"{db_column} as {col}")
    
    # Filter out NULL columns from GROUP BY (can't group by NULL)
    valid_group_columns = [c for c in group_columns if c != "NULL"]
    if not valid_group_columns:
        # All requested columns are unavailable in legacy - return empty
        return [], 0
    
    group_by_clause = ", ".join(valid_group_columns)
    select_group_clause = ", ".join(select_columns)
    
    # Determine runs calculation
    batter_grouping = "batter" in group_by
    use_runs_off_bat_only = batter_grouping or has_batter_filters
    runs_calculation = "SUM(d.runs_off_bat)" if use_runs_off_bat_only else "SUM(d.runs_off_bat + d.extras)"
    
    query_params = {k: v for k, v in params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs', 'min_wickets', 'max_wickets']}

    # Single combined CTE — replaces total_balls_query + parent_query +
    # aggregation_query with one scan of `deliveries`. universe_balls and
    # parent_balls come from window functions in the same pass. No HAVING /
    # LIMIT applies here (route merges + filters downstream).
    if len(group_by) > 1:
        parent_partition_sql = f"SUM(g.balls) OVER (PARTITION BY g.{group_by[0]})"
    else:
        parent_partition_sql = "NULL::bigint"
    final_select_groups = ", ".join(f"g.{col} as {col}" for col in group_by)

    needs_bat_pos = "batting_position" in group_by
    bat_pos_cte = ""
    bat_pos_join = ""
    if needs_bat_pos:
        bat_pos_cte = """bat_pos AS (
            SELECT match_id, innings, batter,
                   DENSE_RANK() OVER (PARTITION BY match_id, innings ORDER BY MIN(over*6 + ball)) AS pos
            FROM deliveries
            WHERE batter IS NOT NULL
            GROUP BY match_id, innings, batter
        ),
        """
        bat_pos_join = "LEFT JOIN bat_pos bp ON bp.match_id = d.match_id AND bp.innings = d.innings AND bp.batter = d.batter"

    needs_partner_canon = ("partnership" in group_by) or ("non_striker" in group_by)
    pa_join = ""
    if needs_partner_canon:
        pa_join = (
            "LEFT JOIN player_aliases pa_bat ON pa_bat.player_name = d.batter "
            "LEFT JOIN player_aliases pa_ns  ON pa_ns.player_name = d.non_striker"
        )

    combined_query = f"""
        WITH {bat_pos_cte}all_groups AS (
            SELECT
                {select_group_clause},
                COUNT(*) as balls,
                COUNT(DISTINCT (d.match_id, d.innings)) as innings_count,
                {runs_calculation} as runs,
                SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                SUM(CASE WHEN d.runs_off_bat = 4 THEN 1 ELSE 0 END) as fours,
                SUM(CASE WHEN d.runs_off_bat = 6 THEN 1 ELSE 0 END) as sixes
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            LEFT JOIN players p ON p.name = d.bowler
            {bat_pos_join}
            {pa_join}
            {where_clause}
            GROUP BY {group_by_clause}
        )
        SELECT
            {final_select_groups},
            g.balls, g.innings_count, g.runs, g.wickets,
            g.dots, g.boundaries, g.fours, g.sixes,
            SUM(g.balls) OVER () as universe_balls,
            {parent_partition_sql} as parent_balls
        FROM all_groups g
        ORDER BY g.balls DESC
    """

    result = db.execute(text(combined_query), query_params).fetchall()

    formatted_results = []
    universe_balls = 0
    n = len(group_by)
    for row in result:
        row_dict = {col: row[i] for i, col in enumerate(group_by)}
        balls = row[n] or 0
        innings_count = row[n + 1] or 0
        runs = row[n + 2] or 0
        wickets = row[n + 3] or 0
        dots = row[n + 4] or 0
        boundaries = row[n + 5] or 0
        fours = row[n + 6] or 0
        sixes = row[n + 7] or 0
        universe_balls = row[n + 8] or 0
        parent_balls = row[n + 9]

        # total_balls_override (if supplied) wins for percent_balls denom —
        # caller may want a different universe than this query's WHERE.
        denominator = total_balls_override if total_balls_override is not None else universe_balls

        if len(group_by) > 1 and parent_balls is not None and parent_balls > 0:
            percent_balls = round((balls / parent_balls) * 100, 2)
        elif denominator > 0:
            percent_balls = round((balls / denominator) * 100, 2)
        else:
            percent_balls = 0

        row_dict.update({
            "balls": balls,
            "innings_count": innings_count,
            "runs": runs,
            "wickets": wickets,
            "dots": dots,
            "boundaries": boundaries,
            "fours": fours,
            "sixes": sixes,
            "average": round(runs / wickets, 2) if wickets > 0 else None,
            "strike_rate": round((runs * 100.0) / balls, 2) if balls > 0 else 0,
            "balls_per_dismissal": round(balls / wickets, 2) if wickets > 0 else None,
            "dot_percentage": round((dots * 100.0) / balls, 2) if balls > 0 else 0,
            "boundary_percentage": round((boundaries * 100.0) / balls, 2) if balls > 0 else 0,
            "percent_balls": percent_balls,
            # control_percentage intentionally omitted — not in legacy schema
        })
        formatted_results.append(row_dict)

    # Empty result: window functions had no rows to evaluate. Fallback only
    # when caller didn't supply an override.
    if not formatted_results and total_balls_override is None:
        fallback_query = f"""
            SELECT COUNT(*)
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            LEFT JOIN players p ON p.name = d.bowler
            {where_clause}
        """
        universe_balls = db.execute(text(fallback_query), query_params).scalar() or 0

    total_balls = total_balls_override if total_balls_override is not None else universe_balls
    return formatted_results, total_balls


def get_legacy_total_balls(where_clause, params, db):
    """Get total ball count from legacy table for a given WHERE clause."""
    count_query = f"""
        SELECT COUNT(*) 
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        LEFT JOIN players p ON p.name = d.bowler
        {where_clause}
    """
    count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs', 'min_wickets', 'max_wickets']}
    return db.execute(text(count_query), count_params).scalar()


# =============================================================================
# MERGE FUNCTIONS FOR COMBINING RESULTS FROM BOTH TABLES
# =============================================================================

def load_player_aliases_for_merge(db) -> Dict[str, str]:
    """
    Load all player aliases into a dict for efficient lookup during merge.
    Returns: {old_name: new_name, ...}
    """
    try:
        query = text("SELECT player_name, alias_name FROM player_aliases")
        result = db.execute(query).fetchall()
        # player_name is OLD (deliveries), alias_name is NEW (delivery_details)
        return {row[0]: row[1] for row in result}
    except Exception as e:
        logger.warning(f"Error loading player aliases: {e}")
        return {}


def normalize_player_name_for_merge(name: str, player_aliases_map: Dict[str, str]) -> str:
    """
    Normalize a player name to the canonical (new) form for merging.
    Uses pre-loaded aliases map for efficiency.
    """
    if not name:
        return name
    # If name is in aliases map (old name -> new name), use the new name
    return player_aliases_map.get(name, name)


def normalize_partnership_for_merge(value: str, player_aliases_map: Dict[str, str]) -> str:
    """
    Normalize a "X & Y" partnership string by canonicalizing each side and
    sorting alphabetically so (Kohli, ABD) and (ABD, Kohli) collapse to one
    group. Also handles the legacy/new name split: a partnership with a
    legacy name on either side is brought into the canonical form.
    """
    if not value or '&' not in value:
        return value
    parts = [p.strip() for p in value.split('&', 1)]
    if len(parts) != 2:
        return value
    a = normalize_player_name_for_merge(parts[0], player_aliases_map)
    b = normalize_player_name_for_merge(parts[1], player_aliases_map)
    a, b = sorted([a, b])
    return f"{a} & {b}"


def merge_grouped_results(
    new_results: List[Dict], 
    legacy_results: List[Dict], 
    group_by: List[str],
    player_aliases_map: Dict[str, str],
    total_balls: int
) -> List[Dict]:
    """
    Merge grouped results from both tables, combining rows with matching group keys.
    Recalculates derived metrics after merging raw counts.
    For multi-level groupings, percent_balls is relative to parent group.
    """
    if not legacy_results:
        return new_results
    def _normalize_row(row: Dict) -> None:
        if 'batter' in row and row.get('batter'):
            row['batter'] = normalize_player_name_for_merge(row['batter'], player_aliases_map)
        if 'bowler' in row and row.get('bowler'):
            row['bowler'] = normalize_player_name_for_merge(row['bowler'], player_aliases_map)
        if 'non_striker' in row and row.get('non_striker'):
            row['non_striker'] = normalize_player_name_for_merge(row['non_striker'], player_aliases_map)
        if 'partnership' in row and row.get('partnership'):
            row['partnership'] = normalize_partnership_for_merge(row['partnership'], player_aliases_map)
        if 'crease_combo' in row and row.get('crease_combo'):
            row['crease_combo'] = row['crease_combo'].lower()

    if not new_results:
        for row in legacy_results:
            _normalize_row(row)
        return legacy_results

    # Build a lookup by group key
    merged = {}

    def make_group_key(row: Dict) -> tuple:
        """Create a hashable key from grouping columns."""
        key_parts = []
        for col in group_by:
            val = row.get(col)
            if col in ('batter', 'bowler', 'non_striker') and val:
                val = normalize_player_name_for_merge(val, player_aliases_map)
            elif col == 'partnership' and val:
                val = normalize_partnership_for_merge(val, player_aliases_map)
            elif col == 'crease_combo' and val:
                val = val.lower()
            key_parts.append(str(val) if val is not None else '')
        return tuple(key_parts)

    # Add new results first
    for row in new_results:
        key = make_group_key(row)
        merged[key] = row.copy()

    # Merge legacy results
    for row in legacy_results:
        _normalize_row(row)
        
        key = make_group_key(row)
        
        if key in merged:
            # Combine raw counts
            existing = merged[key]
            existing['balls'] = (existing.get('balls') or 0) + (row.get('balls') or 0)
            existing['innings_count'] = (existing.get('innings_count') or 0) + (row.get('innings_count') or 0)
            existing['runs'] = (existing.get('runs') or 0) + (row.get('runs') or 0)
            existing['wickets'] = (existing.get('wickets') or 0) + (row.get('wickets') or 0)
            existing['dots'] = (existing.get('dots') or 0) + (row.get('dots') or 0)
            existing['boundaries'] = (existing.get('boundaries') or 0) + (row.get('boundaries') or 0)
            existing['fours'] = (existing.get('fours') or 0) + (row.get('fours') or 0)
            existing['sixes'] = (existing.get('sixes') or 0) + (row.get('sixes') or 0)
        else:
            # New group from legacy
            merged[key] = row.copy()
    
    # Convert to list
    result_list = list(merged.values())
    
    # For multi-level grouping, compute parent totals from merged data
    parent_totals = {}
    if len(group_by) > 1:
        for row in result_list:
            parent_key = str(row.get(group_by[0]))
            parent_totals[parent_key] = parent_totals.get(parent_key, 0) + (row.get('balls') or 0)
    
    # Recalculate derived metrics for all rows
    for row in result_list:
        balls = row.get('balls', 0)
        runs = row.get('runs', 0)
        wickets = row.get('wickets', 0)
        dots = row.get('dots', 0)
        boundaries = row.get('boundaries', 0)
        
        # Calculate percent_balls relative to parent group (for multi-level) or total (for single-level)
        if len(group_by) > 1 and parent_totals:
            parent_key = str(row.get(group_by[0]))
            parent_balls = parent_totals.get(parent_key, total_balls)
            row['percent_balls'] = round((balls / parent_balls) * 100, 2) if parent_balls > 0 else 0
        else:
            row['percent_balls'] = round((balls / total_balls) * 100, 2) if total_balls > 0 else 0
        
        # Recalculate other metrics
        row['average'] = round(runs / wickets, 2) if wickets > 0 else None
        row['strike_rate'] = round((runs * 100.0) / balls, 2) if balls > 0 else 0
        row['balls_per_dismissal'] = round(balls / wickets, 2) if wickets > 0 else None
        row['dot_percentage'] = round((dots * 100.0) / balls, 2) if balls > 0 else 0
        row['boundary_percentage'] = round((boundaries * 100.0) / balls, 2) if balls > 0 else 0
        
        # control_percentage stays as-is from new data (will be None if only legacy)
    
    # Sort by balls descending
    result_list.sort(key=lambda x: x.get('balls', 0), reverse=True)
    
    return result_list


def merge_ungrouped_results(
    new_results: List[Dict],
    legacy_results: List[Dict],
    player_aliases_map: Dict[str, str]
) -> List[Dict]:
    """
    Merge ungrouped (individual delivery) results from both tables.
    Simply concatenates and sorts by date/time.
    """
    # Normalize legacy player names
    for row in legacy_results:
        if row.get('batter'):
            row['batter'] = normalize_player_name_for_merge(row['batter'], player_aliases_map)
        if row.get('bowler'):
            row['bowler'] = normalize_player_name_for_merge(row['bowler'], player_aliases_map)
        if row.get('non_striker'):
            row['non_striker'] = normalize_player_name_for_merge(row['non_striker'], player_aliases_map)
    
    # Combine and sort by year desc, then match/innings/over/ball
    combined = new_results + legacy_results
    combined.sort(
        key=lambda x: (
            -(x.get('year') or 0),
            x.get('match_id') or '',
            x.get('innings') or 0,
            x.get('over') or 0,
            x.get('ball') or 0
        )
    )
    
    return combined


def _normalize_lower_list(values: List[str]) -> List[str]:
    return [str(v).strip().lower() for v in (values or []) if str(v).strip()]


def _validate_enum_list(values: List[str], allowed: Set[str], field_name: str) -> List[str]:
    normalized = _normalize_lower_list(values)
    invalid = sorted({v for v in normalized if v not in allowed})
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} values: {invalid}")
    return normalized


def _expand_team_canonical_tokens(team_names: List[str]) -> List[str]:
    tokens = set()
    for team in team_names or []:
        for variation in get_all_team_name_variations(team):
            lowered = variation.lower()
            tokens.add(TEAM_CANONICAL_MAP.get(lowered, lowered))
        lowered_team = str(team).lower()
        tokens.add(TEAM_CANONICAL_MAP.get(lowered_team, lowered_team))
    return list(tokens)


def _validate_chase_filter_consistency(
    chase_outcome: List[str],
    is_chase: Optional[bool],
    innings: Optional[int],
) -> None:
    if not chase_outcome:
        return
    if is_chase is False:
        raise HTTPException(
            status_code=400,
            detail="chase_outcome cannot be used when is_chase=false",
        )
    if innings is not None and innings != 2:
        raise HTTPException(
            status_code=400,
            detail="chase_outcome requires innings=2 (or omit innings)",
        )


def _match_context_warning(match_context_used: bool) -> List[str]:
    if not match_context_used:
        return []
    return [
        "Team names are normalized for winner/batting/bowling comparison. Unresolved mismatches are classified as no_result."
    ]


def query_batting_stats_service(
    venue: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    teams: List[str],
    batting_teams: List[str],
    bowling_teams: List[str],
    players: List[str],
    batters: List[str],
    bowlers: List[str],
    innings: Optional[int],
    group_by: List[str],
    min_balls: Optional[int],
    max_balls: Optional[int],
    min_runs: Optional[int],
    max_runs: Optional[int],
    limit: int,
    offset: int,
    include_international: bool,
    top_teams: Optional[int],
    match_outcome: List[str],
    is_chase: Optional[bool],
    chase_outcome: List[str],
    toss_decision: List[str],
    db,
):
    if bowlers:
        raise HTTPException(status_code=400, detail="bowlers filter is unsupported for query_mode=batting_stats")

    allowed_group_by = {
        "venue", "competition", "year", "batting_team", "bowling_team",
        "batter", "innings", "match_outcome", "chase_outcome", "toss_decision",
        "match_id", "toss_match_outcome"
    }
    invalid_group_by = [c for c in group_by if c not in allowed_group_by]
    if invalid_group_by:
        raise HTTPException(status_code=400, detail=f"Invalid group_by columns for batting_stats: {invalid_group_by}")

    _validate_chase_filter_consistency(chase_outcome, is_chase, innings)
    match_outcome = _validate_enum_list(match_outcome, VALID_MATCH_OUTCOMES, "match_outcome")
    chase_outcome = _validate_enum_list(chase_outcome, VALID_MATCH_OUTCOMES, "chase_outcome")
    toss_decision = _validate_enum_list(toss_decision, VALID_TOSS_DECISIONS, "toss_decision")

    batting_team_expr = "bs.batting_team"
    bowling_team_expr = f"""(
        CASE
            WHEN {get_team_canonical_sql('bs.batting_team')} = {get_team_canonical_sql('m.team1')} THEN m.team2
            WHEN {get_team_canonical_sql('bs.batting_team')} = {get_team_canonical_sql('m.team2')} THEN m.team1
            ELSE NULL
        END
    )"""
    match_outcome_sql = get_match_outcome_sql(
        batting_team_expr=batting_team_expr,
        bowling_team_expr=bowling_team_expr,
        winner_expr="m.winner",
        outcome_json_expr="m.outcome",
    )
    chase_outcome_sql = get_chase_outcome_sql("bs.innings", match_outcome_sql)

    conditions = ["1=1"]
    params = {"limit": min(limit, 10000), "offset": offset}

    if venue:
        params["venue_aliases"] = get_venue_aliases(venue)
        conditions.append("m.venue = ANY(:venue_aliases)")
    if start_date:
        conditions.append("m.date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("m.date <= :end_date")
        params["end_date"] = end_date

    competition_conditions = []
    if leagues:
        expanded_leagues = expand_league_abbreviations(leagues)
        competition_conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
        params["leagues"] = expanded_leagues
    if include_international:
        if top_teams:
            top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            competition_conditions.append(
                "(m.match_type = 'international' AND m.team1 = ANY(:top_teams) AND m.team2 = ANY(:top_teams))"
            )
            params["top_teams"] = top_team_list
        else:
            competition_conditions.append("m.match_type = 'international'")
    if competition_conditions:
        conditions.append("(" + " OR ".join(competition_conditions) + ")")

    if teams:
        params["teams_tokens"] = _expand_team_canonical_tokens(teams)
        conditions.append(
            f"({get_team_canonical_sql('bs.batting_team')} = ANY(:teams_tokens) OR {get_team_canonical_sql(bowling_team_expr)} = ANY(:teams_tokens))"
        )
    if batting_teams:
        params["batting_teams_tokens"] = _expand_team_canonical_tokens(batting_teams)
        conditions.append(f"{get_team_canonical_sql('bs.batting_team')} = ANY(:batting_teams_tokens)")
    if bowling_teams:
        params["bowling_teams_tokens"] = _expand_team_canonical_tokens(bowling_teams)
        conditions.append(f"{get_team_canonical_sql(bowling_team_expr)} = ANY(:bowling_teams_tokens)")

    if players:
        params["players"] = _expand_player_names(players, db) if db else players
        conditions.append("bs.striker = ANY(:players)")
    if batters:
        params["batters"] = _expand_player_names(batters, db) if db else batters
        conditions.append("bs.striker = ANY(:batters)")

    if innings:
        conditions.append("bs.innings = :innings")
        params["innings"] = innings
    if is_chase is True:
        conditions.append("bs.innings = 2")
    elif is_chase is False:
        conditions.append("bs.innings != 2")
    if match_outcome:
        conditions.append(f"{match_outcome_sql} = ANY(:match_outcome)")
        params["match_outcome"] = match_outcome
    if chase_outcome:
        conditions.append("bs.innings = 2")
        conditions.append(f"{chase_outcome_sql} = ANY(:chase_outcome)")
        params["chase_outcome"] = chase_outcome
    if toss_decision:
        conditions.append("LOWER(COALESCE(m.toss_decision, '')) = ANY(:toss_decision)")
        params["toss_decision"] = toss_decision

    where_clause = "WHERE " + " AND ".join(conditions)
    filters_applied = {
        "query_mode": "batting_stats",
        "venue": venue,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "leagues": leagues,
        "teams": teams,
        "batting_teams": batting_teams,
        "bowling_teams": bowling_teams,
        "players": players,
        "batters": batters,
        "innings": innings,
        "is_chase": is_chase,
        "match_outcome": match_outcome,
        "chase_outcome": chase_outcome,
        "toss_decision": toss_decision,
        "group_by": group_by,
    }
    warnings = _match_context_warning(match_context_requested(match_outcome, is_chase, chase_outcome, toss_decision, group_by))

    if not group_by:
        main_query = f"""
            SELECT
                bs.match_id,
                m.date,
                m.venue,
                m.competition,
                bs.innings,
                bs.striker AS batter,
                bs.batting_team,
                {bowling_team_expr} AS bowling_team,
                bs.runs,
                bs.balls_faced,
                bs.wickets AS dismissals,
                bs.fours,
                bs.sixes,
                bs.dots,
                bs.strike_rate,
                {match_outcome_sql} AS match_outcome,
                {chase_outcome_sql} AS chase_outcome,
                LOWER(COALESCE(m.toss_decision, '')) AS toss_decision
            FROM batting_stats bs
            JOIN matches m ON m.id = bs.match_id
            {where_clause}
            ORDER BY m.date DESC, bs.match_id
            LIMIT :limit
            OFFSET :offset
        """
        result = db.execute(text(main_query), params).fetchall()
        formatted = [
            {
                "match_id": row[0],
                "date": row[1].isoformat() if row[1] else None,
                "venue": row[2],
                "competition": row[3],
                "innings": row[4],
                "batter": row[5],
                "batting_team": row[6],
                "bowling_team": row[7],
                "runs": row[8],
                "balls_faced": row[9],
                "dismissals": row[10],
                "fours": row[11],
                "sixes": row[12],
                "dots": row[13],
                "strike_rate": float(row[14]) if row[14] is not None else 0.0,
                "match_outcome": row[15],
                "chase_outcome": row[16],
                "toss_decision": row[17],
            }
            for row in result
        ]
        count_query = f"""
            SELECT COUNT(*)
            FROM batting_stats bs
            JOIN matches m ON m.id = bs.match_id
            {where_clause}
        """
        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
        total_count = db.execute(text(count_query), count_params).scalar() or 0
        return {
            "data": formatted,
            "metadata": {
                "total_matching_rows": total_count,
                "total_innings_in_query": total_count,
                "returned_rows": len(formatted),
                "limit": limit,
                "offset": offset,
                "has_more": total_count > (offset + len(formatted)),
                "filters_applied": filters_applied,
                "query_mode_used": "batting_stats",
                "data_source": "batting_stats",
                "warnings": warnings,
                "note": "Innings-level batting statistics",
            }
        }

    grouping_columns = {
        "venue": "m.venue",
        "competition": "m.competition",
        "year": "EXTRACT(YEAR FROM m.date)",
        "batting_team": "bs.batting_team",
        "bowling_team": bowling_team_expr,
        "batter": "bs.striker",
        "innings": "bs.innings",
        "match_id": "bs.match_id",
        "match_outcome": match_outcome_sql,
        "chase_outcome": chase_outcome_sql,
        "toss_decision": "LOWER(COALESCE(m.toss_decision, ''))",
        "toss_match_outcome": get_toss_match_outcome_sql("m.toss_winner", "m.winner", "m.outcome"),
    }
    group_cols = [grouping_columns[c] for c in group_by]
    select_cols = [f"{grouping_columns[c]} AS {c}" for c in group_by]
    group_by_clause = ", ".join(group_cols)
    select_group_clause = ", ".join(select_cols)

    having_conditions = []
    if min_balls is not None:
        having_conditions.append("SUM(bs.balls_faced) >= :min_balls")
        params["min_balls"] = min_balls
    if max_balls is not None:
        having_conditions.append("SUM(bs.balls_faced) <= :max_balls")
        params["max_balls"] = max_balls
    if min_runs is not None:
        having_conditions.append("SUM(bs.runs) >= :min_runs")
        params["min_runs"] = min_runs
    if max_runs is not None:
        having_conditions.append("SUM(bs.runs) <= :max_runs")
        params["max_runs"] = max_runs
    having_conditions.append("(SUM(bs.runs) > 0 OR SUM(bs.balls_faced) > 0)")
    having_clause = "HAVING " + " AND ".join(having_conditions) if having_conditions else ""

    aggregation_query = f"""
        SELECT
            {select_group_clause},
            COUNT(*) AS innings_count,
            SUM(bs.runs) AS runs,
            SUM(bs.balls_faced) AS balls_faced,
            SUM(bs.wickets) AS dismissals,
            SUM(bs.fours) AS fours,
            SUM(bs.sixes) AS sixes,
            SUM(bs.dots) AS dots,
            CASE WHEN SUM(bs.balls_faced) > 0 THEN (SUM(bs.runs)::DECIMAL * 100.0) / SUM(bs.balls_faced) ELSE 0 END AS strike_rate,
            CASE WHEN SUM(bs.wickets) > 0 THEN SUM(bs.runs)::DECIMAL / SUM(bs.wickets) ELSE NULL END AS average
        FROM batting_stats bs
        JOIN matches m ON m.id = bs.match_id
        {where_clause}
        GROUP BY {group_by_clause}
        {having_clause}
        ORDER BY innings_count DESC
        LIMIT :limit
        OFFSET :offset
    """
    result = db.execute(text(aggregation_query), params).fetchall()
    formatted = []
    for row in result:
        payload = {col: row[i] for i, col in enumerate(group_by)}
        s = len(group_by)
        payload.update({
            "innings_count": row[s],
            "runs": row[s + 1],
            "balls_faced": row[s + 2],
            "dismissals": row[s + 3],
            "fours": row[s + 4],
            "sixes": row[s + 5],
            "dots": row[s + 6],
            "strike_rate": round(float(row[s + 7]), 2) if row[s + 7] is not None else 0.0,
            "average": round(float(row[s + 8]), 2) if row[s + 8] is not None else None,
        })
        formatted.append(payload)

    count_query = f"""
        SELECT COUNT(*) FROM (
            SELECT {group_by_clause}
            FROM batting_stats bs
            JOIN matches m ON m.id = bs.match_id
            {where_clause}
            GROUP BY {group_by_clause}
            {having_clause}
        ) grouped_count
    """
    count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
    total_groups = db.execute(text(count_query), count_params).scalar() or 0
    innings_total_query = f"""
        SELECT COALESCE(SUM(innings_count), 0) FROM (
            SELECT COUNT(*) AS innings_count
            FROM batting_stats bs
            JOIN matches m ON m.id = bs.match_id
            {where_clause}
            GROUP BY {group_by_clause}
            {having_clause}
        ) grouped_innings
    """
    total_innings_in_query = db.execute(text(innings_total_query), count_params).scalar() or 0
    return {
        "data": formatted,
        "summary_data": None,
        "percentages": None,
        "metadata": {
            "total_groups": total_groups,
            "total_innings_in_query": total_innings_in_query,
            "returned_groups": len(formatted),
            "limit": limit,
            "offset": offset,
            "has_more": total_groups > (offset + len(formatted)),
            "grouped_by": group_by,
            "filters_applied": filters_applied,
            "has_summaries": False,
            "query_mode_used": "batting_stats",
            "data_source": "batting_stats",
            "warnings": warnings,
            "note": "Grouped innings-level batting statistics",
        },
    }


def query_bowling_stats_service(
    venue: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    teams: List[str],
    batting_teams: List[str],
    bowling_teams: List[str],
    players: List[str],
    batters: List[str],
    bowlers: List[str],
    innings: Optional[int],
    group_by: List[str],
    min_balls: Optional[int],
    max_balls: Optional[int],
    min_runs: Optional[int],
    max_runs: Optional[int],
    min_wickets: Optional[int],
    max_wickets: Optional[int],
    limit: int,
    offset: int,
    include_international: bool,
    top_teams: Optional[int],
    match_outcome: List[str],
    is_chase: Optional[bool],
    chase_outcome: List[str],
    toss_decision: List[str],
    db,
):
    if batters:
        raise HTTPException(status_code=400, detail="batters filter is unsupported for query_mode=bowling_stats")

    allowed_group_by = {
        "venue", "competition", "year", "batting_team", "bowling_team",
        "bowler", "innings", "match_outcome", "chase_outcome", "toss_decision",
        "match_id", "toss_match_outcome"
    }
    invalid_group_by = [c for c in group_by if c not in allowed_group_by]
    if invalid_group_by:
        raise HTTPException(status_code=400, detail=f"Invalid group_by columns for bowling_stats: {invalid_group_by}")

    _validate_chase_filter_consistency(chase_outcome, is_chase, innings)
    match_outcome = _validate_enum_list(match_outcome, VALID_MATCH_OUTCOMES, "match_outcome")
    chase_outcome = _validate_enum_list(chase_outcome, VALID_MATCH_OUTCOMES, "chase_outcome")
    toss_decision = _validate_enum_list(toss_decision, VALID_TOSS_DECISIONS, "toss_decision")

    bowling_team_expr = "bs.bowling_team"
    batting_team_expr = f"""(
        CASE
            WHEN {get_team_canonical_sql('bs.bowling_team')} = {get_team_canonical_sql('m.team1')} THEN m.team2
            WHEN {get_team_canonical_sql('bs.bowling_team')} = {get_team_canonical_sql('m.team2')} THEN m.team1
            ELSE NULL
        END
    )"""
    match_outcome_sql = get_match_outcome_sql(
        batting_team_expr=batting_team_expr,
        bowling_team_expr=bowling_team_expr,
        winner_expr="m.winner",
        outcome_json_expr="m.outcome",
    )
    chase_outcome_sql = get_chase_outcome_sql("bs.innings", match_outcome_sql)

    conditions = ["1=1"]
    params = {"limit": min(limit, 10000), "offset": offset}

    if venue:
        params["venue_aliases"] = get_venue_aliases(venue)
        conditions.append("m.venue = ANY(:venue_aliases)")
    if start_date:
        conditions.append("m.date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("m.date <= :end_date")
        params["end_date"] = end_date

    competition_conditions = []
    if leagues:
        expanded_leagues = expand_league_abbreviations(leagues)
        competition_conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
        params["leagues"] = expanded_leagues
    if include_international:
        if top_teams:
            top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            competition_conditions.append(
                "(m.match_type = 'international' AND m.team1 = ANY(:top_teams) AND m.team2 = ANY(:top_teams))"
            )
            params["top_teams"] = top_team_list
        else:
            competition_conditions.append("m.match_type = 'international'")
    if competition_conditions:
        conditions.append("(" + " OR ".join(competition_conditions) + ")")

    if teams:
        params["teams_tokens"] = _expand_team_canonical_tokens(teams)
        conditions.append(
            f"({get_team_canonical_sql('bs.bowling_team')} = ANY(:teams_tokens) OR {get_team_canonical_sql(batting_team_expr)} = ANY(:teams_tokens))"
        )
    if batting_teams:
        params["batting_teams_tokens"] = _expand_team_canonical_tokens(batting_teams)
        conditions.append(f"{get_team_canonical_sql(batting_team_expr)} = ANY(:batting_teams_tokens)")
    if bowling_teams:
        params["bowling_teams_tokens"] = _expand_team_canonical_tokens(bowling_teams)
        conditions.append(f"{get_team_canonical_sql('bs.bowling_team')} = ANY(:bowling_teams_tokens)")

    if players:
        params["players"] = _expand_player_names(players, db) if db else players
        conditions.append("bs.bowler = ANY(:players)")
    if bowlers:
        params["bowlers"] = _expand_player_names(bowlers, db) if db else bowlers
        conditions.append("bs.bowler = ANY(:bowlers)")

    if innings:
        conditions.append("bs.innings = :innings")
        params["innings"] = innings
    if is_chase is True:
        conditions.append("bs.innings = 2")
    elif is_chase is False:
        conditions.append("bs.innings != 2")
    if match_outcome:
        conditions.append(f"{match_outcome_sql} = ANY(:match_outcome)")
        params["match_outcome"] = match_outcome
    if chase_outcome:
        conditions.append("bs.innings = 2")
        conditions.append(f"{chase_outcome_sql} = ANY(:chase_outcome)")
        params["chase_outcome"] = chase_outcome
    if toss_decision:
        conditions.append("LOWER(COALESCE(m.toss_decision, '')) = ANY(:toss_decision)")
        params["toss_decision"] = toss_decision
    if not group_by:
        if min_wickets is not None:
            conditions.append("bs.wickets >= :min_wickets")
            params["min_wickets"] = min_wickets
        if max_wickets is not None:
            conditions.append("bs.wickets <= :max_wickets")
            params["max_wickets"] = max_wickets

    where_clause = "WHERE " + " AND ".join(conditions)
    filters_applied = {
        "query_mode": "bowling_stats",
        "venue": venue,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "leagues": leagues,
        "teams": teams,
        "batting_teams": batting_teams,
        "bowling_teams": bowling_teams,
        "players": players,
        "bowlers": bowlers,
        "innings": innings,
        "is_chase": is_chase,
        "match_outcome": match_outcome,
        "chase_outcome": chase_outcome,
        "toss_decision": toss_decision,
        "min_wickets": min_wickets,
        "max_wickets": max_wickets,
        "group_by": group_by,
    }
    warnings = _match_context_warning(match_context_requested(match_outcome, is_chase, chase_outcome, toss_decision, group_by))

    if not group_by:
        main_query = f"""
            SELECT
                bs.match_id,
                m.date,
                m.venue,
                m.competition,
                bs.innings,
                bs.bowler,
                {batting_team_expr} AS batting_team,
                bs.bowling_team,
                bs.overs,
                bs.runs_conceded,
                bs.wickets,
                bs.dots,
                bs.fours_conceded,
                bs.sixes_conceded,
                bs.economy,
                {match_outcome_sql} AS match_outcome,
                {chase_outcome_sql} AS chase_outcome,
                LOWER(COALESCE(m.toss_decision, '')) AS toss_decision
            FROM bowling_stats bs
            JOIN matches m ON m.id = bs.match_id
            {where_clause}
            ORDER BY m.date DESC, bs.match_id
            LIMIT :limit
            OFFSET :offset
        """
        result = db.execute(text(main_query), params).fetchall()
        formatted = [
            {
                "match_id": row[0],
                "date": row[1].isoformat() if row[1] else None,
                "venue": row[2],
                "competition": row[3],
                "innings": row[4],
                "bowler": row[5],
                "batting_team": row[6],
                "bowling_team": row[7],
                "overs": float(row[8]) if row[8] is not None else 0.0,
                "runs_conceded": row[9],
                "wickets": row[10],
                "dots": row[11],
                "fours_conceded": row[12],
                "sixes_conceded": row[13],
                "economy": float(row[14]) if row[14] is not None else 0.0,
                "match_outcome": row[15],
                "chase_outcome": row[16],
                "toss_decision": row[17],
            }
            for row in result
        ]
        count_query = f"""
            SELECT COUNT(*)
            FROM bowling_stats bs
            JOIN matches m ON m.id = bs.match_id
            {where_clause}
        """
        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
        total_count = db.execute(text(count_query), count_params).scalar() or 0
        return {
            "data": formatted,
            "metadata": {
                "total_matching_rows": total_count,
                "total_innings_in_query": total_count,
                "returned_rows": len(formatted),
                "limit": limit,
                "offset": offset,
                "has_more": total_count > (offset + len(formatted)),
                "filters_applied": filters_applied,
                "query_mode_used": "bowling_stats",
                "data_source": "bowling_stats",
                "warnings": warnings,
                "note": "Innings-level bowling statistics",
            }
        }

    grouping_columns = {
        "venue": "m.venue",
        "competition": "m.competition",
        "year": "EXTRACT(YEAR FROM m.date)",
        "batting_team": batting_team_expr,
        "bowling_team": "bs.bowling_team",
        "bowler": "bs.bowler",
        "innings": "bs.innings",
        "match_id": "bs.match_id",
        "match_outcome": match_outcome_sql,
        "chase_outcome": chase_outcome_sql,
        "toss_decision": "LOWER(COALESCE(m.toss_decision, ''))",
        "toss_match_outcome": get_toss_match_outcome_sql("m.toss_winner", "m.winner", "m.outcome"),
    }
    group_cols = [grouping_columns[c] for c in group_by]
    select_cols = [f"{grouping_columns[c]} AS {c}" for c in group_by]
    group_by_clause = ", ".join(group_cols)
    select_group_clause = ", ".join(select_cols)

    having_conditions = []
    if min_balls is not None:
        having_conditions.append("(SUM(bs.overs) * 6.0) >= :min_balls")
        params["min_balls"] = min_balls
    if max_balls is not None:
        having_conditions.append("(SUM(bs.overs) * 6.0) <= :max_balls")
        params["max_balls"] = max_balls
    if min_runs is not None:
        having_conditions.append("SUM(bs.runs_conceded) >= :min_runs")
        params["min_runs"] = min_runs
    if max_runs is not None:
        having_conditions.append("SUM(bs.runs_conceded) <= :max_runs")
        params["max_runs"] = max_runs
    if min_wickets is not None:
        having_conditions.append("SUM(bs.wickets) >= :group_min_wickets")
        params["group_min_wickets"] = min_wickets
    if max_wickets is not None:
        having_conditions.append("SUM(bs.wickets) <= :group_max_wickets")
        params["group_max_wickets"] = max_wickets
    having_clause = "HAVING " + " AND ".join(having_conditions) if having_conditions else ""

    aggregation_query = f"""
        SELECT
            {select_group_clause},
            COUNT(*) AS innings_count,
            SUM(bs.overs) AS overs,
            SUM(bs.runs_conceded) AS runs_conceded,
            SUM(bs.wickets) AS wickets,
            SUM(bs.dots) AS dots,
            SUM(bs.fours_conceded) AS fours_conceded,
            SUM(bs.sixes_conceded) AS sixes_conceded,
            CASE WHEN SUM(bs.overs) > 0 THEN SUM(bs.runs_conceded)::DECIMAL / SUM(bs.overs) ELSE 0 END AS economy,
            CASE WHEN SUM(bs.wickets) > 0 THEN SUM(bs.runs_conceded)::DECIMAL / SUM(bs.wickets) ELSE NULL END AS average,
            CASE WHEN SUM(bs.wickets) > 0 THEN (SUM(bs.overs) * 6.0)::DECIMAL / SUM(bs.wickets) ELSE NULL END AS balls_per_wicket
        FROM bowling_stats bs
        JOIN matches m ON m.id = bs.match_id
        {where_clause}
        GROUP BY {group_by_clause}
        {having_clause}
        ORDER BY innings_count DESC
        LIMIT :limit
        OFFSET :offset
    """
    result = db.execute(text(aggregation_query), params).fetchall()
    formatted = []
    for row in result:
        payload = {col: row[i] for i, col in enumerate(group_by)}
        s = len(group_by)
        payload.update({
            "innings_count": row[s],
            "overs": round(float(row[s + 1]), 2) if row[s + 1] is not None else 0.0,
            "runs_conceded": row[s + 2],
            "wickets": row[s + 3],
            "dots": row[s + 4],
            "fours_conceded": row[s + 5],
            "sixes_conceded": row[s + 6],
            "economy": round(float(row[s + 7]), 2) if row[s + 7] is not None else 0.0,
            "average": round(float(row[s + 8]), 2) if row[s + 8] is not None else None,
            "balls_per_wicket": round(float(row[s + 9]), 2) if row[s + 9] is not None else None,
        })
        formatted.append(payload)

    count_query = f"""
        SELECT COUNT(*) FROM (
            SELECT {group_by_clause}
            FROM bowling_stats bs
            JOIN matches m ON m.id = bs.match_id
            {where_clause}
            GROUP BY {group_by_clause}
            {having_clause}
        ) grouped_count
    """
    count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
    total_groups = db.execute(text(count_query), count_params).scalar() or 0
    innings_total_query = f"""
        SELECT COALESCE(SUM(innings_count), 0) FROM (
            SELECT COUNT(*) AS innings_count
            FROM bowling_stats bs
            JOIN matches m ON m.id = bs.match_id
            {where_clause}
            GROUP BY {group_by_clause}
            {having_clause}
        ) grouped_innings
    """
    total_innings_in_query = db.execute(text(innings_total_query), count_params).scalar() or 0
    return {
        "data": formatted,
        "summary_data": None,
        "percentages": None,
        "metadata": {
            "total_groups": total_groups,
            "total_innings_in_query": total_innings_in_query,
            "returned_groups": len(formatted),
            "limit": limit,
            "offset": offset,
            "has_more": total_groups > (offset + len(formatted)),
            "grouped_by": group_by,
            "filters_applied": filters_applied,
            "has_summaries": False,
            "query_mode_used": "bowling_stats",
            "data_source": "bowling_stats",
            "warnings": warnings,
            "note": "Grouped innings-level bowling statistics",
        },
    }


def query_deliveries_service(
    # Basic filters
    venue: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    teams: List[str],
    batting_teams: List[str],
    bowling_teams: List[str],
    players: List[str],
    batters: List[str],
    bowlers: List[str],
    
    # Batter/Bowler filters
    bat_hand: Optional[str],
    bowl_style: List[str],
    bowl_kind: List[str],
    crease_combo: List[str],
    
    # Delivery detail filters
    line: List[str],
    length: List[str],
    shot: List[str],
    control: Optional[int],
    wagon_zone: List[int],
    dismissal: List[str],
    
    # Match context filters
    innings: Optional[int],
    over_min: Optional[int],
    over_max: Optional[int],
    match_outcome: List[str],
    is_chase: Optional[bool],
    chase_outcome: List[str],
    toss_decision: List[str],
    
    # Grouping and aggregation
    group_by: List[str],
    show_summary_rows: bool,
    
    # Filters for grouped results
    min_balls: Optional[int],
    max_balls: Optional[int],
    min_runs: Optional[int],
    max_runs: Optional[int],
    min_wickets: Optional[int],
    max_wickets: Optional[int],
    
    # Pagination and limits
    limit: int,
    offset: int,
    
    # Include international matches
    include_international: bool,
    top_teams: Optional[int],
    query_mode: str,
    
    db
):
    """
    Main service function to query cricket delivery data with flexible filtering and grouping.
    
    Routes queries to appropriate tables based on date range and columns used:
    - delivery_details: 2015+ data with advanced columns (line, length, shot, etc.)
    - deliveries: Pre-2015 data with basic columns
    
    For queries spanning both date ranges, results are merged with player name normalization.
    """
    try:
        logger.info(
            f"Query deliveries service called with query_mode={query_mode}, venue={venue}, leagues={leagues}, group_by={group_by}"
        )
        logger.info(f"Date range: {start_date} to {end_date}")

        if query_mode not in VALID_QUERY_MODES:
            raise HTTPException(status_code=400, detail=f"Invalid query_mode: {query_mode}")

        match_outcome = _validate_enum_list(match_outcome, VALID_MATCH_OUTCOMES, "match_outcome")
        chase_outcome = _validate_enum_list(chase_outcome, VALID_MATCH_OUTCOMES, "chase_outcome")
        toss_decision = _validate_enum_list(toss_decision, VALID_TOSS_DECISIONS, "toss_decision")
        _validate_chase_filter_consistency(chase_outcome, is_chase, innings)
        validate_mode_filters(
            query_mode=query_mode,
            bat_hand=bat_hand,
            bowl_style=bowl_style,
            bowl_kind=bowl_kind,
            crease_combo=crease_combo,
            line=line,
            length=length,
            shot=shot,
            control=control,
            wagon_zone=wagon_zone,
            dismissal=dismissal,
            over_min=over_min,
            over_max=over_max,
        )
        validate_wicket_filters(
            query_mode=query_mode,
            min_wickets=min_wickets,
            max_wickets=max_wickets,
        )

        if query_mode == "batting_stats":
            return query_batting_stats_service(
                venue=venue,
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                teams=teams,
                batting_teams=batting_teams,
                bowling_teams=bowling_teams,
                players=players,
                batters=batters,
                bowlers=bowlers,
                innings=innings,
                group_by=group_by,
                min_balls=min_balls,
                max_balls=max_balls,
                min_runs=min_runs,
                max_runs=max_runs,
                limit=limit,
                offset=offset,
                include_international=include_international,
                top_teams=top_teams,
                match_outcome=match_outcome,
                is_chase=is_chase,
                chase_outcome=chase_outcome,
                toss_decision=toss_decision,
                db=db,
            )
        if query_mode == "bowling_stats":
            return query_bowling_stats_service(
                venue=venue,
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                teams=teams,
                batting_teams=batting_teams,
                bowling_teams=bowling_teams,
                players=players,
                batters=batters,
                bowlers=bowlers,
                innings=innings,
                group_by=group_by,
                min_balls=min_balls,
                max_balls=max_balls,
                min_runs=min_runs,
                max_runs=max_runs,
                min_wickets=min_wickets,
                max_wickets=max_wickets,
                limit=limit,
                offset=offset,
                include_international=include_international,
                top_teams=top_teams,
                match_outcome=match_outcome,
                is_chase=is_chase,
                chase_outcome=chase_outcome,
                toss_decision=toss_decision,
                db=db,
            )
        
        # Prepare filters dict for routing analysis
        filters_for_routing = {
            'bat_hand': bat_hand,
            'bowl_style': bowl_style,
            'bowl_kind': bowl_kind,
            'line': line,
            'length': length,
            'shot': shot,
            'control': control,
            'wagon_zone': wagon_zone,
            'dismissal': dismissal,
        }
        
        # Analyze query to determine which tables to use
        routing = analyze_query_requirements(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by or [],
            filters_used=filters_for_routing
        )
        
        logger.info(f"Query routing: use_new={routing['use_new']}, use_legacy={routing['use_legacy']}, warnings={routing['warnings']}")
        
        # Prepare filters metadata
        filters_applied = {
            "query_mode": query_mode,
            "venue": venue,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "leagues": leagues,
            "teams": teams,
            "batting_teams": batting_teams,
            "bowling_teams": bowling_teams,
            "players": players,
            "batters": batters,
            "bowlers": bowlers,
            "bat_hand": bat_hand,
            "bowl_style": bowl_style,
            "bowl_kind": bowl_kind,
            "crease_combo": crease_combo,
            "line": line,
            "length": length,
            "shot": shot,
            "control": control,
            "wagon_zone": wagon_zone,
            "dismissal": dismissal,
            "innings": innings,
            "over_range": f"{over_min}-{over_max}" if over_min is not None or over_max is not None else None,
            "match_outcome": match_outcome,
            "is_chase": is_chase,
            "chase_outcome": chase_outcome,
            "toss_decision": toss_decision,
            "min_wickets": min_wickets,
            "max_wickets": max_wickets,
            "group_by": group_by
        }
        
        match_context_used = match_context_requested(
            match_outcome=match_outcome,
            is_chase=is_chase,
            chase_outcome=chase_outcome,
            toss_decision=toss_decision,
            group_by=group_by,
        )
        delivery_warnings = list(routing["warnings"]) + _match_context_warning(match_context_used)
        join_new_matches = match_context_used

        has_batter_filters = bool(batters) or bool(players)
        data_sources = []
        
        # =====================================================================
        # QUERY NEW TABLE (delivery_details) - 2015+
        # =====================================================================
        new_results = []
        new_total_count = 0
        new_total_balls = 0
        new_total_innings = 0
        
        if routing['use_new']:
            new_date_range = routing['new_date_range']
            new_start, new_end = new_date_range if new_date_range else (DELIVERY_DETAILS_START_DATE, end_date or date.today())
            
            new_params = {
                "limit": min(limit, 10000),
                "offset": offset
            }
            
            new_where_clause, new_params = build_where_clause(
                venue=venue,
                start_date=new_start,
                end_date=new_end,
                leagues=leagues,
                teams=teams,
                batting_teams=batting_teams,
                bowling_teams=bowling_teams,
                players=players,
                batters=batters,
                bowlers=bowlers,
                bat_hand=bat_hand,
                bowl_style=bowl_style,
                bowl_kind=bowl_kind,
                crease_combo=crease_combo,
                line=line,
                length=length,
                shot=shot,
                control=control,
                wagon_zone=wagon_zone,
                dismissal=dismissal,
                innings=innings,
                over_min=over_min,
                over_max=over_max,
                match_outcome=match_outcome,
                is_chase=is_chase,
                chase_outcome=chase_outcome,
                toss_decision=toss_decision,
                include_international=include_international,
                top_teams=top_teams,
                group_by=group_by,
                base_params=new_params,
                db=db
            )
            
            # Get total balls from new table
            new_join_clause = "JOIN matches m ON m.id = dd.p_match" if join_new_matches else ""
            total_balls_query = f"SELECT COUNT(*) FROM delivery_details dd {new_join_clause} {new_where_clause}"
            total_balls_params = {k: v for k, v in new_params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs', 'min_wickets', 'max_wickets']}
            new_total_balls = db.execute(text(total_balls_query), total_balls_params).scalar() or 0
            total_innings_query = f"SELECT COUNT(DISTINCT (dd.p_match, dd.inns)) FROM delivery_details dd {new_join_clause} {new_where_clause}"
            new_total_innings = db.execute(text(total_innings_query), total_balls_params).scalar() or 0
            
            if not group_by or len(group_by) == 0:
                # Ungrouped query
                result = handle_ungrouped_query(
                    new_where_clause, new_params, limit, offset, db, filters_applied, join_matches=join_new_matches
                )
                new_results = result['data']
                new_total_count = result['metadata']['total_matching_rows']
            else:
                # Grouped query - get raw results for potential merging
                result = handle_grouped_query(
                    new_where_clause, new_params, group_by, min_balls, max_balls,
                    min_runs, max_runs, limit, offset, db, filters_applied,
                    has_batter_filters, show_summary_rows, join_matches=join_new_matches,
                    min_wickets=min_wickets, max_wickets=max_wickets,
                )
                new_results = result['data']
                new_total_count = result['metadata']['total_groups']
                new_total_innings = result.get("metadata", {}).get("total_innings_in_query", new_total_innings)
            
            data_sources.append(f"delivery_details ({new_start.year}-{new_end.year})")
        
        # =====================================================================
        # QUERY LEGACY TABLE (deliveries) - Pre-2015
        # =====================================================================
        legacy_results = []
        legacy_total_count = 0
        legacy_total_balls = 0
        legacy_total_innings = 0
        
        if routing['use_legacy']:
            legacy_date_range = routing['legacy_date_range']
            legacy_start, legacy_end = legacy_date_range if legacy_date_range else (start_date or date(2005, 1, 1), date(2014, 12, 31))
            
            legacy_params = {
                "limit": min(limit, 10000),
                "offset": offset
            }
            
            legacy_where_clause, legacy_params = build_legacy_where_clause(
                venue=venue,
                start_date=legacy_start,
                end_date=legacy_end,
                leagues=leagues,
                teams=teams,
                batting_teams=batting_teams,
                bowling_teams=bowling_teams,
                players=players,
                batters=batters,
                bowlers=bowlers,
                bowl_style=bowl_style,
                bowl_kind=bowl_kind,
                crease_combo=crease_combo,
                dismissal=dismissal,
                innings=innings,
                over_min=over_min,
                over_max=over_max,
                match_outcome=match_outcome,
                is_chase=is_chase,
                chase_outcome=chase_outcome,
                toss_decision=toss_decision,
                include_international=include_international,
                top_teams=top_teams,
                group_by=group_by,
                base_params=legacy_params,
                db=db
            )
            
            legacy_total_balls = get_legacy_total_balls(legacy_where_clause, legacy_params, db) or 0
            legacy_count_params = {k: v for k, v in legacy_params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs', 'min_wickets', 'max_wickets']}
            legacy_total_innings_query = f"""
                SELECT COUNT(DISTINCT (d.match_id, d.innings))
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                LEFT JOIN players p ON p.name = d.bowler
                {legacy_where_clause}
            """
            legacy_total_innings = db.execute(text(legacy_total_innings_query), legacy_count_params).scalar() or 0
            
            if not group_by or len(group_by) == 0:
                # Ungrouped query
                legacy_results, legacy_total_count = query_legacy_ungrouped(
                    legacy_where_clause, legacy_params, limit, offset, db
                )
            else:
                # Grouped query
                legacy_results, legacy_total_balls = query_legacy_grouped(
                    legacy_where_clause, legacy_params, group_by, db, has_batter_filters
                )
                legacy_total_count = len(legacy_results)
                legacy_total_innings = sum(int(r.get("innings_count") or 0) for r in legacy_results)
            
            data_sources.append(f"deliveries ({legacy_start.year}-{legacy_end.year})")
        
        # =====================================================================
        # MERGE RESULTS
        # =====================================================================
        total_balls = new_total_balls + legacy_total_balls
        total_innings_in_query = 0
        
        if routing['use_new'] and routing['use_legacy']:
            # Load player aliases for merging
            player_aliases_map = load_player_aliases_for_merge(db)
            
            if not group_by or len(group_by) == 0:
                # Merge ungrouped results
                merged_data = merge_ungrouped_results(new_results, legacy_results, player_aliases_map)
                total_innings_in_query = new_total_innings + legacy_total_innings
                # Apply pagination to merged results
                merged_data = merged_data[offset:offset + limit]
                total_count = new_total_count + legacy_total_count
            else:
                # Merge grouped results
                merged_data = merge_grouped_results(
                    new_results, legacy_results, group_by, player_aliases_map, total_balls
                )
                # Apply min/max filters after merge
                if min_balls is not None:
                    merged_data = [r for r in merged_data if r.get('balls', 0) >= min_balls]
                if max_balls is not None:
                    merged_data = [r for r in merged_data if r.get('balls', 0) <= max_balls]
                if min_runs is not None:
                    merged_data = [r for r in merged_data if r.get('runs', 0) >= min_runs]
                if max_runs is not None:
                    merged_data = [r for r in merged_data if r.get('runs', 0) <= max_runs]
                total_innings_in_query = sum(int(r.get("innings_count") or 0) for r in merged_data)
                total_count = len(merged_data)
                # Apply pagination
                merged_data = merged_data[offset:offset + limit]
        else:
            # Single source - no merge needed
            merged_data = new_results if routing['use_new'] else legacy_results
            total_count = new_total_count if routing['use_new'] else legacy_total_count
            if routing['use_legacy'] and not routing['use_new']:
                player_aliases_map = load_player_aliases_for_merge(db)
                for row in merged_data:
                    if row.get('batter'):
                        row['batter'] = normalize_player_name_for_merge(row['batter'], player_aliases_map)
                    if row.get('bowler'):
                        row['bowler'] = normalize_player_name_for_merge(row['bowler'], player_aliases_map)
            if not group_by or len(group_by) == 0:
                total_innings_in_query = new_total_innings if routing['use_new'] else legacy_total_innings
            elif routing['use_new']:
                total_innings_in_query = result.get("metadata", {}).get("total_innings_in_query", 0)
            else:
                total_innings_in_query = sum(int(r.get("innings_count") or 0) for r in legacy_results)
        
        # =====================================================================
        # BUILD RESPONSE
        # =====================================================================
        if not group_by or len(group_by) == 0:
            # Ungrouped response
            data_source_label = (
                "delivery_details+deliveries"
                if len(data_sources) > 1
                else ("delivery_details" if routing['use_new'] else "deliveries")
            )
            return {
                "data": merged_data,
                "metadata": {
                    "total_matching_rows": total_count,
                    "total_innings_in_query": total_innings_in_query,
                    "returned_rows": len(merged_data),
                    "limit": limit,
                    "offset": offset,
                    "has_more": total_count > (offset + len(merged_data)),
                    "filters_applied": filters_applied,
                    "data_sources": data_sources,
                    "query_mode_used": query_mode,
                    "data_source": data_source_label,
                    "warnings": delivery_warnings,
                    "note": "Individual delivery records" + (" (merged from multiple sources)" if len(data_sources) > 1 else "")
                }
            }
        else:
            # Grouped response
            # Generate summary data if requested (only from new table for now)
            summary_data = None
            percentages = None
            if show_summary_rows and len(group_by) >= 1 and routing['use_new'] and 'result' in dir():
                summary_data = result.get('summary_data')
                percentages = result.get('percentages')

            data_source_label = (
                "delivery_details+deliveries"
                if len(data_sources) > 1
                else ("delivery_details" if routing['use_new'] else "deliveries")
            )
            
            return {
                "data": merged_data,
                "summary_data": summary_data,
                "percentages": percentages,
                "metadata": {
                    "total_groups": total_count,
                    "total_innings_in_query": total_innings_in_query,
                    "returned_groups": len(merged_data),
                    "total_balls_in_query": total_balls,
                    "limit": limit,
                    "offset": offset,
                    "has_more": total_count > (offset + len(merged_data)),
                    "grouped_by": group_by,
                    "filters_applied": filters_applied,
                    "has_summaries": summary_data is not None,
                    "data_sources": data_sources,
                    "query_mode_used": query_mode,
                    "data_source": data_source_label,
                    "warnings": delivery_warnings,
                    "note": "Grouped data with cricket aggregations" + (" (merged from multiple sources)" if len(data_sources) > 1 else "")
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in query_deliveries_service: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


def build_where_clause(
    venue, start_date, end_date, leagues, teams, batting_teams, bowling_teams,
    players, batters, bowlers, bat_hand, bowl_style, bowl_kind, crease_combo,
    line, length, shot, control, wagon_zone, dismissal, innings, over_min, over_max,
    match_outcome, is_chase, chase_outcome, toss_decision,
    include_international, top_teams, group_by, base_params, db=None
):
    """Build dynamic WHERE clause for delivery_details table."""
    conditions = ["1=1"]
    params = base_params.copy()
    
    # Venue filter (ground in delivery_details)
    if venue:
        params["venue_aliases"] = get_venue_aliases(venue)
        conditions.append("dd.ground = ANY(:venue_aliases)")
    
    # Date filters (using year column for efficiency, can add date parsing if needed)
    if start_date:
        conditions.append("dd.year >= :start_year")
        params["start_year"] = start_date.year
    
    if end_date:
        conditions.append("dd.year <= :end_year")
        params["end_year"] = end_date.year
    
    # Competition filters (leagues and/or international)
    # These should be OR'd together - a delivery can be from a league OR international
    competition_conditions = []
    
    if leagues:
        expanded_leagues = expand_league_abbreviations(leagues)
        competition_conditions.append("dd.competition = ANY(:leagues)")
        params["leagues"] = expanded_leagues
    
    if include_international:
        if top_teams:
            top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            competition_conditions.append("(dd.competition = 'T20I' AND dd.team_bat = ANY(:top_teams) AND dd.team_bowl = ANY(:top_teams))")
            params["top_teams"] = top_team_list
        else:
            competition_conditions.append("dd.competition = 'T20I'")
    
    # Combine competition conditions with OR
    if competition_conditions:
        conditions.append("(" + " OR ".join(competition_conditions) + ")")
    
    # Team filters
    team_conditions = []
    
    if teams:
        team_variations = []
        for team in teams:
            team_variations.extend(get_all_team_name_variations(team))
        team_conditions.append("(dd.team_bat = ANY(:teams) OR dd.team_bowl = ANY(:teams))")
        params["teams"] = team_variations
    
    if batting_teams:
        batting_variations = []
        for team in batting_teams:
            batting_variations.extend(get_all_team_name_variations(team))
        team_conditions.append("dd.team_bat = ANY(:batting_teams)")
        params["batting_teams"] = batting_variations
    
    if bowling_teams:
        bowling_variations = []
        for team in bowling_teams:
            bowling_variations.extend(get_all_team_name_variations(team))
        team_conditions.append("dd.team_bowl = ANY(:bowling_teams)")
        params["bowling_teams"] = bowling_variations
    
    if team_conditions:
        conditions.append("(" + " AND ".join(team_conditions) + ")")
    
    # Player filters - resolve aliases so legacy names (e.g. "YS Samra")
    # also match delivery_details full names (e.g. "Yuvraj Samra")
    if players:
        player_variants = _expand_player_names(players, db) if db else players
        conditions.append("(dd.bat = ANY(:players) OR dd.bowl = ANY(:players))")
        params["players"] = player_variants

    if batters:
        batter_variants = _expand_player_names(batters, db) if db else batters
        conditions.append("dd.bat = ANY(:batters)")
        params["batters"] = batter_variants

    if bowlers:
        bowler_variants = _expand_player_names(bowlers, db) if db else bowlers
        conditions.append("dd.bowl = ANY(:bowlers)")
        params["bowlers"] = bowler_variants
    
    # Batter/Bowler attribute filters
    if bat_hand:
        conditions.append("dd.bat_hand = :bat_hand")
        params["bat_hand"] = bat_hand
    
    if bowl_style:
        conditions.append("dd.bowl_style = ANY(:bowl_style)")
        params["bowl_style"] = bowl_style
    
    if bowl_kind:
        kind_conditions = ["dd.bowl_kind = ANY(:bowl_kind)"]
        # Fallback: when bowl_kind is NULL, infer from bowl_style
        fallback_styles = set()
        for k in bowl_kind:
            if "spin" in k.lower():
                fallback_styles.update(SPIN_STYLES)
            elif "pace" in k.lower() or "fast" in k.lower():
                fallback_styles.update(PACE_STYLES)
        if fallback_styles:
            kind_conditions.append(
                "(dd.bowl_kind IS NULL AND dd.bowl_style = ANY(:bowl_kind_fallback_styles))"
            )
            params["bowl_kind_fallback_styles"] = sorted(fallback_styles)
        conditions.append("(" + " OR ".join(kind_conditions) + ")")
        params["bowl_kind"] = bowl_kind
    
    # Crease combo filter - expand LHB_RHB to include RHB_LHB (mixed combos are equivalent)
    if crease_combo:
        expanded_crease = []
        for combo in crease_combo:
            expanded_crease.append(combo)
            if combo == "LHB_RHB":
                expanded_crease.append("RHB_LHB")
            elif combo == "RHB_LHB":
                expanded_crease.append("LHB_RHB")
        conditions.append("dd.crease_combo = ANY(:crease_combo)")
        params["crease_combo"] = list(set(expanded_crease))
    
    # Delivery detail filters
    if line:
        conditions.append("dd.line = ANY(:line)")
        params["line"] = line
    
    if length:
        conditions.append("dd.length = ANY(:length)")
        params["length"] = length
    
    if shot:
        conditions.append("dd.shot = ANY(:shot)")
        params["shot"] = shot
    
    if control is not None:
        conditions.append("dd.control = :control")
        params["control"] = control
    
    if wagon_zone:
        conditions.append("dd.wagon_zone = ANY(:wagon_zone)")
        params["wagon_zone"] = wagon_zone

    if dismissal:
        conditions.append("dd.dismissal = ANY(:dismissal)")
        params["dismissal"] = dismissal

    match_outcome_sql = get_match_outcome_sql(
        batting_team_expr="dd.team_bat",
        bowling_team_expr="dd.team_bowl",
        winner_expr="m.winner",
        outcome_json_expr="m.outcome",
    )
    chase_outcome_sql = get_chase_outcome_sql("dd.inns", match_outcome_sql)

    if match_outcome:
        conditions.append(f"{match_outcome_sql} = ANY(:match_outcome)")
        params["match_outcome"] = match_outcome

    if is_chase is True:
        conditions.append("dd.inns = 2")
    elif is_chase is False:
        conditions.append("dd.inns != 2")

    if chase_outcome:
        conditions.append("dd.inns = 2")
        conditions.append(f"{chase_outcome_sql} = ANY(:chase_outcome)")
        params["chase_outcome"] = chase_outcome

    if toss_decision:
        conditions.append("LOWER(COALESCE(m.toss_decision, '')) = ANY(:toss_decision)")
        params["toss_decision"] = toss_decision

    # Grouping by dismissal should only include wicket deliveries
    if group_by and "dismissal" in group_by:
        conditions.append("dd.dismissal IS NOT NULL AND dd.dismissal != ''")
    
    # Match context filters
    if innings:
        conditions.append("dd.inns = :innings")
        params["innings"] = innings
    
    if over_min is not None:
        conditions.append("dd.over >= :over_min")
        params["over_min"] = over_min
    
    if over_max is not None:
        conditions.append("dd.over <= :over_max")
        params["over_max"] = over_max
    
    where_clause = "WHERE " + " AND ".join(conditions)
    return where_clause, params


from utils.league_utils import expand_league_abbreviations


def get_all_team_name_variations(team_name):
    """Get all possible name variations for a team."""
    reverse_mapping = {}
    for full_name, abbrev in teams_mapping.items():
        if abbrev not in reverse_mapping:
            reverse_mapping[abbrev] = []
        reverse_mapping[abbrev].append(full_name)
    
    if team_name in reverse_mapping:
        return reverse_mapping[team_name] + [team_name]
    
    abbrev = teams_mapping.get(team_name)
    if abbrev and abbrev in reverse_mapping:
        return reverse_mapping[abbrev] + [team_name]
    
    return [team_name]


def handle_ungrouped_query(where_clause, params, limit, offset, db, filters, join_matches=False):
    """Return individual delivery records from delivery_details."""
    join_clause = "JOIN matches m ON m.id = dd.p_match" if join_matches else ""
    
    main_query = f"""
        SELECT 
            dd.p_match as match_id,
            dd.inns as innings,
            dd.over,
            dd.ball,
            dd.bat as batter,
            dd.bowl as bowler,
            dd.batruns as runs_off_bat,
            dd.score as total_runs,
            dd.team_bat as batting_team,
            dd.team_bowl as bowling_team,
            dd.bat_hand,
            dd.bowl_style,
            dd.bowl_kind,
            LOWER(CASE WHEN dd.crease_combo = 'RHB_LHB' THEN 'LHB_RHB' ELSE dd.crease_combo END) as crease_combo,
            dd.line,
            dd.length,
            dd.shot,
            dd.control,
            dd.wagon_x,
            dd.wagon_y,
            dd.wagon_zone,
            dd.dismissal as wicket_type,
            dd.ground as venue,
            dd.match_date as date,
            dd.competition,
            dd.year,
            dd.outcome
        FROM delivery_details dd
        {join_clause}
        {where_clause}
        ORDER BY dd.year DESC, dd.p_match, dd.inns, dd.over, dd.ball
        LIMIT :limit
        OFFSET :offset
    """
    
    result = db.execute(text(main_query), params).fetchall()
    
    formatted_results = []
    for row in result:
        formatted_results.append({
            "match_id": row[0],
            "innings": row[1],
            "over": row[2],
            "ball": row[3],
            "batter": row[4],
            "bowler": row[5],
            "runs_off_bat": row[6],
            "total_runs": row[7],
            "batting_team": row[8],
            "bowling_team": row[9],
            "bat_hand": row[10],
            "bowl_style": row[11],
            "bowl_kind": row[12],
            "crease_combo": row[13],
            "line": row[14],
            "length": row[15],
            "shot": row[16],
            "control": row[17],
            "wagon_x": row[18],
            "wagon_y": row[19],
            "wagon_zone": row[20],
            "wicket_type": row[21],
            "venue": row[22],
            "date": row[23],
            "competition": row[24],
            "year": row[25],
            "outcome": row[26]
        })
    
    # Count total
    count_query = f"""
        SELECT COUNT(*) FROM delivery_details dd
        {join_clause}
        {where_clause}
    """
    count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
    total_count = db.execute(text(count_query), count_params).scalar()
    
    return {
        "data": formatted_results,
        "metadata": {
            "total_matching_rows": total_count,
            "returned_rows": len(formatted_results),
            "limit": limit,
            "offset": offset,
            "has_more": total_count > (offset + len(formatted_results)),
            "filters_applied": filters,
            "note": "Individual delivery records from delivery_details"
        }
    }


def get_grouping_columns_map():
    """Map user-friendly group_by values to delivery_details column names."""
    match_outcome_sql = get_match_outcome_sql(
        batting_team_expr="dd.team_bat",
        bowling_team_expr="dd.team_bowl",
        winner_expr="m.winner",
        outcome_json_expr="m.outcome",
    )
    chase_outcome_sql = get_chase_outcome_sql("dd.inns", match_outcome_sql)

    return {
        # Location
        "venue": "dd.ground",
        "country": "dd.country",
        
        # Match identifiers
        "match_id": "dd.p_match",
        "competition": "dd.competition",
        "year": "dd.year",
        
        # Teams
        "batting_team": "dd.team_bat",
        "bowling_team": "dd.team_bowl",
        
        # Players
        "batter": "dd.bat",
        "bowler": "dd.bowl",
        # delivery_details.non_striker is mostly stored in legacy short-form
        # ("V Kohli") while dd.bat is canonical. Use player_aliases to project
        # to canonical, so non_striker / partnership groupings collapse the
        # name variants. pa_ns/pa_bat joins are added by handle_grouped_query.
        "non_striker": "COALESCE(pa_ns.alias_name, dd.non_striker)",
        # Bidirectional pair: (Kohli, ABD) and (ABD, Kohli) collapse to one row.
        "partnership": (
            "(LEAST("
            "COALESCE(pa_bat.alias_name, dd.bat, ''), "
            "COALESCE(pa_ns.alias_name, dd.non_striker, '')"
            ") || ' & ' || GREATEST("
            "COALESCE(pa_bat.alias_name, dd.bat, ''), "
            "COALESCE(pa_ns.alias_name, dd.non_striker, '')"
            "))"
        ),
        # Wired by the bat_pos CTE in handle_grouped_query.
        "batting_position": "bp.pos",

        # Innings/Phase
        "innings": "dd.inns",
        "phase": "CASE WHEN dd.over < 6 THEN 'powerplay' WHEN dd.over < 15 THEN 'middle' ELSE 'death' END",
        
        # Batter attributes
        "bat_hand": "dd.bat_hand",
        "striker_batter_type": "dd.bat_hand",  # Backward-compatible alias
        "non_striker_batter_type": "NULL",  # Not available in delivery_details
        # Normalize crease_combo: RHB_LHB and LHB_RHB are both "mixed" - normalize to lowercase lhb_rhb
        "crease_combo": "LOWER(CASE WHEN dd.crease_combo = 'RHB_LHB' THEN 'LHB_RHB' ELSE dd.crease_combo END)",
        "ball_direction": "NULL",  # Not available in delivery_details
        
        # Bowler attributes
        "bowl_style": "dd.bowl_style",
        "bowl_kind": "dd.bowl_kind",
        
        # Delivery details
        "line": "dd.line",
        "length": "dd.length",
        "shot": "dd.shot",
        "control": "dd.control",
        "wagon_zone": "dd.wagon_zone",
        "dismissal": "dd.dismissal",
        # Match context
        "match_outcome": match_outcome_sql,
        "chase_outcome": chase_outcome_sql,
        "toss_decision": "LOWER(COALESCE(m.toss_decision, ''))",
        "toss_match_outcome": get_toss_match_outcome_sql("m.toss_winner", "m.winner", "m.outcome"),
    }


def handle_grouped_query(
    where_clause, params, group_by, min_balls, max_balls,
    min_runs, max_runs, limit, offset, db, filters_applied=None,
    has_batter_filters=False, show_summary_rows=False, join_matches=False,
    min_wickets=None, max_wickets=None,
):
    """Return aggregated cricket statistics grouped by specified columns.

    Single-statement plan with two scans of delivery_details:
      Stage 1 (CTE all_groups): cheap aggregates per group (balls, innings,
        runs, wickets) — needed to evaluate HAVING and the metadata window
        functions (universe_balls, parent_balls, total_groups, total_innings).
      Stage 2 (final SELECT): rich aggregates (dots, boundaries, fours,
        sixes, control_pct) computed only for the LIMIT-survivor groups.
    Replaces five separate queries (total_balls + parent_totals + main agg +
    count + innings_total) with one combined CTE plus a cheap fallback for
    the empty-result case.
    """

    grouping_columns = get_grouping_columns_map()
    join_clause = "JOIN matches m ON m.id = dd.p_match" if join_matches else ""

    invalid_columns = [col for col in group_by if col not in grouping_columns]
    if invalid_columns:
        raise HTTPException(status_code=400, detail=f"Invalid group_by columns: {invalid_columns}")

    # batting_position needs an aux CTE that ranks batters by first-ball order
    # within each innings. Compute it once over the full table and LEFT JOIN.
    needs_bat_pos = "batting_position" in group_by
    bat_pos_cte = ""
    bat_pos_join = ""
    if needs_bat_pos:
        bat_pos_cte = """bat_pos AS (
            SELECT p_match, inns, bat,
                   DENSE_RANK() OVER (PARTITION BY p_match, inns ORDER BY MIN(over*6 + ball)) AS pos
            FROM delivery_details
            WHERE bat IS NOT NULL
            GROUP BY p_match, inns, bat
        ),
        """
        bat_pos_join = "LEFT JOIN bat_pos bp ON bp.p_match = dd.p_match AND bp.inns = dd.inns AND bp.bat = dd.bat"

    # Partnership / non_striker grouping: player_aliases JOIN canonicalizes
    # the legacy-form non_striker/bat values to alias_name (the canonical
    # form), so name variants for the same player collapse to one row.
    needs_partner_canon = ("partnership" in group_by) or ("non_striker" in group_by)
    pa_join = ""
    if needs_partner_canon:
        pa_join = (
            "LEFT JOIN player_aliases pa_bat ON pa_bat.player_name = dd.bat "
            "LEFT JOIN player_aliases pa_ns  ON pa_ns.player_name = dd.non_striker"
        )

    group_columns = [grouping_columns[col] for col in group_by]
    select_group_clause = ", ".join(f"{db_col} as {col}" for col, db_col in zip(group_by, group_columns))
    group_by_clause = ", ".join(group_columns)

    batter_grouping = "batter" in group_by
    use_runs_off_bat_only = batter_grouping or has_batter_filters
    runs_calculation = "SUM(dd.batruns)" if use_runs_off_bat_only else "SUM(dd.score)"

    # HAVING in the new pattern is a WHERE on the aggregated CTE; predicates
    # reference the aggregated column aliases (balls/runs/wickets) rather
    # than re-issuing the SUM/COUNT.
    having_conditions = []
    if min_balls is not None:
        having_conditions.append("balls >= :min_balls")
        params["min_balls"] = min_balls
    if max_balls is not None:
        having_conditions.append("balls <= :max_balls")
        params["max_balls"] = max_balls
    if min_runs is not None:
        having_conditions.append("runs >= :min_runs")
        params["min_runs"] = min_runs
    if max_runs is not None:
        having_conditions.append("runs <= :max_runs")
        params["max_runs"] = max_runs
    if min_wickets is not None:
        having_conditions.append("wickets >= :min_wickets")
        params["min_wickets"] = min_wickets
    if max_wickets is not None:
        having_conditions.append("wickets <= :max_wickets")
        params["max_wickets"] = max_wickets

    having_predicate = " AND ".join(having_conditions) if having_conditions else "TRUE"
    having_where_clause = f"WHERE {having_predicate}" if having_conditions else ""

    # Multi-level grouping: percent_balls is shown relative to the first
    # group_by column's total. Single-level: relative to the universe.
    if len(group_by) > 1:
        parent_partition_sql = f"SUM(g.balls) OVER (PARTITION BY g.{group_by[0]})"
    else:
        parent_partition_sql = "NULL::bigint"

    # Stage 2 join: compute grouping expressions once in stage2_source (with
    # the same joins/filters as Stage 1), then match against qualifying groups.
    # Use IS NOT DISTINCT FROM so NULL-group keys still join correctly.
    stage2_join_conditions = " AND ".join(
        f"s.{col} IS NOT DISTINCT FROM q.{col}"
        for col in group_by
    )

    final_select_groups = ", ".join(f"q.{col} as {col}" for col in group_by)
    final_group_by_carry = ", ".join(f"q.{col}" for col in group_by)

    combined_query = f"""
        WITH {bat_pos_cte}all_groups AS (
            SELECT
                {select_group_clause},
                COUNT(*) as balls,
                COUNT(DISTINCT (dd.p_match, dd.inns)) as innings_count,
                {runs_calculation} as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets
            FROM delivery_details dd
            {bat_pos_join}
            {pa_join}
            {join_clause}
            {where_clause}
            GROUP BY {group_by_clause}
        ),
        with_totals AS (
            SELECT g.*,
                SUM(g.balls) OVER () as universe_balls,
                {parent_partition_sql} as parent_balls
            FROM all_groups g
        ),
        qualifying AS (
            SELECT *,
                COUNT(*) OVER () as total_groups_after_having,
                SUM(innings_count) OVER () as total_innings_after_having
            FROM with_totals
            {having_where_clause}
            ORDER BY balls DESC
            LIMIT :limit OFFSET :offset
        ),
        stage2_source AS (
            SELECT
                {select_group_clause},
                dd.batruns,
                dd.wide,
                dd.noball,
                dd.control
            FROM delivery_details dd
            {bat_pos_join}
            {pa_join}
            {join_clause}
            {where_clause}
        )
        SELECT
            {final_select_groups},
            q.balls, q.innings_count, q.runs, q.wickets,
            q.universe_balls, q.parent_balls,
            q.total_groups_after_having, q.total_innings_after_having,
            SUM(CASE WHEN s.batruns = 0 AND s.wide = 0 AND s.noball = 0 THEN 1 ELSE 0 END) as dots,
            SUM(CASE WHEN s.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
            SUM(CASE WHEN s.batruns = 4 THEN 1 ELSE 0 END) as fours,
            SUM(CASE WHEN s.batruns = 6 THEN 1 ELSE 0 END) as sixes,
            CASE WHEN q.wickets > 0 THEN CAST(q.runs AS DECIMAL) / q.wickets ELSE NULL END as average,
            CASE WHEN q.balls > 0 THEN (CAST(q.runs AS DECIMAL) * 100.0) / q.balls ELSE 0 END as strike_rate,
            CASE WHEN q.wickets > 0 THEN CAST(q.balls AS DECIMAL) / q.wickets ELSE NULL END as balls_per_dismissal,
            CASE WHEN q.balls > 0
                THEN (CAST(SUM(CASE WHEN s.batruns = 0 AND s.wide = 0 AND s.noball = 0 THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / q.balls
                ELSE 0 END as dot_percentage,
            CASE WHEN q.balls > 0
                THEN (CAST(SUM(CASE WHEN s.batruns IN (4, 6) THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / q.balls
                ELSE 0 END as boundary_percentage,
            CASE WHEN SUM(CASE WHEN s.control IS NOT NULL THEN 1 ELSE 0 END) > 0
                THEN (CAST(SUM(CASE WHEN s.control = 1 THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) /
                      SUM(CASE WHEN s.control IS NOT NULL THEN 1 ELSE 0 END)
                ELSE NULL END as control_percentage
        FROM qualifying q
        JOIN stage2_source s ON {stage2_join_conditions}
        GROUP BY {final_group_by_carry}, q.balls, q.innings_count, q.runs, q.wickets,
                 q.universe_balls, q.parent_balls,
                 q.total_groups_after_having, q.total_innings_after_having
        ORDER BY q.balls DESC
    """

    result = db.execute(text(combined_query), params).fetchall()

    universe_balls = 0
    total_groups = 0
    total_innings_in_query = 0
    formatted_results = []
    n = len(group_by)

    for row in result:
        row_dict = {col: row[i] for i, col in enumerate(group_by)}
        balls = row[n]
        innings_count = row[n + 1]
        runs = row[n + 2]
        wickets = row[n + 3]
        universe_balls = row[n + 4] or 0
        parent_balls = row[n + 5]
        total_groups = row[n + 6] or 0
        total_innings_in_query = row[n + 7] or 0
        dots = row[n + 8]
        boundaries = row[n + 9]
        fours = row[n + 10]
        sixes = row[n + 11]
        average = row[n + 12]
        strike_rate = row[n + 13]
        balls_per_dismissal = row[n + 14]
        dot_percentage = row[n + 15]
        boundary_percentage = row[n + 16]
        control_percentage = row[n + 17]

        if len(group_by) > 1 and parent_balls is not None and parent_balls > 0:
            percent_balls = round((balls / parent_balls) * 100, 2)
        elif universe_balls > 0:
            percent_balls = round((balls / universe_balls) * 100, 2)
        else:
            percent_balls = 0

        row_dict.update({
            "balls": balls,
            "innings_count": innings_count,
            "runs": runs,
            "wickets": wickets,
            "dots": dots,
            "boundaries": boundaries,
            "fours": fours,
            "sixes": sixes,
            "average": float(average) if average is not None else None,
            "strike_rate": float(strike_rate) if strike_rate is not None else 0,
            "balls_per_dismissal": float(balls_per_dismissal) if balls_per_dismissal is not None else None,
            "dot_percentage": float(dot_percentage) if dot_percentage is not None else 0,
            "boundary_percentage": float(boundary_percentage) if boundary_percentage is not None else 0,
            "control_percentage": float(control_percentage) if control_percentage is not None else None,
            "percent_balls": percent_balls,
        })
        formatted_results.append(row_dict)

    # Empty Stage 2 means no rows passed HAVING (or LIMIT/OFFSET past the
    # end). Window-function metadata is unavailable in that case — fall back
    # to one cheap aggregate over the same all_groups CTE so the response
    # still carries accurate totals.
    if not formatted_results:
        fallback_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
        fallback_query = f"""
            WITH {bat_pos_cte}all_groups AS (
                SELECT
                    {select_group_clause},
                    COUNT(*) as balls,
                    COUNT(DISTINCT (dd.p_match, dd.inns)) as innings_count,
                    {runs_calculation} as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets
                FROM delivery_details dd
                {bat_pos_join}
                {pa_join}
                {join_clause}
                {where_clause}
                GROUP BY {group_by_clause}
            )
            SELECT
                COALESCE(SUM(balls), 0) as universe_balls,
                COUNT(*) FILTER (WHERE {having_predicate}) as total_groups,
                COALESCE(SUM(innings_count) FILTER (WHERE {having_predicate}), 0) as total_innings
            FROM all_groups
        """
        fb_row = db.execute(text(fallback_query), fallback_params).fetchone()
        if fb_row:
            universe_balls = fb_row[0] or 0
            total_groups = fb_row[1] or 0
            total_innings_in_query = fb_row[2] or 0

    summary_data = None
    percentages = None
    if show_summary_rows and len(group_by) >= 1:
        summary_data, percentages = generate_summary_data(
            where_clause, params, group_by, runs_calculation, db, universe_balls, join_matches=join_matches
        )

    return {
        "data": formatted_results,
        "summary_data": summary_data,
        "percentages": percentages,
        "metadata": {
            "total_groups": total_groups,
            "total_innings_in_query": total_innings_in_query,
            "returned_groups": len(formatted_results),
            "total_balls_in_query": universe_balls,
            "limit": limit,
            "offset": offset,
            "has_more": total_groups > (offset + len(formatted_results)),
            "grouped_by": group_by,
            "filters_applied": filters_applied,
            "has_summaries": summary_data is not None,
            "note": "Grouped data from delivery_details with cricket aggregations"
        }
    }


def generate_summary_data(where_clause, params, group_by, runs_calculation, db, total_balls, join_matches=False):
    """Generate hierarchical summary data for grouped queries with percent_balls."""
    try:
        grouping_columns = get_grouping_columns_map()
        join_clause = "JOIN matches m ON m.id = dd.p_match" if join_matches else ""
        summaries = {}
        percentages = {}
        
        # Generate summaries for each level of grouping
        for level in range(1, len(group_by) + 1):
            summary_group_by = group_by[:level]
            
            if level == 1:
                summary_key = f"{summary_group_by[0]}_summaries"
            else:
                summary_key = f"level_{level}_summaries"
            
            summary_columns = []
            summary_group_clause = []
            
            for col in summary_group_by:
                db_column = grouping_columns[col]
                summary_group_clause.append(db_column)
                summary_columns.append(f"{db_column} as {col}")
            
            summary_group_by_clause = ", ".join(summary_group_clause)
            summary_select_clause = ", ".join(summary_columns)
            summary_needs_bat_pos = "batting_position" in summary_group_by
            summary_bat_pos_cte = ""
            summary_bat_pos_join = ""
            if summary_needs_bat_pos:
                summary_bat_pos_cte = """WITH bat_pos AS (
                    SELECT p_match, inns, bat,
                           DENSE_RANK() OVER (PARTITION BY p_match, inns ORDER BY MIN(over*6 + ball)) AS pos
                    FROM delivery_details
                    WHERE bat IS NOT NULL
                    GROUP BY p_match, inns, bat
                )
                """
                summary_bat_pos_join = "LEFT JOIN bat_pos bp ON bp.p_match = dd.p_match AND bp.inns = dd.inns AND bp.bat = dd.bat"

            summary_needs_partner_canon = ("partnership" in summary_group_by) or ("non_striker" in summary_group_by)
            summary_pa_join = ""
            if summary_needs_partner_canon:
                summary_pa_join = (
                    "LEFT JOIN player_aliases pa_bat ON pa_bat.player_name = dd.bat "
                    "LEFT JOIN player_aliases pa_ns  ON pa_ns.player_name = dd.non_striker"
                )

            summary_query = f"""
                {summary_bat_pos_cte}
                SELECT 
                    {summary_select_clause},
                    COUNT(*) as total_balls,
                    {runs_calculation} as total_runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as total_wickets,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as total_dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as total_boundaries,
                    CASE WHEN COUNT(*) > 0 
                        THEN (CAST({runs_calculation} AS DECIMAL) * 100.0) / COUNT(*)
                        ELSE 0 END as strike_rate
                FROM delivery_details dd
                {summary_bat_pos_join}
                {summary_pa_join}
                {join_clause}
                {where_clause}
                GROUP BY {summary_group_by_clause}
                ORDER BY total_balls DESC
            """
            
            summary_params = {k: v for k, v in params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs', 'min_wickets', 'max_wickets']}
            summary_result = db.execute(text(summary_query), summary_params).fetchall()
            
            formatted_summaries = []
            level_percentages = {}
            
            for row in summary_result:
                summary_dict = {}
                for i, col in enumerate(summary_group_by):
                    summary_dict[col] = row[i]
                
                stats_start = len(summary_group_by)
                balls = row[stats_start]
                # Summary rows show percent of total query
                percent_balls = round((balls / total_balls) * 100, 2) if total_balls > 0 else 0
                
                summary_dict.update({
                    "total_balls": balls,
                    "total_runs": row[stats_start + 1],
                    "total_wickets": row[stats_start + 2],
                    "total_dots": row[stats_start + 3],
                    "total_boundaries": row[stats_start + 4],
                    "strike_rate": float(row[stats_start + 5]) if row[stats_start + 5] is not None else 0,
                    "percent_balls": percent_balls
                })
                formatted_summaries.append(summary_dict)
                
                # Build key for percentage lookup (level 1 only)
                if level == 1:
                    key = str(row[0])
                    level_percentages[key] = {"percent": percent_balls, "balls": balls}
            
            summaries[summary_key] = formatted_summaries
            
            # Store first-level data for easy lookup
            if level == 1:
                percentages = level_percentages
        
        return summaries, percentages
        
    except Exception as e:
        logger.error(f"Error generating summary data: {str(e)}")
        return None, None
