from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import List, Optional
from datetime import date
from models import teams_mapping, Match, BattingStats

def get_all_team_name_variations(team_name: str) -> List[str]:
    """Get all possible name variations for a given team based on teams_mapping"""
    # Create a reverse mapping from abbreviation to all team names
    reverse_mapping = {}
    for full_name, abbrev in teams_mapping.items():
        if abbrev not in reverse_mapping:
            reverse_mapping[abbrev] = []
        reverse_mapping[abbrev].append(full_name)
    
    # If team_name is an abbreviation, return all full names for it
    if team_name in reverse_mapping:
        return reverse_mapping[team_name]
    
    # If it's a full name, find its abbreviation and return all related names
    abbrev = teams_mapping.get(team_name)
    if abbrev and abbrev in reverse_mapping:
        return reverse_mapping[abbrev]
    
    # If not found in mapping, return just the original name
    return [team_name]

def get_team_matches_service(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    db
) -> List[dict]:
    """
    Get all matches played by a team within the specified date range
    """
    try:
        team_variations = get_all_team_name_variations(team_name)
        
        matches_query = text("""
            WITH match_scores AS (
                SELECT 
                    m.id, m.date, m.venue, m.city, m.event_name,
                    m.team1, m.team2, m.winner, m.toss_winner, m.toss_decision,
                    m.competition, m.match_type,
                    (SELECT CONCAT(COALESCE(SUM(d1.runs_off_bat + d1.extras), 0), '/', 
                                   COALESCE(COUNT(CASE WHEN d1.wicket_type IS NOT NULL THEN 1 END), 0))
                     FROM deliveries d1 WHERE d1.match_id = m.id AND d1.innings = 1) as team1_score,
                    (SELECT CONCAT(COALESCE(SUM(d2.runs_off_bat + d2.extras), 0), '/', 
                                   COALESCE(COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END), 0))
                     FROM deliveries d2 WHERE d2.match_id = m.id AND d2.innings = 2) as team2_score
                FROM matches m
                WHERE (m.team1 = ANY(:team_variations) OR m.team2 = ANY(:team_variations))
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                ORDER BY m.date DESC
            )
            SELECT * FROM match_scores
        """)
        
        results = db.execute(matches_query, {
            "team_variations": team_variations,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        matches = []
        for row in results:
            team_was_team1 = row.team1 in team_variations
            opponent = row.team2 if team_was_team1 else row.team1
            team_score = row.team1_score if team_was_team1 else row.team2_score
            opponent_score = row.team2_score if team_was_team1 else row.team1_score
            
            match_result = "NR"
            if row.winner:
                match_result = "W" if row.winner in team_variations else "L"
            
            match_data = {
                "match_id": row.id,
                "date": row.date.isoformat() if row.date else None,
                "venue": row.venue,
                "city": row.city,
                "event_name": row.event_name,
                "competition": row.competition,
                "match_type": row.match_type,
                "team": teams_mapping.get(team_name, team_name),
                "opponent": teams_mapping.get(opponent, opponent),
                "team_score": team_score,
                "opponent_score": opponent_score,
                "result": match_result,
                "toss_winner": teams_mapping.get(row.toss_winner, row.toss_winner) if row.toss_winner else None,
                "toss_decision": row.toss_decision,
                "batted_first": team_was_team1,
                "winner": teams_mapping.get(row.winner, row.winner) if row.winner else None
            }
            matches.append(match_data)
        
        return matches
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team matches: {str(e)}")

def get_team_batting_stats_service(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    db
) -> List[dict]:
    """
    Get all batting stats for a team within the specified date range
    """
    try:
        team_variations = get_all_team_name_variations(team_name)
        
        batting_stats_query = text("""
            SELECT bs.*, m.date, m.venue, m.competition
            FROM batting_stats bs
            INNER JOIN matches m ON bs.match_id = m.id
            WHERE bs.batting_team = ANY(:team_variations)
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            ORDER BY m.date DESC, bs.innings ASC, bs.batting_position ASC
        """)
        
        results = db.execute(batting_stats_query, {
            "team_variations": team_variations,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()
        
        batting_stats = []
        for row in results:
            stat_data = {
                "match_id": row.match_id,
                "innings": row.innings,
                "striker": row.striker,
                "batting_team": teams_mapping.get(row.batting_team, row.batting_team),
                "runs": row.runs,
                "balls_faced": row.balls_faced,
                "wickets": row.wickets,
                "fours": row.fours,
                "sixes": row.sixes,
                "dots": row.dots,
                "ones": row.ones,
                "twos": row.twos,
                "threes": row.threes,
                "strike_rate": float(row.strike_rate) if row.strike_rate else None,
                "fantasy_points": float(row.fantasy_points) if row.fantasy_points else None,
                "batting_points": float(row.batting_points) if row.batting_points else None,
                "bowling_points": float(row.bowling_points) if row.bowling_points else None,
                "fielding_points": float(row.fielding_points) if row.fielding_points else None,
                "powerplay": {
                    "runs": row.pp_runs,
                    "balls": row.pp_balls,
                    "wickets": row.pp_wickets,
                    "dots": row.pp_dots,
                    "boundaries": row.pp_boundaries,
                    "strike_rate": float(row.pp_strike_rate) if row.pp_strike_rate else None
                },
                "middle_overs": {
                    "runs": row.middle_runs,
                    "balls": row.middle_balls,
                    "wickets": row.middle_wickets,
                    "dots": row.middle_dots,
                    "boundaries": row.middle_boundaries,
                    "strike_rate": float(row.middle_strike_rate) if row.middle_strike_rate else None
                },
                "death_overs": {
                    "runs": row.death_runs,
                    "balls": row.death_balls,
                    "wickets": row.death_wickets,
                    "dots": row.death_dots,
                    "boundaries": row.death_boundaries,
                    "strike_rate": float(row.death_strike_rate) if row.death_strike_rate else None
                },
                "team_comparison": {
                    "team_runs_excl_batter": row.team_runs_excl_batter,
                    "team_balls_excl_batter": row.team_balls_excl_batter,
                    "team_sr_excl_batter": float(row.team_sr_excl_batter) if row.team_sr_excl_batter else None,
                    "sr_diff": float(row.sr_diff) if row.sr_diff else None
                },
                "batting_position": row.batting_position,
                "entry_stats": {
                    "runs": row.entry_runs,
                    "balls": row.entry_balls,
                    "overs": float(row.entry_overs) if row.entry_overs else None
                },
                "match_info": {
                    "date": row.date.isoformat() if row.date else None,
                    "venue": row.venue,
                    "competition": row.competition
                }
            }
            batting_stats.append(stat_data)
        
        return batting_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team batting stats: {str(e)}")

def get_team_phase_stats_service(
    team_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    db
) -> dict:
    """
    Get aggregated phase-wise batting statistics for a team with proper benchmarking
    """
    try:
        team_variations = get_all_team_name_variations(team_name)
        
        # First, determine if this is an international team or league team
        from models import INTERNATIONAL_TEAMS_RANKED
        is_international_team = any(variation in INTERNATIONAL_TEAMS_RANKED for variation in team_variations)
        
        # Get team's phase stats
        team_phase_stats_query = text("""
            WITH team_phase_aggregates AS (
                SELECT 
                    COALESCE(SUM(bs.pp_runs), 0) as total_pp_runs,
                    COALESCE(SUM(bs.pp_balls), 0) as total_pp_balls,
                    COALESCE(SUM(bs.pp_wickets), 0) as total_pp_wickets,
                    COALESCE(SUM(bs.middle_runs), 0) as total_middle_runs,
                    COALESCE(SUM(bs.middle_balls), 0) as total_middle_balls,
                    COALESCE(SUM(bs.middle_wickets), 0) as total_middle_wickets,
                    COALESCE(SUM(bs.death_runs), 0) as total_death_runs,
                    COALESCE(SUM(bs.death_balls), 0) as total_death_balls,
                    COALESCE(SUM(bs.death_wickets), 0) as total_death_wickets,
                    COUNT(DISTINCT bs.match_id) as total_matches
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE bs.batting_team = ANY(:team_variations)
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
            )
            SELECT 
                total_pp_runs, total_pp_balls, total_pp_wickets,
                total_middle_runs, total_middle_balls, total_middle_wickets,
                total_death_runs, total_death_balls, total_death_wickets,
                total_matches,
                CASE WHEN total_pp_wickets > 0 THEN ROUND(total_pp_runs::numeric / total_pp_wickets, 2) ELSE NULL END as pp_average,
                CASE WHEN total_pp_balls > 0 THEN ROUND(total_pp_runs::numeric * 100 / total_pp_balls, 2) ELSE 0 END as pp_strike_rate,
                CASE WHEN total_middle_wickets > 0 THEN ROUND(total_middle_runs::numeric / total_middle_wickets, 2) ELSE NULL END as middle_average,
                CASE WHEN total_middle_balls > 0 THEN ROUND(total_middle_runs::numeric * 100 / total_middle_balls, 2) ELSE 0 END as middle_strike_rate,
                CASE WHEN total_death_wickets > 0 THEN ROUND(total_death_runs::numeric / total_death_wickets, 2) ELSE NULL END as death_average,
                CASE WHEN total_death_balls > 0 THEN ROUND(total_death_runs::numeric * 100 / total_death_balls, 2) ELSE 0 END as death_strike_rate
            FROM team_phase_aggregates
        """)
        
        team_result = db.execute(team_phase_stats_query, {
            "team_variations": team_variations,
            "start_date": start_date,
            "end_date": end_date
        }).fetchone()
        
        if not team_result or team_result.total_matches == 0:
            return {
                "powerplay": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "middle_overs": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "death_overs": {"runs": 0, "balls": 0, "wickets": 0, "average": 0, "strike_rate": 0, "normalized_average": 50, "normalized_strike_rate": 50},
                "total_matches": 0, "context": "No data", "benchmark_teams": 0
            }
        
        # Get benchmark data based on team type
        if is_international_team:
            context = "International Teams"
            benchmark_filter = "m.match_type = 'international'"
            league_param = None
        else:
            # Get the league from recent matches
            league_query = text("""
                SELECT DISTINCT m.competition
                FROM matches m
                INNER JOIN batting_stats bs ON m.id = bs.match_id
                WHERE bs.batting_team = ANY(:team_variations)
                AND m.match_type = 'league'
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                ORDER BY m.date DESC LIMIT 1
            """)
            
            league_result = db.execute(league_query, {
                "team_variations": team_variations,
                "start_date": start_date,
                "end_date": end_date
            }).fetchone()
            
            league_param = league_result.competition if league_result else None
            context = f"{league_param} Teams" if league_param else "League Teams"
            benchmark_filter = "m.match_type = 'league' AND (:league_param IS NULL OR m.competition = :league_param)"
        
        # Get benchmark statistics using a simpler approach
        benchmark_query = text(f"""
            WITH team_stats AS (
                SELECT 
                    bs.batting_team,
                    SUM(bs.pp_runs)::float / NULLIF(SUM(bs.pp_wickets), 0) as team_pp_avg,
                    SUM(bs.pp_runs)::float * 100 / NULLIF(SUM(bs.pp_balls), 0) as team_pp_sr,
                    SUM(bs.middle_runs)::float / NULLIF(SUM(bs.middle_wickets), 0) as team_middle_avg,
                    SUM(bs.middle_runs)::float * 100 / NULLIF(SUM(bs.middle_balls), 0) as team_middle_sr,
                    SUM(bs.death_runs)::float / NULLIF(SUM(bs.death_wickets), 0) as team_death_avg,
                    SUM(bs.death_runs)::float * 100 / NULLIF(SUM(bs.death_balls), 0) as team_death_sr
                FROM batting_stats bs
                INNER JOIN matches m ON bs.match_id = m.id
                WHERE {benchmark_filter}
                AND bs.batting_team != ANY(:team_variations)
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY bs.batting_team
                HAVING SUM(bs.pp_balls) > 0 AND SUM(bs.middle_balls) > 0 AND SUM(bs.death_balls) > 0
            )
            SELECT 
                COUNT(*) as benchmark_teams,
                AVG(team_pp_avg) as pp_avg_mean,
                STDDEV(team_pp_avg) as pp_avg_stddev,
                AVG(team_pp_sr) as pp_sr_mean,
                STDDEV(team_pp_sr) as pp_sr_stddev,
                AVG(team_middle_avg) as middle_avg_mean,
                STDDEV(team_middle_avg) as middle_avg_stddev,
                AVG(team_middle_sr) as middle_sr_mean,
                STDDEV(team_middle_sr) as middle_sr_stddev,
                AVG(team_death_avg) as death_avg_mean,
                STDDEV(team_death_avg) as death_avg_stddev,
                AVG(team_death_sr) as death_sr_mean,
                STDDEV(team_death_sr) as death_sr_stddev,
                -- Simple percentiles using array functions
                percentile_cont(0.25) within group (order by team_pp_avg) as pp_avg_p25,
                percentile_cont(0.50) within group (order by team_pp_avg) as pp_avg_p50,
                percentile_cont(0.75) within group (order by team_pp_avg) as pp_avg_p75,
                percentile_cont(0.25) within group (order by team_pp_sr) as pp_sr_p25,
                percentile_cont(0.50) within group (order by team_pp_sr) as pp_sr_p50,
                percentile_cont(0.75) within group (order by team_pp_sr) as pp_sr_p75,
                percentile_cont(0.25) within group (order by team_middle_avg) as middle_avg_p25,
                percentile_cont(0.50) within group (order by team_middle_avg) as middle_avg_p50,
                percentile_cont(0.75) within group (order by team_middle_avg) as middle_avg_p75,
                percentile_cont(0.25) within group (order by team_middle_sr) as middle_sr_p25,
                percentile_cont(0.50) within group (order by team_middle_sr) as middle_sr_p50,
                percentile_cont(0.75) within group (order by team_middle_sr) as middle_sr_p75,
                percentile_cont(0.25) within group (order by team_death_avg) as death_avg_p25,
                percentile_cont(0.50) within group (order by team_death_avg) as death_avg_p50,
                percentile_cont(0.75) within group (order by team_death_avg) as death_avg_p75,
                percentile_cont(0.25) within group (order by team_death_sr) as death_sr_p25,
                percentile_cont(0.50) within group (order by team_death_sr) as death_sr_p50,
                percentile_cont(0.75) within group (order by team_death_sr) as death_sr_p75
            FROM team_stats
        """)
        
        # Execute benchmark query with proper parameters
        benchmark_params = {
            "team_variations": team_variations,
            "start_date": start_date,
            "end_date": end_date
        }
        if not is_international_team:
            benchmark_params["league_param"] = league_param
            
        benchmark_result = db.execute(benchmark_query, benchmark_params).fetchone()
        
        # Function to calculate normalized percentile (0-100 scale)
        def calculate_percentile(value, p25, p50, p75):
            if value is None or p25 is None or p50 is None or p75 is None:
                return 50  # Default to median if no data
            
            # Handle edge cases
            if p25 == p50 == p75:  # All teams have same value
                return 50
            
            try:
                if value <= p25:
                    return max(0, 25 * (value / p25)) if p25 > 0 else 25
                elif value <= p50:
                    return 25 + 25 * ((value - p25) / (p50 - p25)) if p50 > p25 else 50
                elif value <= p75:
                    return 50 + 25 * ((value - p50) / (p75 - p50)) if p75 > p50 else 75
                else:
                    # For values above 75th percentile, scale up to 100
                    excess_ratio = (value - p75) / (p75 * 0.5) if p75 > 0 else 0
                    return min(100, 75 + 25 * excess_ratio)
            except (ZeroDivisionError, TypeError):
                return 50
        
        # Extract team stats
        team_pp_avg = float(team_result.pp_average) if team_result.pp_average else None
        team_pp_sr = float(team_result.pp_strike_rate) if team_result.pp_strike_rate else 0
        team_middle_avg = float(team_result.middle_average) if team_result.middle_average else None
        team_middle_sr = float(team_result.middle_strike_rate) if team_result.middle_strike_rate else 0
        team_death_avg = float(team_result.death_average) if team_result.death_average else None
        team_death_sr = float(team_result.death_strike_rate) if team_result.death_strike_rate else 0
        
        # Calculate normalized values if benchmark data exists
        if benchmark_result and benchmark_result.benchmark_teams > 2:  # Need at least 3 teams for percentiles
            pp_avg_norm = calculate_percentile(team_pp_avg, 
                float(benchmark_result.pp_avg_p25) if benchmark_result.pp_avg_p25 else None,
                float(benchmark_result.pp_avg_p50) if benchmark_result.pp_avg_p50 else None,
                float(benchmark_result.pp_avg_p75) if benchmark_result.pp_avg_p75 else None) if team_pp_avg else 50
            
            pp_sr_norm = calculate_percentile(team_pp_sr,
                float(benchmark_result.pp_sr_p25) if benchmark_result.pp_sr_p25 else None,
                float(benchmark_result.pp_sr_p50) if benchmark_result.pp_sr_p50 else None,
                float(benchmark_result.pp_sr_p75) if benchmark_result.pp_sr_p75 else None)
            
            middle_avg_norm = calculate_percentile(team_middle_avg,
                float(benchmark_result.middle_avg_p25) if benchmark_result.middle_avg_p25 else None,
                float(benchmark_result.middle_avg_p50) if benchmark_result.middle_avg_p50 else None,
                float(benchmark_result.middle_avg_p75) if benchmark_result.middle_avg_p75 else None) if team_middle_avg else 50
            
            middle_sr_norm = calculate_percentile(team_middle_sr,
                float(benchmark_result.middle_sr_p25) if benchmark_result.middle_sr_p25 else None,
                float(benchmark_result.middle_sr_p50) if benchmark_result.middle_sr_p50 else None,
                float(benchmark_result.middle_sr_p75) if benchmark_result.middle_sr_p75 else None)
            
            death_avg_norm = calculate_percentile(team_death_avg,
                float(benchmark_result.death_avg_p25) if benchmark_result.death_avg_p25 else None,
                float(benchmark_result.death_avg_p50) if benchmark_result.death_avg_p50 else None,
                float(benchmark_result.death_avg_p75) if benchmark_result.death_avg_p75 else None) if team_death_avg else 50
            
            death_sr_norm = calculate_percentile(team_death_sr,
                float(benchmark_result.death_sr_p25) if benchmark_result.death_sr_p25 else None,
                float(benchmark_result.death_sr_p50) if benchmark_result.death_sr_p50 else None,
                float(benchmark_result.death_sr_p75) if benchmark_result.death_sr_p75 else None)
        else:
            # Fallback to simple normalization if insufficient benchmark data
            def simple_normalize_avg(avg):
                if avg is None: return 50
                if avg <= 15: return 25
                elif avg <= 30: return 25 + (avg - 15) * 25 / 15
                elif avg <= 45: return 50 + (avg - 30) * 25 / 15
                else: return 75 + min(25, (avg - 45) * 25 / 15)
                
            def simple_normalize_sr(sr):
                if sr <= 100: return 25
                elif sr <= 130: return 25 + (sr - 100) * 25 / 30
                elif sr <= 160: return 50 + (sr - 130) * 25 / 30
                else: return 75 + min(25, (sr - 160) * 25 / 30)
            
            pp_avg_norm = simple_normalize_avg(team_pp_avg)
            pp_sr_norm = simple_normalize_sr(team_pp_sr)
            middle_avg_norm = simple_normalize_avg(team_middle_avg)
            middle_sr_norm = simple_normalize_sr(team_middle_sr)
            death_avg_norm = simple_normalize_avg(team_death_avg)
            death_sr_norm = simple_normalize_sr(team_death_sr)
            context += " (Insufficient benchmark data)"
        
        # Format response with both absolute and normalized values
        phase_stats = {
            "powerplay": {
                "runs": team_result.total_pp_runs or 0,
                "balls": team_result.total_pp_balls or 0,
                "wickets": team_result.total_pp_wickets or 0,
                "average": team_pp_avg or 0,
                "strike_rate": team_pp_sr,
                "normalized_average": round(pp_avg_norm, 1),
                "normalized_strike_rate": round(pp_sr_norm, 1)
            },
            "middle_overs": {
                "runs": team_result.total_middle_runs or 0,
                "balls": team_result.total_middle_balls or 0,
                "wickets": team_result.total_middle_wickets or 0,
                "average": team_middle_avg or 0,
                "strike_rate": team_middle_sr,
                "normalized_average": round(middle_avg_norm, 1),
                "normalized_strike_rate": round(middle_sr_norm, 1)
            },
            "death_overs": {
                "runs": team_result.total_death_runs or 0,
                "balls": team_result.total_death_balls or 0,
                "wickets": team_result.total_death_wickets or 0,
                "average": team_death_avg or 0,
                "strike_rate": team_death_sr,
                "normalized_average": round(death_avg_norm, 1),
                "normalized_strike_rate": round(death_sr_norm, 1)
            },
            "total_matches": team_result.total_matches or 0,
            "context": context,
            "benchmark_teams": benchmark_result.benchmark_teams if benchmark_result else 0
        }
        
        return phase_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching team phase stats: {str(e)}")
