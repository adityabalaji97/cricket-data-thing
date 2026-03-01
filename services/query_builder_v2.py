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
    'bat_hand', 'bowl_style', 'bowl_kind'
}

# Columns available in both tables (can be queried across full date range)
COMMON_COLUMNS = {
    'venue', 'competition', 'year', 'batting_team', 'bowling_team',
    'batter', 'bowler', 'innings', 'phase', 'match_id', 'country'
}

# Columns that exist in both but have different coverage
# crease_combo: ~91% in delivery_details, lower in deliveries
PARTIAL_COLUMNS = {'crease_combo'}


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


# =============================================================================
# LEGACY TABLE (deliveries) COLUMN MAPPING
# =============================================================================

def get_legacy_grouping_columns_map():
    """Map user-friendly group_by values to deliveries table column names."""
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
        
        # Innings/Phase
        "innings": "d.innings",
        "phase": "CASE WHEN d.over < 6 THEN 'powerplay' WHEN d.over < 15 THEN 'middle' ELSE 'death' END",
        
        # Batter attributes (partial coverage in legacy)
        "bat_hand": "NULL",  # Not available
        # Normalize crease_combo: swap RHB_LHB -> LHB_RHB and lowercase
        "crease_combo": "LOWER(CASE WHEN d.crease_combo = 'RHB_LHB' THEN 'LHB_RHB' ELSE d.crease_combo END)",
        
        # Bowler attributes
        "bowl_style": "NULL",  # Not available
        "bowl_kind": "NULL",   # Not available
        
        # Delivery details - NOT available in legacy, return NULL
        "line": "NULL",
        "length": "NULL",
        "shot": "NULL",
        "control": "NULL",
        "wagon_zone": "NULL",
    }


