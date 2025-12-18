"""
Query Builder Service - Using delivery_details table

This service provides flexible querying of ball-by-ball cricket data
with support for filtering, grouping, and aggregation.
"""

from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from datetime import date
from models import teams_mapping, INTERNATIONAL_TEAMS_RANKED, leagues_mapping, league_aliases, get_full_league_name
import logging

logger = logging.getLogger(__name__)


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
    """Main service function to query delivery_details with flexible filtering and grouping."""
    try:
        logger.info(f"Query deliveries service called with filters: venue={venue}, leagues={leagues}, group_by={group_by}")
        
        params = {
            "limit": min(limit, 10000),
            "offset": offset
        }
        
        # Build WHERE clause
        where_clause, params = build_where_clause(
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
            bat_hand=bat_hand,
            bowl_style=bowl_style,
            bowl_kind=bowl_kind,
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
            base_params=params
        )
        
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
            "line": line,
            "length": length,
            "shot": shot,
            "control": control,
            "wagon_zone": wagon_zone,
            "innings": innings,
            "over_range": f"{over_min}-{over_max}" if over_min is not None or over_max is not None else None,
            "group_by": group_by
        }
        
        # Route to appropriate handler
        if not group_by or len(group_by) == 0:
            return handle_ungrouped_query(where_clause, params, limit, offset, db, filters_applied)
        else:
            has_batter_filters = bool(batters) or bool(players)
            return handle_grouped_query(
                where_clause, params, group_by, min_balls, max_balls, 
                min_runs, max_runs, limit, offset, db, filters_applied, 
                has_batter_filters, show_summary_rows
            )
        
    except Exception as e:
        logger.error(f"Error in query_deliveries_service: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


def build_where_clause(
    venue, start_date, end_date, leagues, teams, batting_teams, bowling_teams,
    players, batters, bowlers, bat_hand, bowl_style, bowl_kind,
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
    
    # League filters
    if leagues:
        expanded_leagues = expand_league_abbreviations(leagues)
        conditions.append("dd.competition = ANY(:leagues)")
        params["leagues"] = expanded_leagues
    
    # International matches
    if include_international:
        if top_teams:
            top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            conditions.append("(dd.competition = 'T20I' AND dd.team_bat = ANY(:top_teams) AND dd.team_bowl = ANY(:top_teams))")
            params["top_teams"] = top_team_list
        else:
            conditions.append("dd.competition = 'T20I'")
    
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


def expand_league_abbreviations(abbrevs: List[str]) -> List[str]:
    """Expand league abbreviations to include variations."""
    expanded = []
    for abbrev in abbrevs:
        expanded.append(abbrev)
        if abbrev in leagues_mapping:
            expanded.append(leagues_mapping[abbrev])
        else:
            full_name = get_full_league_name(abbrev)
            if full_name != abbrev:
                expanded.append(full_name)
        
        for alias, std_name in league_aliases.items():
            if abbrev == std_name or abbrev == alias:
                expanded.append(alias)
                expanded.append(std_name)
    
    return list(set(expanded))


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
            "line": row[13],
            "length": row[14],
            "shot": row[15],
            "control": row[16],
            "wagon_x": row[17],
            "wagon_y": row[18],
            "wagon_zone": row[19],
            "wicket_type": row[20],
            "venue": row[21],
            "date": row[22],
            "competition": row[23],
            "year": row[24],
            "outcome": row[25]
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
            
            -- Control percentage (NEW)
            CASE WHEN SUM(CASE WHEN dd.control IS NOT NULL THEN 1 ELSE 0 END) > 0
                THEN (CAST(SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / 
                      SUM(CASE WHEN dd.control IS NOT NULL THEN 1 ELSE 0 END)
                ELSE NULL END as control_percentage
            
        FROM delivery_details dd
        {where_clause}
        GROUP BY {group_by_clause}
        {having_clause}
        ORDER BY runs DESC
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
        row_dict.update({
            "balls": row[stats_start],
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
            "control_percentage": float(row[stats_start + 12]) if row[stats_start + 12] is not None else None
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
    if show_summary_rows and len(group_by) > 1:
        summary_data = generate_summary_data(where_clause, params, group_by, runs_calculation, db)
    
    return {
        "data": formatted_results,
        "summary_data": summary_data,
        "metadata": {
            "total_groups": total_groups,
            "returned_groups": len(formatted_results),
            "limit": limit,
            "offset": offset,
            "has_more": total_groups > (offset + len(formatted_results)),
            "grouped_by": group_by,
            "filters_applied": filters_applied,
            "has_summaries": summary_data is not None,
            "note": "Grouped data from delivery_details with cricket aggregations"
        }
    }


def generate_summary_data(where_clause, params, group_by, runs_calculation, db):
    """Generate hierarchical summary data for grouped queries."""
    try:
        grouping_columns = get_grouping_columns_map()
        summaries = {}
        
        for level in range(1, len(group_by)):
            summary_group_by = group_by[:level]
            summary_key = f"{summary_group_by[0]}_summaries" if level == 1 else f"level_{level}_summaries"
            
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
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as total_boundaries
                FROM delivery_details dd
                {where_clause}
                GROUP BY {summary_group_by_clause}
                ORDER BY total_runs DESC
            """
            
            summary_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
            summary_result = db.execute(text(summary_query), summary_params).fetchall()
            
            formatted_summaries = []
            for row in summary_result:
                summary_dict = {}
                for i, col in enumerate(summary_group_by):
                    summary_dict[col] = row[i]
                
                stats_start = len(summary_group_by)
                summary_dict.update({
                    "total_balls": row[stats_start],
                    "total_runs": row[stats_start + 1],
                    "total_wickets": row[stats_start + 2],
                    "total_dots": row[stats_start + 3],
                    "total_boundaries": row[stats_start + 4]
                })
                formatted_summaries.append(summary_dict)
            
            summaries[summary_key] = formatted_summaries
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error generating summary data: {str(e)}")
        return None
