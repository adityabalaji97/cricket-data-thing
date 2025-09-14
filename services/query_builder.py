from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from datetime import date
from models import teams_mapping, INTERNATIONAL_TEAMS_RANKED
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
    
    # Column-specific filters
    crease_combo: Optional[str],
    ball_direction: Optional[str],
    bowler_type: List[str],
    striker_batter_type: Optional[str],
    non_striker_batter_type: Optional[str],
    innings: Optional[int],
    over_min: Optional[int],
    over_max: Optional[int],
    wicket_type: Optional[str],
    
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
    Main service function to query deliveries with flexible filtering and grouping.
    
    This function builds dynamic SQL queries based on the provided filters and grouping options.
    Routes to either individual delivery records or grouped aggregations based on group_by parameter.
    """
    try:
        logger.info(f"Query deliveries service called with filters: venue={venue}, leagues={leagues}, group_by={group_by}")
        logger.info(f"Date filters received: start_date={start_date}, end_date={end_date}")
        
        # Build dynamic WHERE conditions
        params = {
            "limit": min(limit, 10000),  # Enforce max limit
            "offset": offset
        }
        
        # Build WHERE clause using helper function
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
            crease_combo=crease_combo,
            ball_direction=ball_direction,
            bowler_type=bowler_type,
            striker_batter_type=striker_batter_type,
            non_striker_batter_type=non_striker_batter_type,
            innings=innings,
            over_min=over_min,
            over_max=over_max,
            wicket_type=wicket_type,
            include_international=include_international,
            top_teams=top_teams,
            base_params=params
        )
        
        # Prepare filters for metadata
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
            "crease_combo": crease_combo,
            "ball_direction": ball_direction,
            "bowler_type": bowler_type,
            "striker_batter_type": striker_batter_type,
            "non_striker_batter_type": non_striker_batter_type,
            "innings": innings,
            "over_range": f"{over_min}-{over_max}" if over_min is not None or over_max is not None else None,
            "wicket_type": wicket_type,
            "group_by": group_by
        }
        
        # Step 3: Route to appropriate handler based on grouping
        if not group_by or len(group_by) == 0:
            # No grouping - return individual delivery records
            logger.info("Handling ungrouped query (individual deliveries)")
            return handle_ungrouped_query(where_clause, params, limit, offset, db, filters_applied)
        else:
            # Grouping requested - return aggregated cricket statistics
            logger.info(f"Handling grouped query with grouping: {group_by}")
            # Check if batter filters are applied
            has_batter_filters = bool(batters) or bool(players)
            return handle_grouped_query(where_clause, params, group_by, min_balls, max_balls, min_runs, max_runs, limit, offset, db, filters_applied, has_batter_filters, show_summary_rows)
        
    except Exception as e:
        logger.error(f"Error in query_deliveries_service: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

def build_where_clause(
    venue, start_date, end_date, leagues, teams, batting_teams, bowling_teams, players, batters, bowlers,
    crease_combo, ball_direction, bowler_type, striker_batter_type,
    non_striker_batter_type, innings, over_min, over_max, wicket_type,
    include_international, top_teams, base_params
):
    """
    Build dynamic WHERE clause based on provided filters.
    
    Returns:
        Tuple of (where_clause_string, params_dict)
    """
    conditions = ["1=1"]  # Always true base condition
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
    
    # League filters (using your existing pattern)
    if leagues:
        # Expand league abbreviations like in your main.py
        from models import get_league_abbreviation, get_full_league_name
        expanded_leagues = expand_league_abbreviations(leagues)
        conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
        params["leagues"] = expanded_leagues
    
    # International matches
    if include_international:
        if top_teams:
            top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            conditions.append("(m.match_type = 'international' AND m.team1 = ANY(:top_teams) AND m.team2 = ANY(:top_teams))")
            params["top_teams"] = top_team_list
        else:
            conditions.append("(m.match_type = 'international')")
    
    # Team filters - handle general teams, batting teams, and bowling teams
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
    
    # Player filters - handle both generic and specific
    if players:
        conditions.append("(d.batter = ANY(:players) OR d.bowler = ANY(:players))")
        params["players"] = players
    
    # Specific batter filters
    if batters:
        conditions.append("d.batter = ANY(:batters)")
        params["batters"] = batters
    
    # Specific bowler filters  
    if bowlers:
        conditions.append("d.bowler = ANY(:bowlers)")
        params["bowlers"] = bowlers
    
    # Column-specific filters
    if crease_combo:
        conditions.append("d.crease_combo = :crease_combo")
        params["crease_combo"] = crease_combo
    
    if ball_direction:
        conditions.append("d.ball_direction = :ball_direction")
        params["ball_direction"] = ball_direction
    
    if bowler_type:
        conditions.append("d.bowler_type = ANY(:bowler_type)")
        params["bowler_type"] = bowler_type
    
    if striker_batter_type:
        conditions.append("d.striker_batter_type = :striker_batter_type")
        params["striker_batter_type"] = striker_batter_type
    
    if non_striker_batter_type:
        conditions.append("d.non_striker_batter_type = :non_striker_batter_type")
        params["non_striker_batter_type"] = non_striker_batter_type
    
    if innings:
        conditions.append("d.innings = :innings")
        params["innings"] = innings
    
    if over_min is not None:
        conditions.append("d.over >= :over_min")
        params["over_min"] = over_min
    
    if over_max is not None:
        conditions.append("d.over <= :over_max")
        params["over_max"] = over_max
    
    if wicket_type:
        conditions.append("d.wicket_type = :wicket_type")
        params["wicket_type"] = wicket_type
    
    where_clause = "WHERE " + " AND ".join(conditions)
    return where_clause, params

def expand_league_abbreviations(abbrevs: List[str]) -> List[str]:
    """
    Expand league abbreviations to include both abbreviation and full name.
    Reused from main.py pattern.
    """
    from models import leagues_mapping, league_aliases, get_full_league_name
    
    expanded = []
    for abbrev in abbrevs:
        if abbrev in leagues_mapping:
            expanded.append(abbrev)
            expanded.append(leagues_mapping[abbrev])
        else:
            full_name = get_full_league_name(abbrev)
            if full_name != abbrev:
                expanded.append(full_name)
                expanded.append(abbrev)
            else:
                expanded.append(abbrev)
        
        for alias, std_name in league_aliases.items():
            if abbrev == std_name or abbrev == alias:
                expanded.append(alias)
                expanded.append(std_name)
    
    # Remove duplicates
    result = []
    for item in expanded:
        if item not in result:
            result.append(item)
    
    return result

def get_all_team_name_variations(team_name):
    """
    Helper function to get all possible name variations for a team.
    Reused from existing codebase pattern.
    """
    reverse_mapping = {}
    for full_name, abbrev in teams_mapping.items():
        if abbrev not in reverse_mapping:
            reverse_mapping[abbrev] = []
        reverse_mapping[abbrev].append(full_name)
    
    if team_name in reverse_mapping:
        return reverse_mapping[team_name]
    
    abbrev = teams_mapping.get(team_name)
    if abbrev and abbrev in reverse_mapping:
        return reverse_mapping[abbrev]
    
    return [team_name]

def handle_ungrouped_query(where_clause, params, limit, offset, db, filters):
    """
    Handle queries without grouping - return individual delivery records.
    """
    # Build the main query
    main_query = f"""
        SELECT 
            d.match_id,
            d.innings,
            d.over,
            d.ball,
            d.batter,
            d.bowler,
            d.runs_off_bat,
            d.extras,
            d.batting_team,
            d.bowling_team,
            d.crease_combo,
            d.ball_direction,
            d.bowler_type,
            d.striker_batter_type,
            d.non_striker_batter_type,
            d.wicket_type,
            m.venue,
            m.date,
            m.competition,
            EXTRACT(YEAR FROM m.date) as year
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        {where_clause}
        ORDER BY m.date DESC, d.over, d.ball
        LIMIT :limit
        OFFSET :offset
    """
    
    result = db.execute(text(main_query), params).fetchall()
    
    # Format results
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
            "extras": row[7],
            "batting_team": row[8],
            "bowling_team": row[9],
            "crease_combo": row[10],
            "ball_direction": row[11],
            "bowler_type": row[12],
            "striker_batter_type": row[13],
            "non_striker_batter_type": row[14],
            "wicket_type": row[15],
            "venue": row[16],
            "date": row[17].isoformat() if row[17] else None,
            "competition": row[18],
            "year": int(row[19]) if row[19] is not None else None
        })
    
    # Count total matching rows (for pagination info)
    count_query = f"""
        SELECT COUNT(*) 
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        {where_clause}
    """
    
    # Remove LIMIT and OFFSET params for count query (but keep min/max filters for HAVING clause)
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
            "note": "Step 2: Individual delivery records (no grouping)"
        }
    }

def handle_grouped_query(where_clause, params, group_by, min_balls, max_balls, min_runs, max_runs, limit, offset, db, filters_applied=None, has_batter_filters=False, show_summary_rows=False):
    """
    Handle queries with grouping - return aggregated cricket statistics.
    """
    # Map group_by values to actual column names
    grouping_columns = get_grouping_columns_map()
    
    # Validate group_by columns
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
    
    # Determine if we should use runs_off_bat only (for batter grouping or batter filters) or include extras
    batter_grouping = "batter" in group_by
    use_runs_off_bat_only = batter_grouping or has_batter_filters
    runs_calculation = "SUM(d.runs_off_bat)" if use_runs_off_bat_only else "SUM(d.runs_off_bat + d.extras)"
    
    # Build HAVING clause for grouped result filters
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
    
    # Build aggregation query with cricket metrics
    aggregation_query = f"""
        SELECT 
            {select_group_clause},
            COUNT(*) as balls,
            {runs_calculation} as runs,
            SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END) as wickets,
            SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
            SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
            SUM(CASE WHEN d.runs_off_bat = 4 THEN 1 ELSE 0 END) as fours,
            SUM(CASE WHEN d.runs_off_bat = 6 THEN 1 ELSE 0 END) as sixes,
            
            -- Calculated cricket metrics (PostgreSQL compatible)
            CASE WHEN SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END) > 0 
                THEN CAST({runs_calculation} AS DECIMAL) / SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END)
                ELSE NULL END as average,
            
            CASE WHEN COUNT(*) > 0 
                THEN (CAST({runs_calculation} AS DECIMAL) * 100.0) / COUNT(*)
                ELSE 0 END as strike_rate,
            
            CASE WHEN SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END) > 0 
                THEN CAST(COUNT(*) AS DECIMAL) / SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END)
                ELSE NULL END as balls_per_dismissal,
            
            CASE WHEN COUNT(*) > 0 
                THEN (CAST(SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / COUNT(*)
                ELSE 0 END as dot_percentage,
            
            CASE WHEN COUNT(*) > 0 
                THEN (CAST(SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / COUNT(*)
                ELSE 0 END as boundary_percentage
            
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
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
        
        # Add cricket statistics
        stats_start_index = len(group_by)
        row_dict.update({
            "balls": row[stats_start_index],
            "runs": row[stats_start_index + 1],
            "wickets": row[stats_start_index + 2],
            "dots": row[stats_start_index + 3],
            "boundaries": row[stats_start_index + 4],
            "fours": row[stats_start_index + 5],
            "sixes": row[stats_start_index + 6],
            "average": float(row[stats_start_index + 7]) if row[stats_start_index + 7] is not None else None,
            "strike_rate": float(row[stats_start_index + 8]) if row[stats_start_index + 8] is not None else 0,
            "balls_per_dismissal": float(row[stats_start_index + 9]) if row[stats_start_index + 9] is not None else None,
            "dot_percentage": float(row[stats_start_index + 10]) if row[stats_start_index + 10] is not None else 0,
            "boundary_percentage": float(row[stats_start_index + 11]) if row[stats_start_index + 11] is not None else 0
        })
        
        formatted_results.append(row_dict)
    
    # Count total groups (for pagination info)
    count_query = f"""
        SELECT COUNT(*) FROM (
            SELECT {group_by_clause}
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            {where_clause}
            GROUP BY {group_by_clause}
            {having_clause}
        ) as grouped_count
    """
    
    # Remove LIMIT and OFFSET params for count query
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
            "note": "Step 3: Grouped data with cricket aggregations"
        }
    }

def get_grouping_columns_map():
    """
    Map user-friendly group_by values to actual database column names.
    """
    return {
        "venue": "m.venue",
        "match_id": "d.match_id",
        "crease_combo": "d.crease_combo",
        "ball_direction": "d.ball_direction",
        "bowler_type": "d.bowler_type",
        "striker_batter_type": "d.striker_batter_type",
        "non_striker_batter_type": "d.non_striker_batter_type",
        "innings": "d.innings",
        "batting_team": "d.batting_team",
        "bowling_team": "d.bowling_team",
        "batter": "d.batter",
        "bowler": "d.bowler",
        "competition": "m.competition",
        "year": "EXTRACT(YEAR FROM m.date)",
        "phase": "CASE WHEN d.over < 6 THEN 'powerplay' WHEN d.over < 15 THEN 'middle' ELSE 'death' END"
    }

def generate_summary_data(where_clause, params, group_by, runs_calculation, db):
    """
    Generate hierarchical summary data and percentage calculations for grouped queries.
    
    For example, if grouping by [year, crease_combo]:
    - Generate summaries for each year (first group level)
    - Calculate what % each crease_combo represents within its year
    """
    try:
        grouping_columns = get_grouping_columns_map()
        
        # Generate summary data for each group level (except the last one)
        summaries = {}
        percentages = []
        
        # For each level from 1 to len(group_by)-1, create summary groups
        for level in range(1, len(group_by)):
            summary_group_by = group_by[:level]
            summary_key = f"{summary_group_by[0]}_summaries" if level == 1 else f"level_{level}_summaries"
            
            # Build summary query for this level
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
                    SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END) as total_wickets,
                    SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as total_dots,
                    SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as total_boundaries,
                    SUM(CASE WHEN d.runs_off_bat = 4 THEN 1 ELSE 0 END) as total_fours,
                    SUM(CASE WHEN d.runs_off_bat = 6 THEN 1 ELSE 0 END) as total_sixes
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                {where_clause}
                GROUP BY {summary_group_by_clause}
                ORDER BY total_runs DESC
            """
            
            # Remove pagination params for summary queries
            summary_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
            summary_result = db.execute(text(summary_query), summary_params).fetchall()
            
            # Format summary results
            formatted_summaries = []
            for row in summary_result:
                summary_dict = {}
                # Add grouping columns
                for i, col in enumerate(summary_group_by):
                    summary_dict[col] = row[i]
                
                # Add aggregated stats
                stats_start = len(summary_group_by)
                summary_dict.update({
                    "total_balls": row[stats_start],
                    "total_runs": row[stats_start + 1],
                    "total_wickets": row[stats_start + 2],
                    "total_dots": row[stats_start + 3],
                    "total_boundaries": row[stats_start + 4],
                    "total_fours": row[stats_start + 5],
                    "total_sixes": row[stats_start + 6]
                })
                
                formatted_summaries.append(summary_dict)
            
            summaries[summary_key] = formatted_summaries
        
        # Generate percentage calculations for the main data
        # For each row in the main results, calculate what % it represents within its parent group
        if len(group_by) >= 2:
            parent_group_by = group_by[:-1]  # All but the last grouping column
            
            # Build percentage calculation query
            parent_columns = []
            parent_group_clause = []
            
            for col in parent_group_by:
                db_column = grouping_columns[col]
                parent_group_clause.append(db_column)
                parent_columns.append(f"{db_column} as {col}")
            
            parent_group_by_clause = ", ".join(parent_group_clause)
            parent_select_clause = ", ".join(parent_columns)
            
            # Query to get totals for each parent group
            parent_totals_query = f"""
                SELECT 
                    {parent_select_clause},
                    COUNT(*) as parent_total_balls
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                {where_clause}
                GROUP BY {parent_group_by_clause}
            """
            
            parent_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
            parent_totals_result = db.execute(text(parent_totals_query), parent_params).fetchall()
            
            # Create lookup for parent totals
            parent_totals_lookup = {}
            for row in parent_totals_result:
                key_parts = []
                for i, col in enumerate(parent_group_by):
                    key_parts.append(str(row[i]))
                parent_key = "|".join(key_parts)
                parent_totals_lookup[parent_key] = row[len(parent_group_by)]  # parent_total_balls
            
            # Now get full detailed data with parent keys to calculate percentages
            full_group_columns = []
            full_group_clause = []
            
            for col in group_by:
                db_column = grouping_columns[col]
                full_group_clause.append(db_column)
                full_group_columns.append(f"{db_column} as {col}")
            
            full_group_by_clause = ", ".join(full_group_clause)
            full_select_clause = ", ".join(full_group_columns)
            
            percentage_query = f"""
                SELECT 
                    {full_select_clause},
                    COUNT(*) as balls
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                {where_clause}
                GROUP BY {full_group_by_clause}
            """
            
            percentage_result = db.execute(text(percentage_query), parent_params).fetchall()
            
            # Calculate percentages
            for row in percentage_result:
                percentage_dict = {}
                
                # Add all grouping columns
                for i, col in enumerate(group_by):
                    percentage_dict[col] = row[i]
                
                # Build parent key for lookup
                parent_key_parts = []
                for i, col in enumerate(parent_group_by):
                    parent_key_parts.append(str(row[i]))
                parent_key = "|".join(parent_key_parts)
                
                # Calculate percentage
                balls_for_this_row = row[len(group_by)]  # balls count
                parent_total = parent_totals_lookup.get(parent_key, 0)
                
                if parent_total > 0:
                    percent_balls = (balls_for_this_row / parent_total) * 100.0
                else:
                    percent_balls = 0.0
                
                percentage_dict["percent_balls"] = round(percent_balls, 1)
                percentages.append(percentage_dict)
        
        return {
            **summaries,
            "percentages": percentages
        }
        
    except Exception as e:
        logger.error(f"Error generating summary data: {str(e)}")
        return None