def build_legacy_where_clause(
    venue, start_date, end_date, leagues, teams, batting_teams, bowling_teams,
    players, batters, bowlers, crease_combo, innings, over_min, over_max,
    include_international, top_teams, base_params, db
):
    """Build dynamic WHERE clause for legacy deliveries table."""
    conditions = ["1=1"]
    params = base_params.copy()
    
    # Venue filter
    if venue:
        conditions.append("m.venue = :venue")
        params["venue"] = venue
    
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
            NULL as bowl_style,
            NULL as bowl_kind,
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
    
    query_params = {k: v for k, v in params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs']}
    
    # Get total balls for percentage calculation
    if total_balls_override is None:
        total_balls_query = f"""
            SELECT COUNT(*) 
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            {where_clause}
        """
        total_balls = db.execute(text(total_balls_query), query_params).scalar() or 0
    else:
        total_balls = total_balls_override
    
    # For multi-level grouping, get parent group totals (first column)
    parent_totals = {}
    if len(group_by) > 1:
        first_col = group_by[0]
        first_db_col = grouping_columns.get(first_col)
        if first_db_col and first_db_col != "NULL":
            parent_query = f"""
                SELECT {first_db_col} as parent_key, COUNT(*) as parent_balls
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                {where_clause}
                GROUP BY {first_db_col}
            """
            parent_result = db.execute(text(parent_query), query_params).fetchall()
            for row in parent_result:
                parent_totals[str(row[0])] = row[1]
    
    aggregation_query = f"""
        SELECT 
            {select_group_clause},
            COUNT(*) as balls,
            {runs_calculation} as runs,
            SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END) as wickets,
            SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
            SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
            SUM(CASE WHEN d.runs_off_bat = 4 THEN 1 ELSE 0 END) as fours,
            SUM(CASE WHEN d.runs_off_bat = 6 THEN 1 ELSE 0 END) as sixes
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        {where_clause}
        GROUP BY {group_by_clause}
        ORDER BY COUNT(*) DESC
    """
    
    result = db.execute(text(aggregation_query), query_params).fetchall()
    
    # Format results with fully calculated metrics
    formatted_results = []
    for row in result:
        row_dict = {}
        
        # Add grouping columns
        for i, col in enumerate(group_by):
            row_dict[col] = row[i]
        
        # Get raw stats
        stats_start = len(group_by)
        balls = row[stats_start] or 0
        runs = row[stats_start + 1] or 0
        wickets = row[stats_start + 2] or 0
        dots = row[stats_start + 3] or 0
        boundaries = row[stats_start + 4] or 0
        fours = row[stats_start + 5] or 0
        sixes = row[stats_start + 6] or 0
        
        # Calculate percent_balls relative to parent group (for multi-level) or total (for single-level)
        if len(group_by) > 1 and parent_totals:
            parent_key = str(row[0])  # First column value is the parent
            parent_balls = parent_totals.get(parent_key, total_balls)
            percent_balls = round((balls / parent_balls) * 100, 2) if parent_balls > 0 else 0
        else:
            percent_balls = round((balls / total_balls) * 100, 2) if total_balls > 0 else 0
        
        # Calculate all derived metrics
        row_dict.update({
            "balls": balls,
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
            # control_percentage not available in legacy - don't include it
        })
        
        formatted_results.append(row_dict)
    
    return formatted_results, total_balls


def get_legacy_total_balls(where_clause, params, db):
    """Get total ball count from legacy table for a given WHERE clause."""
    count_query = f"""
        SELECT COUNT(*) 
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        {where_clause}
    """
    count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs']}
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
    if not new_results:
        # Normalize legacy player names and crease_combo
        for row in legacy_results:
            if 'batter' in row and row.get('batter'):
                row['batter'] = normalize_player_name_for_merge(row['batter'], player_aliases_map)
            if 'bowler' in row and row.get('bowler'):
                row['bowler'] = normalize_player_name_for_merge(row['bowler'], player_aliases_map)
            if 'crease_combo' in row and row.get('crease_combo'):
                row['crease_combo'] = row['crease_combo'].lower()
        return legacy_results
    
    # Build a lookup by group key
    merged = {}
    
    def make_group_key(row: Dict) -> tuple:
        """Create a hashable key from grouping columns."""
        key_parts = []
        for col in group_by:
            val = row.get(col)
            # Normalize player names for key matching
            if col == 'batter' and val:
                val = normalize_player_name_for_merge(val, player_aliases_map)
            elif col == 'bowler' and val:
                val = normalize_player_name_for_merge(val, player_aliases_map)
            # Normalize crease_combo to lowercase
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
        # Normalize player names and crease_combo in the row
        if 'batter' in row and row.get('batter'):
            row['batter'] = normalize_player_name_for_merge(row['batter'], player_aliases_map)
        if 'bowler' in row and row.get('bowler'):
            row['bowler'] = normalize_player_name_for_merge(row['bowler'], player_aliases_map)
        if 'crease_combo' in row and row.get('crease_combo'):
            row['crease_combo'] = row['crease_combo'].lower()
        
        key = make_group_key(row)
        
        if key in merged:
            # Combine raw counts
            existing = merged[key]
            existing['balls'] = (existing.get('balls') or 0) + (row.get('balls') or 0)
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
    
    # Match context filters
    innings: Optional[int],
    over_min: Optional[int],
    over_max: Optional[int],
    
    # Grouping and aggregation
    group_by: List[str],
    show_summary_rows: bool,
    
    # Filters for grouped results
    min_balls: Optional[int],
    max_balls: Optional[int],
    min_runs: Optional[int],
    max_runs: Optional[int],
    
    # Pagination and limits
    limit: int,
    offset: int,
    
    # Include international matches
    include_international: bool,
    top_teams: Optional[int],
    
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
        logger.info(f"Query deliveries service called with filters: venue={venue}, leagues={leagues}, group_by={group_by}")
        logger.info(f"Date range: {start_date} to {end_date}")
        
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
            "innings": innings,
            "over_range": f"{over_min}-{over_max}" if over_min is not None or over_max is not None else None,
            "group_by": group_by
        }
        
        has_batter_filters = bool(batters) or bool(players)
        data_sources = []
        
        # =====================================================================
        # QUERY NEW TABLE (delivery_details) - 2015+
        # =====================================================================
        new_results = []
        new_total_count = 0
        new_total_balls = 0
        
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
                innings=innings,
                over_min=over_min,
                over_max=over_max,
                include_international=include_international,
                top_teams=top_teams,
                base_params=new_params
            )
            
            # Get total balls from new table
            total_balls_query = f"SELECT COUNT(*) FROM delivery_details dd {new_where_clause}"
            total_balls_params = {k: v for k, v in new_params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs']}
            new_total_balls = db.execute(text(total_balls_query), total_balls_params).scalar() or 0
            
            if not group_by or len(group_by) == 0:
                # Ungrouped query
                result = handle_ungrouped_query(new_where_clause, new_params, limit, offset, db, filters_applied)
                new_results = result['data']
                new_total_count = result['metadata']['total_matching_rows']
            else:
                # Grouped query - get raw results for potential merging
                result = handle_grouped_query(
                    new_where_clause, new_params, group_by, min_balls, max_balls,
                    min_runs, max_runs, limit, offset, db, filters_applied,
                    has_batter_filters, show_summary_rows
                )
                new_results = result['data']
                new_total_count = result['metadata']['total_groups']
            
            data_sources.append(f"delivery_details ({new_start.year}-{new_end.year})")
        
        # =====================================================================
        # QUERY LEGACY TABLE (deliveries) - Pre-2015
        # =====================================================================
        legacy_results = []
        legacy_total_count = 0
        legacy_total_balls = 0
        
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
                crease_combo=crease_combo,
                innings=innings,
                over_min=over_min,
                over_max=over_max,
                include_international=include_international,
                top_teams=top_teams,
                base_params=legacy_params,
                db=db
            )
            
            legacy_total_balls = get_legacy_total_balls(legacy_where_clause, legacy_params, db) or 0
            
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
            
            data_sources.append(f"deliveries ({legacy_start.year}-{legacy_end.year})")
        
        # =====================================================================
        # MERGE RESULTS
        # =====================================================================
        total_balls = new_total_balls + legacy_total_balls
        
        if routing['use_new'] and routing['use_legacy']:
            # Load player aliases for merging
            player_aliases_map = load_player_aliases_for_merge(db)
            
            if not group_by or len(group_by) == 0:
                # Merge ungrouped results
                merged_data = merge_ungrouped_results(new_results, legacy_results, player_aliases_map)
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
                
                total_count = len(merged_data)
                # Apply pagination
                merged_data = merged_data[offset:offset + limit]
        else:
            # Single source - no merge needed
            merged_data = new_results if routing['use_new'] else legacy_results
            total_count = new_total_count if routing['use_new'] else legacy_total_count
        
        # =====================================================================
        # BUILD RESPONSE
        # =====================================================================
        if not group_by or len(group_by) == 0:
            # Ungrouped response
            return {
                "data": merged_data,
                "metadata": {
                    "total_matching_rows": total_count,
                    "returned_rows": len(merged_data),
                    "limit": limit,
                    "offset": offset,
                    "has_more": total_count > (offset + len(merged_data)),
                    "filters_applied": filters_applied,
                    "data_sources": data_sources,
                    "warnings": routing['warnings'],
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
            
            return {
                "data": merged_data,
                "summary_data": summary_data,
                "percentages": percentages,
                "metadata": {
                    "total_groups": total_count,
                    "returned_groups": len(merged_data),
                    "total_balls_in_query": total_balls,
                    "limit": limit,
                    "offset": offset,
                    "has_more": total_count > (offset + len(merged_data)),
                    "grouped_by": group_by,
                    "filters_applied": filters_applied,
                    "has_summaries": summary_data is not None,
                    "data_sources": data_sources,
                    "warnings": routing['warnings'],
                    "note": "Grouped data with cricket aggregations" + (" (merged from multiple sources)" if len(data_sources) > 1 else "")
                }
            }
        
    except Exception as e:
        logger.error(f"Error in query_deliveries_service: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


def build_where_clause(
    venue, start_date, end_date, leagues, teams, batting_teams, bowling_teams,
    players, batters, bowlers, bat_hand, bowl_style, bowl_kind, crease_combo,
    line, length, shot, control, wagon_zone, innings, over_min, over_max,
    include_international, top_teams, base_params
):
    """Build dynamic WHERE clause for delivery_details table."""
    conditions = ["1=1"]
    params = base_params.copy()
    
    # Venue filter (ground in delivery_details)
    if venue:
        conditions.append("dd.ground = :venue")
        params["venue"] = venue
    
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
    
    # Player filters
    if players:
        conditions.append("(dd.bat = ANY(:players) OR dd.bowl = ANY(:players))")
        params["players"] = players
    
    if batters:
        conditions.append("dd.bat = ANY(:batters)")
        params["batters"] = batters
    
    if bowlers:
        conditions.append("dd.bowl = ANY(:bowlers)")
        params["bowlers"] = bowlers
    
    # Batter/Bowler attribute filters
    if bat_hand:
        conditions.append("dd.bat_hand = :bat_hand")
        params["bat_hand"] = bat_hand
    
    if bowl_style:
        conditions.append("dd.bowl_style = ANY(:bowl_style)")
        params["bowl_style"] = bowl_style
    
    if bowl_kind:
        conditions.append("dd.bowl_kind = ANY(:bowl_kind)")
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


def handle_ungrouped_query(where_clause, params, limit, offset, db, filters):
    """Return individual delivery records from delivery_details."""
    
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
        SELECT COUNT(*) FROM delivery_details dd {where_clause}
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
        
        # Innings/Phase
        "innings": "dd.inns",
        "phase": "CASE WHEN dd.over < 6 THEN 'powerplay' WHEN dd.over < 15 THEN 'middle' ELSE 'death' END",
        
        # Batter attributes
        "bat_hand": "dd.bat_hand",
        # Normalize crease_combo: RHB_LHB and LHB_RHB are both "mixed" - normalize to lowercase lhb_rhb
        "crease_combo": "LOWER(CASE WHEN dd.crease_combo = 'RHB_LHB' THEN 'LHB_RHB' ELSE dd.crease_combo END)",
        
        # Bowler attributes
        "bowl_style": "dd.bowl_style",
        "bowl_kind": "dd.bowl_kind",
        
        # Delivery details
        "line": "dd.line",
        "length": "dd.length",
        "shot": "dd.shot",
        "control": "dd.control",
        "wagon_zone": "dd.wagon_zone",
    }


def handle_grouped_query(
    where_clause, params, group_by, min_balls, max_balls, 
    min_runs, max_runs, limit, offset, db, filters_applied=None,
    has_batter_filters=False, show_summary_rows=False
):
    """Return aggregated cricket statistics grouped by specified columns."""
    
    grouping_columns = get_grouping_columns_map()
    
    # Validate columns
    invalid_columns = [col for col in group_by if col not in grouping_columns]
    if invalid_columns:
        raise HTTPException(status_code=400, detail=f"Invalid group_by columns: {invalid_columns}")
    
    # Build GROUP BY clause
    group_columns = []
    select_columns = []
    
    for col in group_by:
        db_column = grouping_columns[col]
        group_columns.append(db_column)
        select_columns.append(f"{db_column} as {col}")
    
    group_by_clause = ", ".join(group_columns)
    select_group_clause = ", ".join(select_columns)
    
    # Determine runs calculation
    batter_grouping = "batter" in group_by
    use_runs_off_bat_only = batter_grouping or has_batter_filters
    runs_calculation = "SUM(dd.batruns)" if use_runs_off_bat_only else "SUM(dd.score)"
    
    # Build HAVING clause
    having_conditions = []
    if min_balls is not None:
        having_conditions.append("COUNT(*) >= :min_balls")
        params["min_balls"] = min_balls
    if max_balls is not None:
        having_conditions.append("COUNT(*) <= :max_balls")
        params["max_balls"] = max_balls
    if min_runs is not None:
        having_conditions.append(f"{runs_calculation} >= :min_runs")
        params["min_runs"] = min_runs
    if max_runs is not None:
        having_conditions.append(f"{runs_calculation} <= :max_runs")
        params["max_runs"] = max_runs
    
    having_clause = "HAVING " + " AND ".join(having_conditions) if having_conditions else ""
    
    # Get total balls matching the WHERE clause
    total_balls_query = f"""
        SELECT COUNT(*) FROM delivery_details dd {where_clause}
    """
    total_balls_params = {k: v for k, v in params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs']}
    total_balls = db.execute(text(total_balls_query), total_balls_params).scalar()
    
    # For multi-level grouping, get parent group totals (first column)
    parent_totals = {}
    if len(group_by) > 1:
        first_col = group_by[0]
        first_db_col = grouping_columns[first_col]
        parent_query = f"""
            SELECT {first_db_col} as parent_key, COUNT(*) as parent_balls
            FROM delivery_details dd
            {where_clause}
            GROUP BY {first_db_col}
        """
        parent_result = db.execute(text(parent_query), total_balls_params).fetchall()
        for row in parent_result:
            parent_totals[str(row[0])] = row[1]
    
    # Build aggregation query
    aggregation_query = f"""
        SELECT 
            {select_group_clause},
            COUNT(*) as balls,
            {runs_calculation} as runs,
            SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
            SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
            SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
            SUM(CASE WHEN dd.batruns = 4 THEN 1 ELSE 0 END) as fours,
            SUM(CASE WHEN dd.batruns = 6 THEN 1 ELSE 0 END) as sixes,
            
            -- Average
            CASE WHEN SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) > 0 
                THEN CAST({runs_calculation} AS DECIMAL) / SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END)
                ELSE NULL END as average,
            
            -- Strike Rate
            CASE WHEN COUNT(*) > 0 
                THEN (CAST({runs_calculation} AS DECIMAL) * 100.0) / COUNT(*)
                ELSE 0 END as strike_rate,
            
            -- Balls per dismissal
            CASE WHEN SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) > 0 
                THEN CAST(COUNT(*) AS DECIMAL) / SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END)
                ELSE NULL END as balls_per_dismissal,
            
            -- Dot percentage
            CASE WHEN COUNT(*) > 0 
                THEN (CAST(SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / COUNT(*)
                ELSE 0 END as dot_percentage,
            
            -- Boundary percentage
            CASE WHEN COUNT(*) > 0 
                THEN (CAST(SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / COUNT(*)
                ELSE 0 END as boundary_percentage,
            
            -- Control percentage
            CASE WHEN SUM(CASE WHEN dd.control IS NOT NULL THEN 1 ELSE 0 END) > 0
                THEN (CAST(SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / 
                      SUM(CASE WHEN dd.control IS NOT NULL THEN 1 ELSE 0 END)
                ELSE NULL END as control_percentage
            
        FROM delivery_details dd
        {where_clause}
        GROUP BY {group_by_clause}
        {having_clause}
        ORDER BY balls DESC
        LIMIT :limit
        OFFSET :offset
    """
    
    result = db.execute(text(aggregation_query), params).fetchall()
    
    # Format results
    formatted_results = []
    for row in result:
        row_dict = {}
        
        # Add grouping columns
        for i, col in enumerate(group_by):
            row_dict[col] = row[i]
        
        # Add statistics
        stats_start = len(group_by)
        balls = row[stats_start]
        
        # Calculate percent_balls relative to parent group (for multi-level) or total (for single-level)
        if len(group_by) > 1 and parent_totals:
            parent_key = str(row[0])  # First column value is the parent
            parent_balls = parent_totals.get(parent_key, total_balls)
            percent_balls = round((balls / parent_balls) * 100, 2) if parent_balls > 0 else 0
        else:
            percent_balls = round((balls / total_balls) * 100, 2) if total_balls > 0 else 0
        
        row_dict.update({
            "balls": balls,
            "runs": row[stats_start + 1],
            "wickets": row[stats_start + 2],
            "dots": row[stats_start + 3],
            "boundaries": row[stats_start + 4],
            "fours": row[stats_start + 5],
            "sixes": row[stats_start + 6],
            "average": float(row[stats_start + 7]) if row[stats_start + 7] is not None else None,
            "strike_rate": float(row[stats_start + 8]) if row[stats_start + 8] is not None else 0,
            "balls_per_dismissal": float(row[stats_start + 9]) if row[stats_start + 9] is not None else None,
            "dot_percentage": float(row[stats_start + 10]) if row[stats_start + 10] is not None else 0,
            "boundary_percentage": float(row[stats_start + 11]) if row[stats_start + 11] is not None else 0,
            "control_percentage": float(row[stats_start + 12]) if row[stats_start + 12] is not None else None,
            "percent_balls": percent_balls
        })
        
        formatted_results.append(row_dict)
    
    # Count total groups
    count_query = f"""
        SELECT COUNT(*) FROM (
            SELECT {group_by_clause}
            FROM delivery_details dd
            {where_clause}
            GROUP BY {group_by_clause}
            {having_clause}
        ) as grouped_count
    """
    count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
    total_groups = db.execute(text(count_query), count_params).scalar()
    
    # Generate summary data if requested
    summary_data = None
    percentages = None
    if show_summary_rows and len(group_by) >= 1:
        summary_data, percentages = generate_summary_data(where_clause, params, group_by, runs_calculation, db, total_balls)
    
    return {
        "data": formatted_results,
        "summary_data": summary_data,
        "percentages": percentages,
        "metadata": {
            "total_groups": total_groups,
            "returned_groups": len(formatted_results),
            "total_balls_in_query": total_balls,
            "limit": limit,
            "offset": offset,
            "has_more": total_groups > (offset + len(formatted_results)),
            "grouped_by": group_by,
            "filters_applied": filters_applied,
            "has_summaries": summary_data is not None,
            "note": "Grouped data from delivery_details with cricket aggregations"
        }
    }


def generate_summary_data(where_clause, params, group_by, runs_calculation, db, total_balls):
    """Generate hierarchical summary data for grouped queries with percent_balls."""
    try:
        grouping_columns = get_grouping_columns_map()
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
            
            summary_query = f"""
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
                {where_clause}
                GROUP BY {summary_group_by_clause}
                ORDER BY total_balls DESC
            """
            
            summary_params = {k: v for k, v in params.items() if k not in ['limit', 'offset', 'min_balls', 'max_balls', 'min_runs', 'max_runs']}
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
