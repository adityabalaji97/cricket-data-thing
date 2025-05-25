import os
from email.mime import base
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import date
from sqlalchemy import func, desc, and_, or_
from pydantic import BaseModel
from collections import defaultdict
from statistics import mean
from database import database, get_session
from models import Match, Delivery, Player, BattingStats, BowlingStats
# main.py (add to existing FastAPI app)
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import text
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
import logging
from models import teams_mapping
from typing import List, Dict, Optional
from datetime import date, datetime
from models import teams_mapping
from models import get_league_abbreviation, get_full_league_name, leagues_mapping, league_aliases
from sqlalchemy.sql import text
from routers.matchups import router as matchups_router
import math


# Helper function to expand league abbreviations
def expand_league_abbreviations(abbrevs: List[str]) -> List[str]:
    """Expand league abbreviations to include both the abbreviation and the full name."""
    expanded = []
    for abbrev in abbrevs:
        # First check if this is a full name with an abbreviation
        if abbrev in leagues_mapping:
            expanded.append(abbrev)  # Add the full name
            expanded.append(leagues_mapping[abbrev])  # Add the abbreviation
        # Then check if it's an abbreviation with a full name
        else:
            full_name = get_full_league_name(abbrev)
            if full_name != abbrev:  # If we found a mapping
                expanded.append(full_name)
                expanded.append(abbrev)
            else:
                expanded.append(abbrev)  # Include the original if no mapping found
        
        # Also check aliases (for renamed leagues)
        for alias, std_name in league_aliases.items():
            if abbrev == std_name or abbrev == alias:
                expanded.append(alias)
                expanded.append(std_name)
    
    # Remove duplicates while preserving order
    result = []
    for item in expanded:
        if item not in result:
            result.append(item)
    
    return result

logging.basicConfig(filename='venue_stats.log', level=logging.INFO)

from fastapi.responses import JSONResponse

app = FastAPI(title="Cricket Stats API")
app.include_router(matchups_router)

# Get CORS origins from environment variable or use defaults
cors_origins_env = os.getenv('CORS_ORIGINS', '')
if cors_origins_env:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(',')]
else:
    cors_origins = [
        "http://localhost:3000", 
        "https://cricket-data-thing.vercel.app",
        "https://hindsight2020.vercel.app"
    ]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add a database connection error handling middleware
@app.middleware("http")
async def db_error_middleware(request, call_next):
    try:
        # Process the request
        response = await call_next(request)
        return response
    except Exception as e:
        # Log the error
        logging.error(f"Error during request: {str(e)}")
        
        # Return a proper error response
        status_code = 500
        error_detail = "Internal server error"
        
        if "too many connections" in str(e).lower():
            status_code = 503  # Service Unavailable
            error_detail = "Database connection limit reached. Please try again later."
        
        return JSONResponse(
            status_code=status_code,
            content={"detail": error_detail}
        )@app.on_event("startup")
def startup():
    from database import init_db
    # Initialize database tables
    init_db()
    logging.info("Database tables initialized")



@app.get("/")
def read_root():
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    response = {
        "message": "Welcome to the Cricket Data Thing API", 
        "documentation": "/docs",
        "version": "1.0"
    }
    
    if debug_mode:
        cors_origins_env = os.getenv('CORS_ORIGINS', '')
        response["debug"] = {
            "cors_origins_env": cors_origins_env,
            "cors_origins_parsed": [origin.strip() for origin in cors_origins_env.split(',')] if cors_origins_env else [],
            "environment": "heroku" if os.getenv('DYNO') else "local"
        }
    
    return response

# Modified simple competitions endpoint using direct SQLAlchemy
@app.get("/competitions")
def get_competitions(db: Session = Depends(get_session)):
    try:
        # Use SQLAlchemy directly with simple queries
        query = text("""
            SELECT DISTINCT 
                competition,
                match_type,
                COUNT(*) as match_count,
                MIN(date)::text as start_date,
                MAX(date)::text as end_date
            FROM matches 
            WHERE competition IS NOT NULL 
            GROUP BY competition, match_type
            ORDER BY match_type, competition
        """)
        
        result = db.execute(query).fetchall()
        
        # Create a mapping of standard competition names to their info
        # This helps deduplicate entries like 'IPL' and 'Indian Premier League'
        standardized_leagues = {}
        
        for row in result:
            if row.match_type != 'league':
                continue
                
            # Get standardized competition name
            competition_name = row.competition
            
            # First check if it's an alias with a standard name (handle renamed leagues)
            if competition_name in league_aliases:
                std_name = league_aliases[competition_name]
            else:
                # Check if it's an abbreviation with a full name mapping
                full_name = get_full_league_name(competition_name)
                if full_name != competition_name:  # It's an abbreviation
                    std_name = full_name
                # Check if it's a full name with an abbreviation
                elif competition_name in leagues_mapping:  # It's a full name
                    std_name = competition_name  # Keep using the full name as standard
                else:
                    std_name = competition_name  # Use as is
            
            # Create/update the league entry
            if std_name not in standardized_leagues:
                standardized_leagues[std_name] = {
                    "value": std_name,
                    "label": std_name,
                    "match_count": row.match_count,
                    "date_range": f"{row.start_date} to {row.end_date}"
                }
            else:
                # Update the match count and date range if this is an additional record for the same league
                existing = standardized_leagues[std_name]
                existing["match_count"] += row.match_count
                
                # Update date range if needed
                current_start, current_end = existing["date_range"].split(" to ")
                if row.start_date < current_start:
                    current_start = row.start_date
                if row.end_date > current_end:
                    current_end = row.end_date
                existing["date_range"] = f"{current_start} to {current_end}"
        
        # Convert the mapping to a list for the response
        leagues = list(standardized_leagues.values())
        
        return {"leagues": leagues}
    except Exception as e:
        logging.error(f"Error in get_competitions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_innings_total(deliveries, match_id, innings):
    innings_deliveries = [
        d for d in deliveries 
        if d.match_id == match_id and d.innings == innings
    ]
    return sum(d.runs_off_bat + d.extras for d in innings_deliveries)

def get_phase_stats(deliveries, match_ids, innings):
    if not match_ids:  # Return empty default stats if no matches
        return {
            phase_name: {
                "total_runs": 0,
                "total_balls": 0,
                "total_wickets": 0,
                "batting_strike_rate": 0,
                "batting_average": 0,
                "bowling_strike_rate": 0,
                "boundary_percentage": 0,
                "dot_percentage": 0,
                "score": "0-0 (0)"
            }
            for phase_name in ["powerplay", "middle1", "middle2", "death"]
        }

    phases = [
        (0, 6, "powerplay"),
        (6, 10, "middle1"),
        (10, 15, "middle2"),
        (15, 20, "death")
    ]
    
    phase_stats = {}
    for start, end, phase_name in phases:
        start_ball = start * 6
        end_ball = end * 6
        
        phase_deliveries = [
            d for d in deliveries 
            if d.match_id in match_ids 
            and d.innings == innings 
            and (start <= (d.over) < end)
        ]
        
        total_balls = len(phase_deliveries)
        total_runs = sum(d.runs_off_bat + d.extras for d in phase_deliveries)
        total_wickets = len([d for d in phase_deliveries if d.wicket_type])
        total_boundaries = len([d for d in phase_deliveries if d.runs_off_bat in [4, 6]])
        total_dots = len([d for d in phase_deliveries if d.runs_off_bat == 0 and d.extras == 0])
        
        phase_stats[phase_name] = {
            "total_runs": total_runs,
            "total_balls": total_balls,
            "total_wickets": total_wickets,
            "batting_strike_rate": (total_runs * 100) / total_balls if total_balls > 0 else 0,
            "batting_average": total_runs / total_wickets if total_wickets > 0 else 0,  # Changed from float('inf') to 0
            "bowling_strike_rate": total_balls / total_wickets if total_wickets > 0 else 0,  # Changed from float('inf') to 0
            "boundary_percentage": (total_boundaries * 100) / total_balls if total_balls > 0 else 0,
            "dot_percentage": (total_dots * 100) / total_balls if total_balls > 0 else 0,
            "score": f"{total_runs}-{total_wickets} ({total_balls})"
        }
    
    return phase_stats

INTERNATIONAL_TEAMS_RANKED = [
    'India', 'Australia', 'England', 'West Indies', 'New Zealand',
    'South Africa', 'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan',
    'Ireland', 'Zimbabwe', 'Scotland', 'Netherlands', 'Namibia',
    'UAE', 'Nepal', 'USA', 'Oman', 'Papua New Guinea'
]

@app.get("/venue_notes/{venue}")
def get_venue_notes(
    venue: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),  # Change default to empty list
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    db: Session = Depends(get_session)
):
    try:
        # Log incoming parameters
        logging.info(f"Incoming request parameters:")
        logging.info(f"Leagues: {leagues}")
        logging.info(f"Venue: {venue}")
        logging.info(f"Date range: {start_date} to {end_date}")
        logging.info(f"Include international: {include_international}")
        logging.info(f"Top teams: {top_teams}")

        competition_conditions = []
        params = {
            "venue": venue if venue != "All Venues" else None,
            "start_date": start_date,
            "end_date": end_date,
            "leagues": leagues
        }
        
        # Handle league matches
        if leagues and len(leagues) > 0:
            # Expand league abbreviations to include full names
            expanded_leagues = expand_league_abbreviations(leagues)
            params["leagues"] = expanded_leagues
            logging.info(f"Expanded leagues: {leagues} -> {expanded_leagues}")
            competition_conditions.append("""
                (m.match_type = 'league' AND m.competition = ANY(:leagues))
            """)
        
        # Handle international matches with top teams
        if include_international:
            if top_teams:
                top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
                params["top_team_list"] = top_team_list
                competition_conditions.append("""
                    (m.match_type = 'international' 
                     AND (m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list)))
                """)
            else:
                competition_conditions.append("(m.match_type = 'international')")
        
        # Combine conditions
        if competition_conditions:
            competition_filter = "AND (" + " OR ".join(competition_conditions) + ")"
        else:
            competition_filter = "AND false"

        logging.info(f"Competition filter: {competition_filter}")
        logging.info(f"Params: {params}")

        # Add some debug logging
        logging.info(f"Final competition filter: {competition_filter}")
        logging.info(f"Final params: {params}")

        # Get basic match stats
        matches_query = """
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
                SUM(CASE WHEN fm.won_batting_first THEN 1 ELSE 0 END) as batting_first_wins,
                SUM(CASE WHEN fm.won_fielding_first THEN 1 ELSE 0 END) as batting_second_wins,
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
        """.format(
            venue_filter="AND m.venue = :venue" if venue != "All Venues" else "",
            competition_filter=competition_filter
        )

        # Updated phase stats query with competition filter
        phase_query = """
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
        """.format(
            venue_filter="AND m.venue = :venue" if venue != "All Venues" else "",
            competition_filter=competition_filter
        )

        # Log the queries for debugging
        logging.info(f"Executing queries with parameters: {params}")

        matches_query = text(matches_query)
        phase_query = text(phase_query)
        
        # Execute queries
        match_stats = db.execute(matches_query, params).fetchone()
        phase_stats = db.execute(phase_query, params).fetchall()

        if not match_stats:
            return {
                "venue": venue,
                "total_matches": 0,
                "batting_first_wins": 0,
                "batting_second_wins": 0,
                "highest_total": 0,
                "lowest_total": 0,
                "average_first_innings": 0,
                "average_second_innings": 0,
                "highest_total_chased": 0,
                "lowest_total_defended": 0,
                "average_winning_score": 0,
                "average_chasing_score": 0,
                "phase_wise_stats": {
                    "batting_first_wins": {},
                    "chasing_wins": {}
                }
            }

        # Process phase stats into required format
        phase_wise_stats = {
            'batting_first_wins': {},
            'chasing_wins': {}
        }

        for stat in phase_stats:
            batting_first_stats = {
                'runs_per_innings': float(stat.batting_first_runs or 0),
                'wickets_per_innings': float(stat.batting_first_wickets or 0),
                'balls_per_innings': float(stat.batting_first_balls or 0)
            }
            
            chasing_stats = {
                'runs_per_innings': float(stat.chasing_runs or 0),
                'wickets_per_innings': float(stat.chasing_wickets or 0),
                'balls_per_innings': float(stat.chasing_balls or 0)
            }
            
            if stat.innings == 1:
                phase_wise_stats['batting_first_wins'][stat.phase] = batting_first_stats
                phase_wise_stats['chasing_wins'][stat.phase] = chasing_stats

        return {
            "venue": venue,
            "total_matches": match_stats.total_matches or 0,
            "batting_first_wins": match_stats.batting_first_wins or 0,
            "batting_second_wins": match_stats.batting_second_wins or 0,
            "highest_total": match_stats.highest_total or 0,
            "lowest_total": match_stats.lowest_total or 0,
            "average_first_innings": float(match_stats.average_first_innings or 0),
            "average_second_innings": float(match_stats.average_second_innings or 0),
            "highest_total_chased": match_stats.highest_total_chased or 0,
            "lowest_total_defended": match_stats.lowest_total_defended or 0,
            "average_winning_score": float(match_stats.average_winning_score or 0),
            "average_chasing_score": float(match_stats.average_chasing_score or 0),
            "phase_wise_stats": phase_wise_stats
        }

    except Exception as e:
        logging.error(f"Error in get_venue_notes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Request models
class PlayerInningsBase(BaseModel):
    match_id: str
    date: date
    venue: str
    batting_team: str
    bowling_team: str
    runs: int = 0
    balls_faced: int = 0
    strike_rate: Optional[float] = 0.0
    fours: Optional[int] = 0
    sixes: Optional[int] = 0
    batting_position: Optional[int] = None
    
    # Phase-wise stats
    pp_runs: Optional[int] = 0
    pp_balls: Optional[int] = 0
    pp_strike_rate: Optional[float] = 0.0
    middle_runs: Optional[int] = 0
    middle_balls: Optional[int] = 0
    middle_strike_rate: Optional[float] = 0.0
    death_runs: Optional[int] = 0
    death_balls: Optional[int] = 0
    death_strike_rate: Optional[float] = 0.0
    
    class Config:
        orm_mode = True
        allow_none = True  # Allow null values

class PlayerBowlingInningsBase(BaseModel):
    match_id: str
    date: date
    venue: str
    bowling_team: str
    batting_team: str
    overs: float = 0.0
    runs_conceded: int = 0
    wickets: int = 0
    economy: Optional[float] = 0.0
    dots: Optional[int] = 0
    fours_conceded: Optional[int] = 0
    sixes_conceded: Optional[int] = 0
    
    # Phase-wise stats
    pp_overs: Optional[float] = 0.0
    pp_runs: Optional[int] = 0
    pp_wickets: Optional[int] = 0
    pp_economy: Optional[float] = 0.0
    middle_overs: Optional[float] = 0.0
    middle_runs: Optional[int] = 0
    middle_wickets: Optional[int] = 0
    middle_economy: Optional[float] = 0.0
    death_overs: Optional[float] = 0.0
    death_runs: Optional[int] = 0
    death_wickets: Optional[int] = 0
    death_economy: Optional[float] = 0.0
    
    class Config:
        orm_mode = True
        allow_none = True  # Allow null values

@app.get("/player/{player_name}/batting", response_model=List[PlayerInningsBase])
def get_player_batting_innings(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    tournament: Optional[str] = None,
    venue: Optional[str] = None,
    min_runs: Optional[int] = None,
    max_runs: Optional[int] = None,
    db: Session = Depends(get_session)
):
    """Get batting innings for a player with optional filters"""
    try:
        print(f"Fetching batting innings for player: {player_name}")
        
        # First verify if the player exists
        player_exists = db.query(BattingStats).filter(BattingStats.striker == player_name).first()
        if not player_exists:
            raise HTTPException(status_code=404, detail=f"No batting innings found for player {player_name}")
        
        # Build the query
        query = (
            db.query(BattingStats, Match)
            .join(Match, BattingStats.match_id == Match.id)
            .filter(BattingStats.striker == player_name)
        )
        
        # Log the SQL query
        print(f"SQL Query: {query}")
        
        # Apply filters
        if start_date:
            query = query.filter(Match.date >= start_date)
        if end_date:
            query = query.filter(Match.date <= end_date)
        if tournament:
            query = query.filter(Match.event_name == tournament)
        if venue:
            query = query.filter(Match.venue == venue)
        if min_runs:
            query = query.filter(BattingStats.runs >= min_runs)
        if max_runs:
            query = query.filter(BattingStats.runs <= max_runs)
            
        # Order by date descending
        query = query.order_by(desc(Match.date))
        
        print("Executing query...")
        results = query.all()
        print(f"Found {len(results)} innings")
        
        if not results:
            raise HTTPException(status_code=404, detail=f"No innings found for player {player_name} with given filters")
            
        innings_list = []
        for batting_stats, match in results:
            try:
                innings = {
                    "match_id": match.id,
                    "date": match.date,
                    "venue": match.venue,
                    "batting_team": batting_stats.batting_team,
                    "bowling_team": match.team2 if match.team1 == batting_stats.batting_team else match.team1,
                    "runs": batting_stats.runs,
                    "balls_faced": batting_stats.balls_faced,
                    "strike_rate": batting_stats.strike_rate,
                    "fours": batting_stats.fours,
                    "sixes": batting_stats.sixes,
                    "batting_position": batting_stats.batting_position,
                    "pp_runs": batting_stats.pp_runs,
                    "pp_balls": batting_stats.pp_balls,
                    "pp_strike_rate": batting_stats.pp_strike_rate,
                    "middle_runs": batting_stats.middle_runs,
                    "middle_balls": batting_stats.middle_balls,
                    "middle_strike_rate": batting_stats.middle_strike_rate,
                    "death_runs": batting_stats.death_runs,
                    "death_balls": batting_stats.death_balls,
                    "death_strike_rate": batting_stats.death_strike_rate
                }
                innings_list.append(innings)
            except Exception as e:
                print(f"Error processing innings: {str(e)}")
                print(f"Batting stats: {batting_stats.__dict__}")
                print(f"Match: {match.__dict__}")
                continue
        
        return innings_list
        
    except Exception as e:
        print(f"Error in get_player_batting_innings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/player/{player_name}/bowling", response_model=List[PlayerBowlingInningsBase])
def get_player_bowling_innings(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    tournament: Optional[str] = None,
    venue: Optional[str] = None,
    min_wickets: Optional[int] = None,
    max_economy: Optional[float] = None,
    db: Session = Depends(get_session)
):
    """Get bowling innings for a player with optional filters"""
    query = (
        db.query(BowlingStats, Match)
        .join(Match, BowlingStats.match_id == Match.id)
        .filter(BowlingStats.bowler == player_name)
    )
    
    # Apply filters
    if start_date:
        query = query.filter(Match.date >= start_date)
    if end_date:
        query = query.filter(Match.date <= end_date)
    if tournament:
        query = query.filter(Match.event_name == tournament)
    if venue:
        query = query.filter(Match.venue == venue)
    if min_wickets:
        query = query.filter(BowlingStats.wickets >= min_wickets)
    if max_economy:
        query = query.filter(BowlingStats.economy <= max_economy)
        
    # Order by date descending
    query = query.order_by(desc(Match.date))
    
    results = query.all()
    
    if not results:
        raise HTTPException(status_code=404, detail="No innings found for the player")
        
    innings_list = []
    for bowling_stats, match in results:
        innings = {
            "match_id": match.id,
            "date": match.date,
            "venue": match.venue,
            "bowling_team": bowling_stats.bowling_team,
            "batting_team": match.team1 if match.team1 != bowling_stats.bowling_team else match.team2,
            "overs": bowling_stats.overs,
            "runs_conceded": bowling_stats.runs_conceded,
            "wickets": bowling_stats.wickets,
            "economy": bowling_stats.economy,
            "dots": bowling_stats.dots,
            "fours_conceded": bowling_stats.fours_conceded,
            "sixes_conceded": bowling_stats.sixes_conceded,
            "pp_overs": bowling_stats.pp_overs,
            "pp_runs": bowling_stats.pp_runs,
            "pp_wickets": bowling_stats.pp_wickets,
            "pp_economy": bowling_stats.pp_economy,
            "middle_overs": bowling_stats.middle_overs,
            "middle_runs": bowling_stats.middle_runs,
            "middle_wickets": bowling_stats.middle_wickets,
            "middle_economy": bowling_stats.middle_economy,
            "death_overs": bowling_stats.death_overs,
            "death_runs": bowling_stats.death_runs,
            "death_wickets": bowling_stats.death_wickets,
            "death_economy": bowling_stats.death_economy
        }
        innings_list.append(innings)
    
    return innings_list

@app.get("/players")
def get_players(db: Session = Depends(get_session)):
    """Get list of all players who have either batting or bowling stats"""
    batters = db.query(BattingStats.striker).distinct().all()
    bowlers = db.query(BowlingStats.bowler).distinct().all()
    
    players = set([b[0] for b in batters] + [bo[0] for bo in bowlers])
    return sorted(list(players))

@app.get("/venues")
def get_venues(db: Session = Depends(get_session)):
    """Get list of all venues"""
    venues = db.query(Match.venue).distinct().all()
    return [venue[0] for venue in venues if venue[0]]

@app.get("/tournaments")
def get_tournaments(db: Session = Depends(get_session)):
    """Get list of all tournaments"""
    tournaments = db.query(Match.event_name).distinct().all()
    return [t[0] for t in tournaments if t[0]]

def get_batting_zone(avg: float, sr: float, avg_batter_avg: float, avg_batter_sr: float) -> str:
    if avg > avg_batter_avg and sr > avg_batter_sr:
        return "dominator"
    elif avg > avg_batter_avg:
        return "accumulator"
    elif sr > avg_batter_sr:
        return "aggressor" 
    else:
        return "below_average"

@app.get("/venues/{venue}/stats")
def get_venue_stats(
    venue: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    db: Session = Depends(get_session)
):
    try:
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "leagues": leagues,
            "full_names": list(teams_mapping.keys()),
            "abbrev_names": list(teams_mapping.values())
        }

        if venue != "All Venues":
            params["venue"] = venue

        competition_conditions = []
        if leagues:
            # Expand league abbreviations to include full names
            params["leagues"] = expand_league_abbreviations(leagues)
            competition_conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
            
        if include_international:
            if top_teams:
                params["top_team_list"] = INTERNATIONAL_TEAMS_RANKED[:top_teams]
                competition_conditions.append(
                    "(m.match_type = 'international' AND m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list))"
                )
            else:
                competition_conditions.append("(m.match_type = 'international')")
                
        competition_filter = " AND (" + " OR ".join(competition_conditions) + ")" if competition_conditions else " AND false"
        venue_filter = "AND m.venue = :venue" if venue != "All Venues" else ""

        # Modified team mapping part of the query
        team_mapping_cte = f"""
        WITH team_mapping AS (
            SELECT *
            FROM (VALUES {','.join(f"('{k}', '{v}')" for k, v in teams_mapping.items())})
            AS t(full_name, abbreviated_name)
        )"""

        # Batting Query
        batting_query = text("""
            WITH team_mapping AS (
                SELECT unnest(:full_names) as full_name,
                    unnest(:abbrev_names) as abbreviated_name
            ),
            match_filter AS (
                SELECT m.id
                FROM matches m
                WHERE 1=1
                    {venue_filter}
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    {competition_filter}
            )
            SELECT 
                bs.striker as name,
                string_agg(DISTINCT COALESCE(tm.abbreviated_name, bs.batting_team), '/') as batting_team,
                COUNT(DISTINCT bs.match_id) as innings,
                SUM(bs.runs) as total_runs,
                CAST(SUM(bs.runs)::float / NULLIF(COUNT(CASE WHEN bs.wickets > 0 THEN 1 END), 0) AS DECIMAL(10,2)) as average,
                CAST((SUM(bs.runs)::float * 100 / NULLIF(SUM(bs.balls_faced), 0)) AS DECIMAL(10,2)) as strike_rate,
                CAST(SUM(bs.balls_faced)::float / NULLIF(COUNT(CASE WHEN bs.wickets > 0 THEN 1 END), 0) AS DECIMAL(10,2)) as balls_per_dismissal
            FROM batting_stats bs
            JOIN match_filter mf ON bs.match_id = mf.id
            JOIN matches m ON bs.match_id = m.id
            LEFT JOIN team_mapping tm ON bs.batting_team = tm.full_name
            GROUP BY bs.striker
            HAVING SUM(bs.balls_faced) >= 0
            ORDER BY total_runs DESC
            LIMIT 10
        """.format(venue_filter=venue_filter, competition_filter=competition_filter))

        # Bowling Query
        bowling_query = text("""
            WITH team_mapping AS (
                SELECT unnest(:full_names) as full_name,
                    unnest(:abbrev_names) as abbreviated_name
            ),
            match_filter AS (
                SELECT m.id
                FROM matches m
                WHERE 1=1
                    {venue_filter}
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    {competition_filter}
            )
            SELECT
                bw.bowler as name,
                string_agg(DISTINCT COALESCE(tm.abbreviated_name, bw.bowling_team), '/') as bowling_team,
                COUNT(DISTINCT bw.match_id) as innings,
                SUM(bw.wickets) as total_wickets,
                CAST((SUM(CAST(bw.overs AS float)) * 6 / NULLIF(SUM(bw.wickets)::float, 0)) AS DECIMAL(10,2)) as strike_rate,
                CAST((SUM(bw.runs_conceded)::float / NULLIF(SUM(bw.wickets), 0)) AS DECIMAL(10,2)) as average,
                CAST((SUM(bw.runs_conceded)::float / NULLIF(SUM(CAST(bw.overs AS float)), 0)) AS DECIMAL(10,2)) as economy
            FROM bowling_stats bw
            JOIN match_filter mf ON bw.match_id = mf.id
            JOIN matches m ON bw.match_id = m.id
            LEFT JOIN team_mapping tm ON bw.bowling_team = tm.full_name
            GROUP BY bw.bowler
            HAVING SUM(CAST(bw.overs AS float)) >= 0
            ORDER BY total_wickets DESC
            LIMIT 10
        """.format(venue_filter=venue_filter, competition_filter=competition_filter))

        batting_leaders = db.execute(batting_query, params).fetchall()
        bowling_leaders = db.execute(bowling_query, params).fetchall()

        # Format the data as dictionaries
        batting_formatted = [
            {
                "name": row[0],
                "batting_team": row[1],
                "batInns": row[2],
                "batRuns": row[3],
                "batAvg": float(row[4]) if row[4] is not None else 0,
                "batSR": float(row[5]) if row[5] is not None else 0,
                "batBPD": float(row[6]) if row[6] is not None else 0
            }
            for row in batting_leaders
        ]

        bowling_formatted = [
            {
                "name": row[0],
                "bowling_team": row[1],
                "bowlInns": row[2],
                "bowlWickets": row[3],
                "bowlBPD": float(row[4]) if row[4] is not None else 0,
                "bowlAvg": float(row[5]) if row[5] is not None else 0,
                "bowlER": float(row[6]) if row[6] is not None else 0
            }
            for row in bowling_leaders
        ]

        # Get all batters stats for scatter plot with most recent team
        scatter_query = text("""
            WITH team_mapping AS (
                SELECT unnest(:full_names) as full_name,
                    unnest(:abbrev_names) as abbreviated_name
            ),
            match_filter AS (
                SELECT m.id
                FROM matches m
                WHERE 1=1
                    {venue_filter}
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    {competition_filter}
            ),
            batter_stats AS (
                SELECT 
                    bs.striker,
                    COUNT(DISTINCT bs.match_id) as innings,
                    SUM(bs.runs) as runs,
                    SUM(bs.wickets) as wickets,
                    SUM(bs.balls_faced) as balls,
                    SUM(bs.dots) as dots,
                    SUM(bs.fours + bs.sixes) as boundaries,
                    SUM(bs.pp_runs) as pp_runs,
                    SUM(bs.pp_wickets) as pp_wickets,
                    SUM(bs.pp_balls) as pp_balls,
                    SUM(bs.pp_dots) as pp_dots,
                    SUM(bs.pp_boundaries) as pp_boundaries,
                    COUNT(DISTINCT CASE WHEN bs.pp_balls > 0 THEN bs.match_id END) as pp_innings,
                    SUM(bs.middle_runs) as middle_runs,
                    SUM(bs.middle_wickets) as middle_wickets,
                    SUM(bs.middle_balls) as middle_balls,
                    SUM(bs.middle_dots) as middle_dots,
                    SUM(bs.middle_boundaries) as middle_boundaries,
                    COUNT(DISTINCT CASE WHEN bs.middle_balls > 0 THEN bs.match_id END) as middle_innings,
                    SUM(bs.death_runs) as death_runs,
                    SUM(bs.death_wickets) as death_wickets,
                    SUM(bs.death_balls) as death_balls,
                    SUM(bs.death_dots) as death_dots,
                    SUM(bs.death_boundaries) as death_boundaries,
                    COUNT(DISTINCT CASE WHEN bs.death_balls > 0 THEN bs.match_id END) as death_innings,
                    CAST(SUM(bs.balls_faced)::float / COUNT(DISTINCT bs.match_id) AS DECIMAL(10,2)) as bpi
                FROM batting_stats bs
                JOIN match_filter mf ON bs.match_id = mf.id
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.batting_team != bs.striker
                GROUP BY bs.striker
                HAVING COUNT(DISTINCT bs.match_id) >= 1
            ),
            latest_teams AS (
                SELECT DISTINCT ON (bs.striker)
                    bs.striker,
                    COALESCE(tm.abbreviated_name, bs.batting_team) as team,
                    m.date
                FROM batting_stats bs
                JOIN match_filter mf ON bs.match_id = mf.id
                JOIN matches m ON bs.match_id = m.id
                LEFT JOIN team_mapping tm ON bs.batting_team = tm.full_name
                WHERE bs.batting_team != bs.striker
                ORDER BY bs.striker, m.date DESC
            ),
            avg_stats AS (
                SELECT 
                    'Average Batter' as name,
                    'Overall' as team,
                    COUNT(DISTINCT bs.match_id) as innings,
                    SUM(bs.runs) as runs,
                    SUM(bs.wickets) as wickets,
                    SUM(bs.balls_faced) as balls,
                    SUM(bs.dots) as dots,
                    SUM(bs.fours + bs.sixes) as boundaries,
                    SUM(bs.pp_runs) as pp_runs,
                    SUM(bs.pp_wickets) as pp_wickets,
                    SUM(bs.pp_balls) as pp_balls,
                    SUM(bs.pp_dots) as pp_dots,
                    SUM(bs.pp_boundaries) as pp_boundaries,
                    COUNT(DISTINCT CASE WHEN bs.pp_balls > 0 THEN bs.match_id END) as pp_innings,
                    SUM(bs.middle_runs) as middle_runs,
                    SUM(bs.middle_wickets) as middle_wickets,
                    SUM(bs.middle_balls) as middle_balls,
                    SUM(bs.middle_dots) as middle_dots,
                    SUM(bs.middle_boundaries) as middle_boundaries,
                    COUNT(DISTINCT CASE WHEN bs.middle_balls > 0 THEN bs.match_id END) as middle_innings,
                    SUM(bs.death_runs) as death_runs,
                    SUM(bs.death_wickets) as death_wickets,
                    SUM(bs.death_balls) as death_balls,
                    SUM(bs.death_dots) as death_dots,
                    SUM(bs.death_boundaries) as death_boundaries,
                    COUNT(DISTINCT CASE WHEN bs.death_balls > 0 THEN bs.match_id END) as death_innings
                FROM batting_stats bs
                JOIN match_filter mf ON bs.match_id = mf.id
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.batting_team != bs.striker
            )
            SELECT 
                bs.striker as name,
                lt.team as batting_team,
                bs.innings,
                bs.runs as total_runs,
                CAST(bs.runs::float / NULLIF(bs.wickets, 0) AS DECIMAL(10,2)) as avg,
                CAST((bs.runs::float * 100 / NULLIF(bs.balls, 0)) AS DECIMAL(10,2)) as sr,
                CAST(bs.dots::float * 100 / NULLIF(bs.balls, 0) AS DECIMAL(10,2)) as dot_percent,
                CAST(bs.boundaries::float * 100 / NULLIF(bs.balls, 0) AS DECIMAL(10,2)) as boundary_percent,
                bs.pp_innings,
                bs.pp_runs,
                bs.pp_balls,
                CAST(bs.pp_runs::float / NULLIF(bs.pp_wickets, 0) AS DECIMAL(10,2)) as pp_avg,
                CAST((bs.pp_runs::float * 100 / NULLIF(bs.pp_balls, 0)) AS DECIMAL(10,2)) as pp_sr,
                CAST(bs.pp_dots::float * 100 / NULLIF(bs.pp_balls, 0) AS DECIMAL(10,2)) as pp_dot_percent,
                CAST(bs.pp_boundaries::float * 100 / NULLIF(bs.pp_balls, 0) AS DECIMAL(10,2)) as pp_boundary_percent,
                bs.middle_innings,
                bs.middle_runs,
                bs.middle_balls,
                CAST(bs.middle_runs::float / NULLIF(bs.middle_wickets, 0) AS DECIMAL(10,2)) as middle_avg,
                CAST((bs.middle_runs::float * 100 / NULLIF(bs.middle_balls, 0)) AS DECIMAL(10,2)) as middle_sr,
                CAST(bs.middle_dots::float * 100 / NULLIF(bs.middle_balls, 0) AS DECIMAL(10,2)) as middle_dot_percent,
                CAST(bs.middle_boundaries::float * 100 / NULLIF(bs.middle_balls, 0) AS DECIMAL(10,2)) as middle_boundary_percent,
                bs.death_innings,
                bs.death_runs,
                bs.death_balls,
                CAST(bs.death_runs::float / NULLIF(bs.death_wickets, 0) AS DECIMAL(10,2)) as death_avg,
                CAST((bs.death_runs::float * 100 / NULLIF(bs.death_balls, 0)) AS DECIMAL(10,2)) as death_sr,
                CAST(bs.death_dots::float * 100 / NULLIF(bs.death_balls, 0) AS DECIMAL(10,2)) as death_dot_percent,
                CAST(bs.death_boundaries::float * 100 / NULLIF(bs.death_balls, 0) AS DECIMAL(10,2)) as death_boundary_percent,
                bs.bpi as balls_per_innings
            FROM batter_stats bs
            JOIN latest_teams lt ON bs.striker = lt.striker
            UNION ALL
            SELECT 
                'Average Batter' as name,
                'Overall' as team,
                innings,
                runs as total_runs,
                CAST(runs::float / NULLIF(wickets, 0) AS DECIMAL(10,2)) as avg,
                CAST((runs::float * 100 / balls) AS DECIMAL(10,2)) as sr,
                CAST(dots::float * 100 / balls AS DECIMAL(10,2)) as dot_percent,
                CAST(boundaries::float * 100 / balls AS DECIMAL(10,2)) as boundary_percent,
                pp_innings,
                pp_runs,
                pp_balls,
                CAST(pp_runs::float / NULLIF(pp_wickets, 0) AS DECIMAL(10,2)) as pp_avg,
                CAST((pp_runs::float * 100 / NULLIF(pp_balls, 0)) AS DECIMAL(10,2)) as pp_sr,
                CAST(pp_dots::float * 100 / NULLIF(pp_balls, 0) AS DECIMAL(10,2)) as pp_dot_percent,
                CAST(pp_boundaries::float * 100 / NULLIF(pp_balls, 0) AS DECIMAL(10,2)) as pp_boundary_percent,
                middle_innings,
                middle_runs,
                middle_balls,
                CAST(middle_runs::float / NULLIF(middle_wickets, 0) AS DECIMAL(10,2)) as middle_avg, 
                CAST((middle_runs::float * 100 / NULLIF(middle_balls, 0)) AS DECIMAL(10,2)) as middle_sr,
                CAST(middle_dots::float * 100 / NULLIF(middle_balls, 0) AS DECIMAL(10,2)) as middle_dot_percent,
                CAST(middle_boundaries::float * 100 / NULLIF(middle_balls, 0) AS DECIMAL(10,2)) as middle_boundary_percent,
                death_innings,
                death_runs,
                death_balls,
                CAST(death_runs::float / NULLIF(death_wickets, 0) AS DECIMAL(10,2)) as death_avg,
                CAST((death_runs::float * 100 / NULLIF(death_balls, 0)) AS DECIMAL(10,2)) as death_sr,
                CAST(death_dots::float * 100 / NULLIF(death_balls, 0) AS DECIMAL(10,2)) as death_dot_percent,
                CAST(death_boundaries::float * 100 / NULLIF(death_balls, 0) AS DECIMAL(10,2)) as death_boundary_percent,
                CAST(balls::float / innings AS DECIMAL(10,2)) as balls_per_innings
            FROM avg_stats
            ORDER BY total_runs DESC
        """.format(venue_filter=venue_filter, competition_filter=competition_filter))

        # Execute scatter plot query
        scatter_data = db.execute(scatter_query, params).fetchall()

        # Get average batter (will be the last row since ordering by runs)
        avg_batter = next((row for row in scatter_data if row[0] == 'Average Batter'), None)

        # Format scatter plot data
        scatter_formatted = [
            {
                "name": row[0],
                "batting_team": row[1],
                "innings": row[2],
                "total_runs": row[3],
                # Overall
                "avg": float(row[4]) if row[4] is not None else 0,
                "sr": float(row[5]) if row[5] is not None else 0,
                "dot_percent": float(row[6]) if row[6] is not None else 0,
                "boundary_percent": float(row[7]) if row[7] is not None else 0,
                # Powerplay 
                "pp_innings": int(row[8]) if row[8] is not None else 0,
                "pp_runs": float(row[9]) if row[9] is not None else 0,
                "pp_balls": float(row[10]) if row[10] is not None else 0,
                "pp_avg": float(row[11]) if row[11] is not None else 0,
                "pp_sr": float(row[12]) if row[12] is not None else 0,
                "pp_dot_percent": float(row[13]) if row[13] is not None else 0,
                "pp_boundary_percent": float(row[14]) if row[14] is not None else 0,
                # Middle overs
                "middle_innings": int(row[15]) if row[15] is not None else 0,
                "middle_runs": float(row[16]) if row[16] is not None else 0,
                "middle_balls": float(row[17]) if row[17] is not None else 0,
                "middle_avg": float(row[18]) if row[18] is not None else 0,
                "middle_sr": float(row[19]) if row[19] is not None else 0,
                "middle_dot_percent": float(row[20]) if row[20] is not None else 0,
                "middle_boundary_percent": float(row[21]) if row[21] is not None else 0,
                # Death overs
                "death_innings": int(row[22]) if row[22] is not None else 0,
                "death_runs": float(row[23]) if row[23] is not None else 0,
                "death_balls": float(row[24]) if row[24] is not None else 0,
                "death_avg": float(row[25]) if row[25] is not None else 0,
                "death_sr": float(row[26]) if row[26] is not None else 0,
                "death_dot_percent": float(row[27]) if row[27] is not None else 0,
                "death_boundary_percent": float(row[28]) if row[28] is not None else 0,
                "balls_per_innings": float(row[29]) if row[29] is not None else 0
            }
            for row in scatter_data
        ]

        return {
            "batting_leaders": batting_formatted,
            "bowling_leaders": bowling_formatted,
            "batting_scatter": scatter_formatted
        }

    except Exception as e:
        logging.error(f"Error getting venue stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/teams")
def get_teams(db: Session = Depends(get_session)):
    try:
        query = text("""
            SELECT DISTINCT team FROM (
                SELECT DISTINCT batting_team as team FROM batting_stats
                UNION
                SELECT DISTINCT bowling_team as team FROM bowling_stats
            ) teams
            WHERE team IS NOT NULL
            ORDER BY team
        """)
        teams = db.execute(query).fetchall()
        
        # Group teams by their abbreviation to deduplicate the list
        team_abbrev_map = {}
        for team in teams:
            team_name = team[0]
            if team_name in teams_mapping:
                abbrev = teams_mapping[team_name]
                # If we already have a team mapped to this abbreviation, skip
                if abbrev not in team_abbrev_map:
                    team_abbrev_map[abbrev] = {
                        'full_name': team_name,
                        'abbreviated_name': abbrev
                    }
            else:
                # For teams not in mapping, use the team name itself
                team_abbrev_map[team_name] = {
                    'full_name': team_name,
                    'abbreviated_name': team_name
                }
        
        # Convert the map to a list
        team_list = list(team_abbrev_map.values())
        
        return sorted(team_list, key=lambda x: x['full_name'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_score_with_wickets(match_id, innings):
    return """
        SELECT 
            CONCAT(
                SUM(runs_off_bat + extras), 
                '/', 
                COUNT(CASE WHEN wicket_type IS NOT NULL THEN 1 END)
            ) as score
        FROM deliveries 
        WHERE match_id = :match_id 
        AND innings = :innings
    """

def get_all_team_name_variations(team_name):
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

@app.get("/venues/{venue}/teams/{team1}/{team2}/history")
def get_match_history(
    venue: str,
    team1: str,
    team2: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_session)
):
    try:
        base_query = """
            WITH match_scores AS (
                SELECT 
                    m.id,
                    m.date,
                    m.team1,
                    m.team2,
                    m.winner,
                    m.venue,
                    m.won_batting_first,
                    m.won_fielding_first,
                    (
                        SELECT CONCAT(
                            COALESCE(SUM(d1.runs_off_bat + d1.extras), 0),
                            '/',
                            COALESCE(COUNT(CASE WHEN d1.wicket_type IS NOT NULL THEN 1 END), 0)
                        )
                        FROM deliveries d1
                        WHERE d1.match_id = m.id AND d1.innings = 1
                    ) as team1_score,
                    (
                        SELECT CONCAT(
                            COALESCE(SUM(d2.runs_off_bat + d2.extras), 0),
                            '/',
                            COALESCE(COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END), 0)
                        )
                        FROM deliveries d2
                        WHERE d2.match_id = m.id AND d2.innings = 2
                    ) as team2_score
                FROM matches m
                WHERE (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                {where_clause}
                ORDER BY m.date DESC
                LIMIT {limit}
            )
            SELECT 
                date,
                team1,
                team2,
                team1_score,
                team2_score,
                winner,
                venue,
                won_batting_first,
                won_fielding_first
            FROM match_scores
        """

        # Venue matches
        venue_results = db.execute(
            text("""
                WITH match_scores AS (
                    SELECT 
                        m.id,
                        m.date,
                        m.team1,
                        m.team2,
                        m.winner,
                        m.venue,
                        m.won_batting_first,
                        m.won_fielding_first,
                        (
                            SELECT CONCAT(
                                COALESCE(SUM(d1.runs_off_bat + d1.extras), 0),
                                '/',
                                COALESCE(COUNT(CASE WHEN d1.wicket_type IS NOT NULL THEN 1 END), 0)
                            )
                            FROM deliveries d1
                            WHERE d1.match_id = m.id AND d1.innings = 1
                        ) as team1_score,
                        (
                            SELECT CONCAT(
                                COALESCE(SUM(d2.runs_off_bat + d2.extras), 0),
                                '/',
                                COALESCE(COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END), 0)
                            )
                            FROM deliveries d2
                            WHERE d2.match_id = m.id AND d2.innings = 2
                        ) as team2_score
                    FROM matches m
                    WHERE (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    {where_clause}
                    ORDER BY m.date DESC
                    LIMIT {limit}
                )
                SELECT 
                    date,
                    team1,
                    team2,
                    team1_score,
                    team2_score,
                    winner,
                    venue,
                    won_batting_first,
                    won_fielding_first
                FROM match_scores
            """.format(
                    where_clause="AND m.venue = :venue",
                    limit="7"
                )),
            {"venue": venue, "start_date": start_date, "end_date": end_date}
        ).fetchall()

        # Get all possible name variations for both teams
        team1_names = get_all_team_name_variations(team1)
        team2_names = get_all_team_name_variations(team2)

        # Team 1 results
        team1_results = db.execute(
            text("""
                WITH match_scores AS (
                    SELECT 
                        m.id,
                        m.date,
                        m.team1,
                        m.team2,
                        m.winner,
                        m.venue,
                        m.won_batting_first,
                        m.won_fielding_first,
                        (
                            SELECT CONCAT(
                                COALESCE(SUM(d1.runs_off_bat + d1.extras), 0),
                                '/',
                                COALESCE(COUNT(CASE WHEN d1.wicket_type IS NOT NULL THEN 1 END), 0)
                            )
                            FROM deliveries d1
                            WHERE d1.match_id = m.id AND d1.innings = 1
                        ) as team1_score,
                        (
                            SELECT CONCAT(
                                COALESCE(SUM(d2.runs_off_bat + d2.extras), 0),
                                '/',
                                COALESCE(COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END), 0)
                            )
                            FROM deliveries d2
                            WHERE d2.match_id = m.id AND d2.innings = 2
                        ) as team2_score
                    FROM matches m
                    WHERE (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                    {where_clause}
                    ORDER BY m.date DESC
                    LIMIT {limit}
                )
                SELECT 
                    date,
                    team1,
                    team2,
                    team1_score,
                    team2_score,
                    winner,
                    venue,
                    won_batting_first,
                    won_fielding_first
                FROM match_scores
            """.format(
                    where_clause="AND (m.team1 = ANY(:team1_names) OR m.team2 = ANY(:team1_names))",
                    limit="5"
                )),
            {"team1_names": team1_names, "start_date": start_date, "end_date": end_date}
        ).fetchall()

        # Team 2 results
        team2_results = db.execute(
            text("""
            WITH match_scores AS (
                SELECT 
                    m.id,
                    m.date,
                    m.team1,
                    m.team2,
                    m.winner,
                    m.venue,
                    m.won_batting_first,
                    m.won_fielding_first,
                    (
                        SELECT CONCAT(
                            COALESCE(SUM(d1.runs_off_bat + d1.extras), 0),
                            '/',
                            COALESCE(COUNT(CASE WHEN d1.wicket_type IS NOT NULL THEN 1 END), 0)
                        )
                        FROM deliveries d1
                        WHERE d1.match_id = m.id AND d1.innings = 1
                    ) as team1_score,
                    (
                        SELECT CONCAT(
                            COALESCE(SUM(d2.runs_off_bat + d2.extras), 0),
                            '/',
                            COALESCE(COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END), 0)
                        )
                        FROM deliveries d2
                        WHERE d2.match_id = m.id AND d2.innings = 2
                    ) as team2_score
                FROM matches m
                WHERE (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                {where_clause}
                ORDER BY m.date DESC
                LIMIT {limit}
            )
            SELECT 
                date,
                team1,
                team2,
                team1_score,
                team2_score,
                winner,
                venue,
                won_batting_first,
                won_fielding_first
            FROM match_scores
        """.format(
                where_clause="AND (m.team1 = ANY(:team2_names) OR m.team2 = ANY(:team2_names))",
                limit="5"
            )),
            {"team2_names": team2_names, "start_date": start_date, "end_date": end_date}
        ).fetchall()

        # Get all possible name variations for both teams
        team1_names = get_all_team_name_variations(team1)
        team2_names = get_all_team_name_variations(team2)

        # Log team names for debugging
        logging.info(f"Searching for matches between: {team1_names} and {team2_names}")

        # Head to head matches
        h2h_matches = db.execute(
            text("""
            WITH match_scores AS (
                SELECT 
                    m.id,
                    m.date,
                    m.team1,
                    m.team2,
                    m.winner,
                    m.venue,
                    m.won_batting_first,
                    m.won_fielding_first,
                    (
                        SELECT CONCAT(
                            COALESCE(SUM(d1.runs_off_bat + d1.extras), 0),
                            '/',
                            COALESCE(COUNT(CASE WHEN d1.wicket_type IS NOT NULL THEN 1 END), 0)
                        )
                        FROM deliveries d1
                        WHERE d1.match_id = m.id AND d1.innings = 1
                    ) as team1_score,
                    (
                        SELECT CONCAT(
                            COALESCE(SUM(d2.runs_off_bat + d2.extras), 0),
                            '/',
                            COALESCE(COUNT(CASE WHEN d2.wicket_type IS NOT NULL THEN 1 END), 0)
                        )
                        FROM deliveries d2
                        WHERE d2.match_id = m.id AND d2.innings = 2
                    ) as team2_score
                FROM matches m
                WHERE (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                {where_clause}
                ORDER BY m.date DESC
                LIMIT {limit}
            )
            SELECT 
                date,
                team1,
                team2,
                team1_score,
                team2_score,
                winner,
                venue,
                won_batting_first,
                won_fielding_first
            FROM match_scores
        """.format(
                where_clause="AND ((m.team1 = ANY(:team1_names) AND m.team2 = ANY(:team2_names)) OR (m.team1 = ANY(:team2_names) AND m.team2 = ANY(:team1_names)))",
                limit="5"
            )),
            {"team1_names": team1_names, "team2_names": team2_names, "start_date": start_date, "end_date": end_date}
        ).fetchall()

        def format_match(match):
            return {
                "date": match.date.isoformat(),
                "team1": teams_mapping.get(match.team1, match.team1),
                "team2": teams_mapping.get(match.team2, match.team2),
                "score1": match.team1_score,
                "score2": match.team2_score,
                "venue": match.venue,
                "winner": teams_mapping.get(match.winner, match.winner) if match.winner else None,
                "won_batting_first": match.won_batting_first
            }

        h2h_stats = {
            "team1_wins": sum(1 for m in h2h_matches if m.winner in team1_names),
            "team2_wins": sum(1 for m in h2h_matches if m.winner in team2_names),
            "draws": len([m for m in h2h_matches if not m.winner]),
            "recent_matches": [format_match(m) for m in h2h_matches]
        }

        return {
            "venue_results": [format_match(m) for m in venue_results],
            "team1_results": [format_match(m) for m in team1_results],
            "team2_results": [format_match(m) for m in team2_results],
            "h2h_stats": h2h_stats
        }

    except Exception as e:
        logging.error(f"Error getting match history: {str(e)}")
        logging.error("Traceback:", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Add these helper routes for debugging
@app.get("/venues/{venue}/recent")
def get_venue_recent_matches(
    venue: str,
    db: Session = Depends(get_session)
):
    """Get recent matches at a venue"""
    try:
        matches = db.query(Match).filter(
            Match.venue == venue
        ).order_by(Match.date.desc()).limit(5).all()
        return matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/teams/{team}/recent")
def get_team_recent_matches(
    team: str,
    db: Session = Depends(get_session)
):
    """Get recent matches for a team"""
    try:
        matches = db.query(Match).filter(
            or_(Match.team1 == team, Match.team2 == team)
        ).order_by(Match.date.desc()).limit(5).all()
        return matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
@app.get("/teams/{team1}/{team2}/matchups")
def get_team_matchups(
    team1: str,
    team2: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    team1_players: List[str] = Query(default=[]),
    team2_players: List[str] = Query(default=[]),
    db: Session = Depends(get_session)
):
    try:
        # Determine if we're using custom teams or predefined teams
        use_custom_teams = len(team1_players) > 0 and len(team2_players) > 0

        print(f"Team1 players: {team1_players}")
        print(f"Team2 players: {team2_players}")
        print(f"Using custom teams: {use_custom_teams}")
        
        if not use_custom_teams:
            # Use predefined teams - original behavior
            team1_names = get_all_team_name_variations(team1)
            team2_names = get_all_team_name_variations(team2)

            # Get recent players from both teams (last 10 matches)
            recent_matches_query = text("""
                WITH recent_matches AS (
                    SELECT id 
                    FROM matches
                    WHERE ((team1 = ANY(:team1_names) OR team2 = ANY(:team1_names)) 
                           OR (team1 = ANY(:team2_names) OR team2 = ANY(:team2_names)))
                    AND (:start_date IS NULL OR date >= :start_date)
                    AND (:end_date IS NULL OR date <= :end_date)
                    ORDER BY date DESC
                    LIMIT 10
                ),
                team1_players AS (
                    SELECT DISTINCT batter as player
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    WHERE batting_team = ANY(:team1_names)
                    UNION
                    SELECT DISTINCT bowler
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    WHERE bowling_team = :team1
                ),
                team2_players AS (
                    SELECT DISTINCT batter as player
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    WHERE batting_team = ANY(:team2_names)
                    UNION
                    SELECT DISTINCT bowler
                    FROM deliveries d
                    JOIN recent_matches rm ON d.match_id = rm.id
                    WHERE bowling_team = :team2
                )
                SELECT player, :team1 as team FROM team1_players
                UNION ALL
                SELECT player, :team2 as team FROM team2_players
            """)
            
            recent_players = db.execute(recent_matches_query, {
                "team1": team1,
                "team2": team2,
                "team1_names": team1_names,
                "team2_names": team2_names,
                "start_date": start_date,
                "end_date": end_date
            }).fetchall()

            # Separate players by team
            team1_players = [row[0] for row in recent_players if row[1] == team1]
            team2_players = [row[0] for row in recent_players if row[1] == team2]

        # Get matchup statistics
        matchup_query = text("""
            WITH player_stats AS (
                SELECT 
                    d.batter,
                    d.bowler,
                    COUNT(*) as balls,
                    SUM(d.runs_off_bat + d.extras) as runs,
                    SUM(CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != 'run out' THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE 
                    (d.batter = ANY(:team1_players) AND d.bowler = ANY(:team2_players)
                    OR d.batter = ANY(:team2_players) AND d.bowler = ANY(:team1_players))
                    AND (:start_date IS NULL OR m.date >= :start_date)
                    AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY d.batter, d.bowler
                HAVING COUNT(*) >= 6
            )
            SELECT 
                batter,
                bowler,
                balls,
                runs,
                wickets,
                boundaries,
                dots,
                CAST(
                    CASE 
                        WHEN wickets = 0 THEN NULL 
                        ELSE (runs::numeric / wickets)
                    END AS numeric(10,2)
                ) as average,
                CAST(
                    (runs::numeric * 100 / NULLIF(balls, 0))
                    AS numeric(10,2)
                ) as strike_rate,
                CAST(
                    (dots::numeric * 100 / NULLIF(balls, 0))
                    AS numeric(10,2)
                ) as dot_percentage,
                CAST(
                    (boundaries::numeric * 100 / NULLIF(balls, 0))
                    AS numeric(10,2)
                ) as boundary_percentage
            FROM player_stats
            ORDER BY balls DESC
        """)

        matchups = db.execute(matchup_query, {
            "team1_players": team1_players,
            "team2_players": team2_players,
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()

        # Format results into two matrices
        team1_batting = {}
        team2_batting = {}

        for row in matchups:
            matchup_data = {
                "balls": row[2],
                "runs": row[3],
                "wickets": row[4],
                "boundaries": row[5],
                "dots": row[6],
                "average": float(row[7]) if row[7] is not None else None,
                "strike_rate": float(row[8]) if row[8] is not None else 0.0,
                "dot_percentage": float(row[9]) if row[9] is not None else 0.0,
                "boundary_percentage": float(row[10]) if row[10] is not None else 0.0
            }

            if row[0] in team1_players:  # Team 1 batting
                if row[0] not in team1_batting:
                    team1_batting[row[0]] = {}
                team1_batting[row[0]][row[1]] = matchup_data
            else:  # Team 2 batting
                if row[0] not in team2_batting:
                    team2_batting[row[0]] = {}
                team2_batting[row[0]][row[1]] = matchup_data

        return {
            "team1": {
                "name": team1,
                "players": team1_players,
                "batting_matchups": team1_batting
            },
            "team2": {
                "name": team2,
                "players": team2_players,
                "batting_matchups": team2_batting
            }
        }

    except Exception as e:
        logging.error(f"Error getting matchups: {str(e)}")
        logging.error("Traceback:", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
'''
@app.get("/venue-bowling-stats")
async def get_venue_bowling_stats(
    venue: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    db: Session = Depends(get_session)
):
    try:
        # Helper function to map column names to indices
        def get_column_index(column_name):
            # This mapping should match the order of columns in your SQL query
            column_indices = {
                "bowler_type": 0,
                "bowling_category": 1,
                "pp_balls_percentage": 2,
                "pp_wickets_percentage": 3,
                "pp_dot_percentage": 4,
                "pp_boundary_percentage": 5,
                "pp_economy": 6,
                "pp_strike_rate": 7,
                "pp_average": 8,
                "middle_balls_percentage": 9,
                "middle_wickets_percentage": 10,
                "middle_dot_percentage": 11,
                "middle_boundary_percentage": 12,
                "middle_economy": 13,
                "middle_strike_rate": 14,
                "middle_average": 15,
                "death_balls_percentage": 16,
                "death_wickets_percentage": 17,
                "death_dot_percentage": 18,
                "death_boundary_percentage": 19,
                "death_economy": 20,
                "death_strike_rate": 21,
                "death_average": 22,
                "overall_balls_percentage": 23,
                "overall_wickets_percentage": 24,
                "overall_dot_percentage": 25,
                "overall_boundary_percentage": 26,
                "overall_economy": 27,
                "overall_strike_rate": 28,
                "overall_average": 29
            }
            return column_indices.get(column_name, 0)  # Default to 0 if not found

        base_query = """
        WITH BowlerTypes AS (
            SELECT 
                p.name,
                p.bowler_type,
                CASE 
                    WHEN p.bowler_type IN ('RF', 'RM', 'RS', 'LF', 'LM', 'LS') THEN 'pace'
                    WHEN p.bowler_type IN ('RO', 'RL', 'LO', 'LC') THEN 'spin'
                END as bowling_category
            FROM players p
            WHERE p.bowler_type IS NOT NULL
        ),
        """

        conditions = []
        params = {}

        if venue != "All Venues":
            conditions.append("m.venue = :venue")
            params["venue"] = venue

        if start_date:
            conditions.append("m.date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("m.date <= :end_date")
            params["end_date"] = end_date

        # Handle leagues with parameter binding
        if leagues:
            conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
            params["leagues"] = leagues

        # Handle international matches with parameter binding
        if include_international:
            if top_teams:
                teams = INTERNATIONAL_TEAMS_RANKED[:top_teams]
                conditions.append("(m.match_type = 'international' AND m.team1 = ANY(:teams) AND m.team2 = ANY(:teams))")
                params["teams"] = teams
            else:
                conditions.append("(m.match_type = 'international')")

        where_clause = "WHERE 1=1"
        if conditions:
            where_clause += f" AND {' AND '.join(conditions)}"

        complete_query = f"""
        {base_query}
        PhaseStats AS (
            SELECT
                bt.bowler_type,
                bt.bowling_category,
                
                NULLIF(CAST(SUM(bs.pp_overs * 6) AS numeric), 0) as pp_balls,
                NULLIF(CAST(SUM(bs.pp_wickets) AS numeric), 0) as pp_wickets,
                NULLIF(CAST(SUM(bs.pp_dots) AS numeric), 0) as pp_dots,
                NULLIF(CAST(SUM(bs.pp_runs) AS numeric), 0) as pp_runs,
                NULLIF(CAST(SUM(bs.pp_boundaries) AS numeric), 0) as pp_boundaries,
                
                NULLIF(CAST(SUM(bs.middle_overs * 6) AS numeric), 0) as middle_balls,
                NULLIF(CAST(SUM(bs.middle_wickets) AS numeric), 0) as middle_wickets,
                NULLIF(CAST(SUM(bs.middle_dots) AS numeric), 0) as middle_dots,
                NULLIF(CAST(SUM(bs.middle_runs) AS numeric), 0) as middle_runs,
                NULLIF(CAST(SUM(bs.middle_boundaries) AS numeric), 0) as middle_boundaries,
                
                NULLIF(CAST(SUM(bs.death_overs * 6) AS numeric), 0) as death_balls,
                NULLIF(CAST(SUM(bs.death_wickets) AS numeric), 0) as death_wickets,
                NULLIF(CAST(SUM(bs.death_dots) AS numeric), 0) as death_dots,
                NULLIF(CAST(SUM(bs.death_runs) AS numeric), 0) as death_runs,
                NULLIF(CAST(SUM(bs.death_boundaries) AS numeric), 0) as death_boundaries
                
            FROM bowling_stats bs
            JOIN matches m ON bs.match_id = m.id
            JOIN BowlerTypes bt ON bs.bowler = bt.name
            {where_clause}
        """

        complete_query += """
            GROUP BY bt.bowler_type, bt.bowling_category
        )
        SELECT
            bowler_type,
            bowling_category,
            
            CAST(COALESCE(ROUND(CAST(100.0 * pp_balls / NULLIF(SUM(pp_balls) OVER (), 0) AS numeric), 2), 0) AS numeric) as pp_balls_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * pp_wickets / NULLIF(SUM(pp_wickets) OVER (), 0) AS numeric), 2), 0) AS numeric) as pp_wickets_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * pp_dots / NULLIF(pp_balls, 0) AS numeric), 2), 0) AS numeric) as pp_dot_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * pp_boundaries / NULLIF(pp_balls, 0) AS numeric), 2), 0) AS numeric) as pp_boundary_percentage,
            CAST(COALESCE(ROUND(CAST(6.0 * pp_runs / NULLIF(pp_balls, 0) AS numeric), 2), 0) AS numeric) as pp_economy,
            CAST(COALESCE(ROUND(CAST(pp_balls / NULLIF(pp_wickets, 0) AS numeric), 2), 0) AS numeric) as pp_strike_rate,
            CAST(COALESCE(ROUND(CAST(pp_runs / NULLIF(pp_wickets, 0) AS numeric), 2), 0) AS numeric) as pp_average,

            CAST(COALESCE(ROUND(CAST(100.0 * middle_balls / NULLIF(SUM(middle_balls) OVER (), 0) AS numeric), 2), 0) AS numeric) as middle_balls_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * middle_wickets / NULLIF(SUM(middle_wickets) OVER (), 0) AS numeric), 2), 0) AS numeric) as middle_wickets_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * middle_dots / NULLIF(middle_balls, 0) AS numeric), 2), 0) AS numeric) as middle_dot_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * middle_boundaries / NULLIF(middle_balls, 0) AS numeric), 2), 0) AS numeric) as middle_boundary_percentage,
            CAST(COALESCE(ROUND(CAST(6.0 * middle_runs / NULLIF(middle_balls, 0) AS numeric), 2), 0) AS numeric) as middle_economy,
            CAST(COALESCE(ROUND(CAST(middle_balls / NULLIF(middle_wickets, 0) AS numeric), 2), 0) AS numeric) as middle_strike_rate,
            CAST(COALESCE(ROUND(CAST(middle_runs / NULLIF(middle_wickets, 0) AS numeric), 2), 0) AS numeric) as middle_average,

            CAST(COALESCE(ROUND(CAST(100.0 * death_balls / NULLIF(SUM(death_balls) OVER (), 0) AS numeric), 2), 0) AS numeric) as death_balls_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * death_wickets / NULLIF(SUM(death_wickets) OVER (), 0) AS numeric), 2), 0) AS numeric) as death_wickets_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * death_dots / NULLIF(death_balls, 0) AS numeric), 2), 0) AS numeric) as death_dot_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * death_boundaries / NULLIF(death_balls, 0) AS numeric), 2), 0) AS numeric) as death_boundary_percentage,
            CAST(COALESCE(ROUND(CAST(6.0 * death_runs / NULLIF(death_balls, 0) AS numeric), 2), 0) AS numeric) as death_economy,
            CAST(COALESCE(ROUND(CAST(death_balls / NULLIF(death_wickets, 0) AS numeric), 2), 0) AS numeric) as death_strike_rate,
            CAST(COALESCE(ROUND(CAST(death_runs / NULLIF(death_wickets, 0) AS numeric), 2), 0) AS numeric) as death_average,

            CAST(COALESCE(ROUND(CAST(100.0 * (pp_balls + middle_balls + death_balls) / 
                NULLIF(SUM(pp_balls + middle_balls + death_balls) OVER (), 0) AS numeric), 2), 0) AS numeric) as overall_balls_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * (pp_wickets + middle_wickets + death_wickets) / 
                NULLIF(SUM(pp_wickets + middle_wickets + death_wickets) OVER (), 0) AS numeric), 2), 0) AS numeric) as overall_wickets_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * (pp_dots + middle_dots + death_dots) / 
                NULLIF(pp_balls + middle_balls + death_balls, 0) AS numeric), 2), 0) AS numeric) as overall_dot_percentage,
            CAST(COALESCE(ROUND(CAST(100.0 * (pp_boundaries + middle_boundaries + death_boundaries) / 
                NULLIF(pp_balls + middle_balls + death_balls, 0) AS numeric), 2), 0) AS numeric) as overall_boundary_percentage,
            CAST(COALESCE(ROUND(CAST(6.0 * (pp_runs + middle_runs + death_runs) / 
                NULLIF(pp_balls + middle_balls + death_balls, 0) AS numeric), 2), 0) AS numeric) as overall_economy,
            CAST(COALESCE(ROUND(CAST((pp_balls + middle_balls + death_balls) / 
                NULLIF(pp_wickets + middle_wickets + death_wickets, 0) AS numeric), 2), 0) AS numeric) as overall_strike_rate,
            CAST(COALESCE(ROUND(CAST((pp_runs + middle_runs + death_runs) / 
                NULLIF(pp_wickets + middle_wickets + death_wickets, 0) AS numeric), 2), 0) AS numeric) as overall_average
        FROM PhaseStats
        ORDER BY bowling_category, bowler_type
        """

        from sqlalchemy.sql import text
        query = text(complete_query)
        
        results = db.execute(query, params).fetchall()

        print("Query results:", results)
        print("Base query:", base_query)
        print("Params:", params)

        logging.info(f"Query results: {results}")
        logging.info(f"Base query: {base_query}")
        logging.info(f"Params: {params}")

        if not results:
            return {
                "paceVsSpin": {
                    phase: {
                        "pace": defaultMetrics(),
                        "spin": defaultMetrics()
                    } for phase in ["pp", "middle", "death", "overall"]
                },
                "bowlingTypes": {
                    phase: [] for phase in ["pp", "middle", "death", "overall"]
                }
            }

        # Use numeric indices to access tuple elements in results
        transformed_data = {
            "paceVsSpin": {
                phase: {
                    category: {
                        "ballsPercentage": float(sum(row[get_column_index(f"{phase}_balls_percentage")] or 0 
                                             for row in results if row[1] == category)),
                        "wicketsPercentage": float(sum(row[get_column_index(f"{phase}_wickets_percentage")] or 0 
                                             for row in results if row[1] == category)),
                        "dotBallPercentage": float(sum(row[get_column_index(f"{phase}_dot_percentage")] or 0 
                                             for row in results if row[1] == category) / 
                                             (len([r for r in results if r[1] == category]) or 1)),
                        "boundaryPercentage": float(sum(row[get_column_index(f"{phase}_boundary_percentage")] or 0 
                                             for row in results if row[1] == category) / 
                                             (len([r for r in results if r[1] == category]) or 1)),
                        "economyRate": float(sum(row[get_column_index(f"{phase}_economy")] or 0 
                                             for row in results if row[1] == category) / 
                                             (len([r for r in results if r[1] == category]) or 1)),
                        "strikeRate": float(sum(row[get_column_index(f"{phase}_strike_rate")] or 0 
                                             for row in results if row[1] == category) / 
                                             (len([r for r in results if r[1] == category]) or 1)),
                        "average": float(sum(row[get_column_index(f"{phase}_average")] or 0 
                                             for row in results if row[1] == category) / 
                                             (len([r for r in results if r[1] == category]) or 1))
                    }
                    for category in ["pace", "spin"]
                }
                for phase in ["pp", "middle", "death", "overall"]
            },
            "bowlingTypes": {
                phase: [
                    {
                        "bowlingType": row[0],  # bowler_type is at index 0
                        "ballsPercentage": float(row[get_column_index(f"{phase}_balls_percentage")] or 0),
                        "wicketsPercentage": float(row[get_column_index(f"{phase}_wickets_percentage")] or 0),
                        "dotBallPercentage": float(row[get_column_index(f"{phase}_dot_percentage")] or 0),
                        "boundaryPercentage": float(row[get_column_index(f"{phase}_boundary_percentage")] or 0),
                        "economyRate": float(row[get_column_index(f"{phase}_economy")] or 0),
                        "strikeRate": float(row[get_column_index(f"{phase}_strike_rate")] or 0),
                        "average": float(row[get_column_index(f"{phase}_average")] or 0)
                    }
                    for row in results
                ]
                for phase in ["pp", "middle", "death", "overall"]
            }
        }

        return transformed_data

    except Exception as e:
        print(f"Error in get_venue_bowling_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
def defaultMetrics():
    return {
        "ballsPercentage": 0,
        "wicketsPercentage": 0,
        "dotBallPercentage": 0,
        "boundaryPercentage": 0,
        "economyRate": 0,
        "strikeRate": 0,
        "average": 0
    }

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from sqlalchemy.sql import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import Optional
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_phase_metrics(data):
    """Helper function to calculate derived metrics for a phase"""
    return {
        "runs": data["runs"],
        "balls": data["balls"],
        "average": round(data["runs"] / data["wickets"], 2) if data["wickets"] and data["runs"] else 0,
        "strike_rate": round((data["runs"] * 100) / data["balls"], 2) if data["balls"] and data["runs"] else 0,
        "dot_percentage": round((data["dots"] * 100) / data["balls"], 2) if data["balls"] and data["dots"] else 0,
        "boundary_percentage": round((data["boundaries"] * 100) / data["balls"], 2) if data["balls"] and data["boundaries"] else 0
    }

@app.get("/player/{player_name}/stats")
def get_player_stats(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    db: Session = Depends(get_session)
):
    try:

        logger.info(f"Received params - start_date: {start_date}, end_date: {end_date}, leagues: {leagues}, include_international: {include_international}")

        params = {
            "player_name": player_name,
            "start_date": start_date,
            "end_date": end_date,
            "venue": venue,
            "has_leagues": bool(leagues),
            "include_international": include_international,
            "top_teams": top_teams is not None,
            "top_team_list": INTERNATIONAL_TEAMS_RANKED[:top_teams] if top_teams else []
        }
        
        # If leagues are provided, expand them to include full names
        if leagues:
            params["leagues"] = expand_league_abbreviations(leagues)
        else:
            params["leagues"] = []

        match_filter = """
            AND (
                (:has_leagues AND m.match_type = 'league' AND m.competition = ANY(:leagues))
                OR (:include_international AND m.match_type = 'international' 
                    AND (:top_teams IS NULL OR 
                        (m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list))
                    )
                )
            )
        """

        overall_query = text(f"""
            SELECT
                COUNT(DISTINCT m.id) as matches,
                SUM(bs.runs) as runs,
                SUM(bs.balls_faced) as balls,
                COUNT(CASE WHEN bs.runs >= 50 AND bs.runs < 100 THEN 1 END) as fifties,
                COUNT(CASE WHEN bs.runs >= 100 THEN 1 END) as hundreds,
                CAST(SUM(bs.runs) AS FLOAT) / NULLIF(COUNT(CASE WHEN bs.wickets > 0 THEN 1 END), 0) as average,
                CAST(SUM(bs.runs) * 100.0 AS FLOAT) / NULLIF(SUM(bs.balls_faced), 0) as strike_rate,
                CAST(SUM(bs.dots) * 100.0 AS FLOAT) / NULLIF(SUM(bs.balls_faced), 0) as dot_percentage,
                CAST(SUM(bs.fours + bs.sixes) * 100.0 AS FLOAT) / NULLIF(SUM(bs.balls_faced), 0) as boundary_percentage
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
        """)

        phase_query = text(f"""
            SELECT 
                SUM(bs.pp_runs) as pp_runs,
                SUM(bs.pp_balls) as pp_balls,
                SUM(bs.pp_dots) as pp_dots,
                SUM(bs.pp_boundaries) as pp_boundaries,
                SUM(bs.pp_wickets) as pp_wickets,
                
                SUM(bs.middle_runs) as middle_runs,
                SUM(bs.middle_balls) as middle_balls,
                SUM(bs.middle_dots) as middle_dots,
                SUM(bs.middle_boundaries) as middle_boundaries,
                SUM(bs.middle_wickets) as middle_wickets,
                
                SUM(bs.death_runs) as death_runs,
                SUM(bs.death_balls) as death_balls,
                SUM(bs.death_dots) as death_dots,
                SUM(bs.death_boundaries) as death_boundaries,
                SUM(bs.death_wickets) as death_wickets
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
        """)

        # New innings query with all fields
        innings_query = text(f"""
            SELECT 
                m.id as match_id,
                m.date,
                m.venue,
                m.competition,
                m.winner,
                bs.*,
                CASE 
                    WHEN m.team1 = bs.batting_team THEN m.team2 
                    ELSE m.team1 
                END as bowling_team
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            ORDER BY m.date DESC
        """)

        pace_spin_query = text(f"""
            WITH BowlerTypes AS (
                SELECT 
                    p.name,
                    p.bowler_type,
                    CASE 
                        WHEN p.bowler_type IN ('RF', 'RM', 'RS', 'LF', 'LM', 'LS') THEN 'pace'
                        WHEN p.bowler_type IN ('RO', 'RL', 'LO', 'LC') THEN 'spin'
                    END as bowling_category
                FROM players p
                WHERE p.bowler_type IS NOT NULL
            )
            SELECT 
                bt.bowling_category as category,
                SUM(d.runs_off_bat + d.extras) as runs,
                COUNT(*) as balls,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as boundaries,
                SUM(CASE WHEN d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                THEN 1 ELSE 0 END) as wickets,
                
                SUM(CASE WHEN d.over < 6 THEN d.runs_off_bat + d.extras ELSE 0 END) as pp_runs,
                SUM(CASE WHEN d.over < 6 THEN 1 ELSE 0 END) as pp_balls,
                SUM(CASE WHEN d.over < 6 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as pp_dots,
                SUM(CASE WHEN d.over < 6 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as pp_boundaries,
                SUM(CASE WHEN d.over < 6 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as pp_wickets,
                
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 THEN d.runs_off_bat + d.extras ELSE 0 END) as middle_runs,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 THEN 1 ELSE 0 END) as middle_balls,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as middle_dots,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as middle_boundaries,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as middle_wickets,
                
                SUM(CASE WHEN d.over >= 15 THEN d.runs_off_bat + d.extras ELSE 0 END) as death_runs,
                SUM(CASE WHEN d.over >= 15 THEN 1 ELSE 0 END) as death_balls,
                SUM(CASE WHEN d.over >= 15 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as death_dots,
                SUM(CASE WHEN d.over >= 15 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as death_boundaries,
                SUM(CASE WHEN d.over >= 15 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as death_wickets
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            JOIN players p ON d.bowler = p.name
            JOIN BowlerTypes bt ON p.name = bt.name
            WHERE d.batter = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            GROUP BY bt.bowling_category
            HAVING bt.bowling_category IS NOT NULL
        """)

        bowling_types_query = text(f"""
            SELECT 
                p.bowler_type,
                SUM(d.runs_off_bat + d.extras) as runs,
                COUNT(*) as balls,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as boundaries,
                SUM(CASE WHEN d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                THEN 1 ELSE 0 END) as wickets,
                
                SUM(CASE WHEN d.over < 6 THEN d.runs_off_bat + d.extras ELSE 0 END) as pp_runs,
                SUM(CASE WHEN d.over < 6 THEN 1 ELSE 0 END) as pp_balls,
                SUM(CASE WHEN d.over < 6 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as pp_dots,
                SUM(CASE WHEN d.over < 6 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as pp_boundaries,
                SUM(CASE WHEN d.over < 6 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as pp_wickets,
                
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 THEN d.runs_off_bat + d.extras ELSE 0 END) as middle_runs,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 THEN 1 ELSE 0 END) as middle_balls,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as middle_dots,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as middle_boundaries,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as middle_wickets,
                
                SUM(CASE WHEN d.over >= 15 THEN d.runs_off_bat + d.extras ELSE 0 END) as death_runs,
                SUM(CASE WHEN d.over >= 15 THEN 1 ELSE 0 END) as death_balls,
                SUM(CASE WHEN d.over >= 15 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as death_dots,
                SUM(CASE WHEN d.over >= 15 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as death_boundaries,
                SUM(CASE WHEN d.over >= 15 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as death_wickets
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            JOIN players p ON d.bowler = p.name
            WHERE d.batter = :player_name
            AND p.bowler_type IS NOT NULL
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            GROUP BY p.bowler_type
        """)

        # Execute queries
        overall = db.execute(overall_query, params).fetchone()
        phase_stats = db.execute(phase_query, params).fetchone()
        pace_spin_stats = db.execute(pace_spin_query, params).fetchall()
        bowling_type_stats = db.execute(bowling_types_query, params).fetchall()
        innings_data = db.execute(innings_query, params).fetchall()

        # Format innings data with all fields
        formatted_innings = []
        for inning in innings_data:
            formatted_innings.append({
                "match_id": inning.match_id,
                "date": inning.date.isoformat(),
                "venue": inning.venue,
                "competition": inning.competition,
                "batting_team": inning.batting_team,
                "bowling_team": inning.bowling_team,
                "winner": inning.winner,
                
                # Basic stats
                "runs": inning.runs,
                "balls_faced": inning.balls_faced,
                "wickets": inning.wickets,
                "strike_rate": float(inning.strike_rate) if inning.strike_rate else 0,
                "fours": inning.fours,
                "sixes": inning.sixes,
                "dots": inning.dots,
                "ones": inning.ones,
                "twos": inning.twos,
                "threes": inning.threes,

                # Position and entry
                "batting_position": inning.batting_position,
                "entry_point": {
                    "runs": inning.entry_runs,
                    "balls": inning.entry_balls,
                    "overs": float(inning.entry_overs) if inning.entry_overs else 0
                },

                # Phase details
                "phase_details": {
                    "powerplay": {
                        "runs": inning.pp_runs,
                        "balls": inning.pp_balls,
                        "strike_rate": float(inning.pp_strike_rate) if inning.pp_strike_rate else 0,
                        "dots": inning.pp_dots,
                        "wickets": inning.pp_wickets,
                        "boundaries": inning.pp_boundaries
                    },
                    "middle": {
                        "runs": inning.middle_runs,
                        "balls": inning.middle_balls,
                        "strike_rate": float(inning.middle_strike_rate) if inning.middle_strike_rate else 0,
                        "dots": inning.middle_dots,
                        "wickets": inning.middle_wickets,
                        "boundaries": inning.middle_boundaries
                    },
                    "death": {
                        "runs": inning.death_runs,
                        "balls": inning.death_balls,
                        "strike_rate": float(inning.death_strike_rate) if inning.death_strike_rate else 0,
                        "dots": inning.death_dots,
                        "wickets": inning.death_wickets,
                        "boundaries": inning.death_boundaries
                    }
                },

                # Team comparison
                "team_comparison": {
                    "team_runs_excl_batter": inning.team_runs_excl_batter,
                    "team_balls_excl_batter": inning.team_balls_excl_batter,
                    "team_sr_excl_batter": float(inning.team_sr_excl_batter) if inning.team_sr_excl_batter else 0,
                    "sr_diff": float(inning.sr_diff) if inning.sr_diff else 0
                }
            })

        def calculate_phase_metrics(data):
            return {
                "runs": data["runs"],
                "balls": data["balls"],
                "average": round(data["runs"] / data["wickets"], 2) if data["wickets"] and data["runs"] else 0,
                "strike_rate": round((data["runs"] * 100) / data["balls"], 2) if data["balls"] and data["runs"] else 0,
                "dot_percentage": round((data["dots"] * 100) / data["balls"], 2) if data["balls"] and data["dots"] else 0,
                "boundary_percentage": round((data["boundaries"] * 100) / data["balls"], 2) if data["balls"] and data["boundaries"] else 0
            }

        response = {
            "overall": {
                "matches": overall.matches,
                "runs": overall.runs or 0,
                "average": round(overall.average, 2) if overall.average else 0,
                "strike_rate": round(overall.strike_rate, 2) if overall.strike_rate else 0,
                "fifties": overall.fifties or 0,
                "hundreds": overall.hundreds or 0,
                "dot_percentage": round(overall.dot_percentage, 2) if overall.dot_percentage else 0,
                "boundary_percentage": round(overall.boundary_percentage, 2) if overall.boundary_percentage else 0
            },
            "phase_stats": {
                "overall": {
                    "powerplay": calculate_phase_metrics({
                        "runs": phase_stats.pp_runs or 0,
                        "balls": phase_stats.pp_balls or 0,
                        "dots": phase_stats.pp_dots or 0,
                        "boundaries": phase_stats.pp_boundaries or 0,
                        "wickets": phase_stats.pp_wickets or 0
                    }),
                    "middle": calculate_phase_metrics({
                        "runs": phase_stats.middle_runs or 0,
                        "balls": phase_stats.middle_balls or 0,
                        "dots": phase_stats.middle_dots or 0,
                        "boundaries": phase_stats.middle_boundaries or 0,
                        "wickets": phase_stats.middle_wickets or 0
                    }),
                    "death": calculate_phase_metrics({
                        "runs": phase_stats.death_runs or 0,
                        "balls": phase_stats.death_balls or 0,
                        "dots": phase_stats.death_dots or 0,
                        "boundaries": phase_stats.death_boundaries or 0,
                        "wickets": phase_stats.death_wickets or 0
                    })
                },
                "pace": {},
                "spin": {},
                "bowling_types": {}
            },
            "innings": formatted_innings
        }

        # Process pace vs spin stats
        for stat in pace_spin_stats:
            phase_data = {
                "powerplay": calculate_phase_metrics({
                    "runs": stat.pp_runs or 0,
                    "balls": stat.pp_balls or 0,
                    "dots": stat.pp_dots or 0,
                    "boundaries": stat.pp_boundaries or 0,
                    "wickets": stat.pp_wickets or 0
                }),
                "middle": calculate_phase_metrics({
                    "runs": stat.middle_runs or 0,
                    "balls": stat.middle_balls or 0,
                    "dots": stat.middle_dots or 0,
                    "boundaries": stat.middle_boundaries or 0,
                    "wickets": stat.middle_wickets or 0
                }),
                "death": calculate_phase_metrics({
                    "runs": stat.death_runs or 0,
                    "balls": stat.death_balls or 0,
                    "dots": stat.death_dots or 0,
                    "boundaries": stat.death_boundaries or 0,
                    "wickets": stat.death_wickets or 0
                }),
                "overall": calculate_phase_metrics({
                    "runs": stat.runs or 0,
                    "balls": stat.balls or 0,
                    "dots": stat.dots or 0,
                    "boundaries": stat.boundaries or 0,
                    "wickets": stat.wickets or 0
                })
            }
            response["phase_stats"][stat.category] = phase_data

        # Process bowling type specific stats
        for stat in bowling_type_stats:
            phase_data = {
                "powerplay": calculate_phase_metrics({
                    "runs": stat.pp_runs or 0,
                    "balls": stat.pp_balls or 0,
                    "dots": stat.pp_dots or 0,
                    "boundaries": stat.pp_boundaries or 0,
                    "wickets": stat.pp_wickets or 0
                }),
                "middle": calculate_phase_metrics({
                    "runs": stat.middle_runs or 0,
                    "balls": stat.middle_balls or 0,
                    "dots": stat.middle_dots or 0,
                    "boundaries": stat.middle_boundaries or 0,
                    "wickets": stat.middle_wickets or 0
                }),
                "death": calculate_phase_metrics({
                    "runs": stat.death_runs or 0,
                    "balls": stat.death_balls or 0,
                    "dots": stat.death_dots or 0,
                    "boundaries": stat.death_boundaries or 0,
                    "wickets": stat.death_wickets or 0
                }),
                "overall": calculate_phase_metrics({
                    "runs": stat.runs or 0,
                    "balls": stat.balls or 0,
                    "dots": stat.dots or 0,
                    "boundaries": stat.boundaries or 0,
                    "wickets": stat.wickets or 0
                })
            }
            response["phase_stats"]["bowling_types"][stat.bowler_type] = phase_data

        return response

    except Exception as e:
        logger.error(f"Error in get_player_stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing stats: {str(e)}")

@app.get("/player/{player_name}/ball_stats")
def get_player_ball_stats(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    db: Session = Depends(get_session)
):
    try:
        params = {
            "player_name": player_name,
            "start_date": start_date,
            "end_date": end_date,
            "venue": venue,
            "has_leagues": bool(leagues),
            "leagues": leagues if leagues else [],
            "include_international": include_international,
            "top_teams": top_teams is not None,
            "top_team_list": INTERNATIONAL_TEAMS_RANKED[:top_teams] if top_teams else []
        }

        match_filter = """
            AND (
                (:has_leagues AND m.match_type = 'league' AND m.competition = ANY(:leagues))
                OR (:include_international AND m.match_type = 'international' 
                    AND (:top_teams IS NULL OR 
                        (m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list))
                    )
                )
            )
        """

        ball_sequence_query = text(f"""
            WITH innings_balls AS (
                SELECT 
                    d.match_id,
                    d.innings,
                    d.batter,
                    d.runs_off_bat + d.extras as runs,
                    CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END as is_dot,
                    CASE WHEN d.runs_off_bat = 4 THEN 1 ELSE 0 END as is_four,
                    CASE WHEN d.runs_off_bat = 6 THEN 1 ELSE 0 END as is_six,
                    CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != 'run out' THEN 1 ELSE 0 END as is_wicket,
                    d.extras,
                    CASE 
                        WHEN d.over < 6 THEN 'powerplay'
                        WHEN d.over < 15 THEN 'middle'
                        ELSE 'death'
                    END as phase,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.match_id, d.innings, d.batter 
                        ORDER BY d.over, d.ball
                    ) as ball_number
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.batter = :player_name
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                AND (:venue IS NULL OR m.venue = :venue)
                {match_filter}
            ),
            innings_totals AS (
                SELECT
                    match_id,
                    innings,
                    ball_number,
                    phase,
                    SUM(runs) OVER (
                        PARTITION BY match_id, innings
                        ORDER BY ball_number
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) as runs_till_ball,
                    SUM(is_dot) OVER (
                        PARTITION BY match_id, innings
                        ORDER BY ball_number
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) as dots_till_ball,
                    SUM(is_four) OVER (
                        PARTITION BY match_id, innings
                        ORDER BY ball_number
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) as fours_till_ball,
                    SUM(is_six) OVER (
                        PARTITION BY match_id, innings
                        ORDER BY ball_number
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) as sixes_till_ball,
                    SUM(is_wicket) OVER (
                        PARTITION BY match_id, innings
                        ORDER BY ball_number
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) as wickets_till_ball,
                    SUM(extras) OVER (
                        PARTITION BY match_id, innings
                        ORDER BY ball_number
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) as extras_till_ball
                FROM innings_balls
            ),
            ball_stats AS (
                SELECT 
                    ball_number,
                    COUNT(*) as innings_with_n_balls,
                    SUM(runs_till_ball) as total_runs,
                    SUM(dots_till_ball) as dots,
                    SUM(fours_till_ball) as fours,
                    SUM(sixes_till_ball) as sixes,
                    SUM(wickets_till_ball) as wickets,
                    SUM(extras_till_ball) as extras,
                    SUM(CASE WHEN phase = 'powerplay' THEN 1 ELSE 0 END) as powerplay_balls,
                    SUM(CASE WHEN phase = 'middle' THEN 1 ELSE 0 END) as middle_balls,
                    SUM(CASE WHEN phase = 'death' THEN 1 ELSE 0 END) as death_balls
                FROM innings_totals
                GROUP BY ball_number
            )
            SELECT
                ball_number,
                innings_with_n_balls,
                total_runs,
                CAST((total_runs * 100.0) / (ball_number * innings_with_n_balls) AS DECIMAL(10,2)) as strike_rate,
                dots,
                fours,
                sixes,
                wickets,
                extras,
                CAST((dots * 100.0) / (ball_number * innings_with_n_balls) AS DECIMAL(10,2)) as dot_percentage,
                CAST(((fours + sixes) * 100.0) / (ball_number * innings_with_n_balls) AS DECIMAL(10,2)) as boundary_percentage,
                CAST(total_runs::float / NULLIF(wickets, 0) AS DECIMAL(10,2)) as average,
                powerplay_balls,
                middle_balls,
                death_balls
            FROM ball_stats
            ORDER BY ball_number
        """)

        ball_stats = db.execute(ball_sequence_query, params).fetchall()

        return {
            "ball_by_ball_stats": [
                {
                    "ball_number": row.ball_number,
                    "innings_with_n_balls": row.innings_with_n_balls,
                    "total_runs": row.total_runs,
                    "strike_rate": float(row.strike_rate if row.strike_rate else 0),
                    "dots": row.dots,
                    "fours": row.fours,
                    "sixes": row.sixes,
                    "wickets": row.wickets,
                    "extras": row.extras,
                    "dot_percentage": float(row.dot_percentage if row.dot_percentage else 0),
                    "boundary_percentage": float(row.boundary_percentage if row.boundary_percentage else 0),
                    "average": float(row.average if row.average else 0),
                    "phase_distribution": {
                        "powerplay": row.powerplay_balls,
                        "middle": row.middle_balls,
                        "death": row.death_balls
                    }
                }
                for row in ball_stats
            ]
        }

    except Exception as e:
        logging.error(f"Error in get_player_ball_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/teams/bowling-type-matchups")
def get_team_bowling_type_matchups(
    players: List[str] = Query(...),
    phase: str = Query("overall", enum=["overall", "powerplay", "middle", "death"]),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_session)
):
    """
    Get team matchups against different bowling types by game phase.
    Returns a matrix of player stats against each bowling type.
    """
    try:
        # Input validation
        if not players:
            raise HTTPException(status_code=400, detail="Must provide at least one player")
            
        # Parameters for SQL query
        params = {
            "players": players,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Build the SQL query to get player stats vs bowling types
        query = text("""
            WITH BowlerTypes AS (
                SELECT 
                    p.name,
                    p.bowler_type,
                    CASE 
                        WHEN p.bowler_type IN ('RF', 'RM', 'RS', 'LF', 'LM', 'LS') THEN 'pace'
                        WHEN p.bowler_type IN ('RO', 'RL', 'LO', 'LC') THEN 'spin'
                    END as bowling_category
                FROM players p
                WHERE p.bowler_type IS NOT NULL
            ),
            PlayerStats AS (
                SELECT 
                    d.batter,
                    bt.bowler_type,
                    
                    -- Overall stats
                    COUNT(*) as balls,
                    SUM(d.runs_off_bat + d.extras) as runs,
                    SUM(CASE WHEN d.wicket_type IS NOT NULL 
                        AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                    THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as boundaries,
                    
                    -- Powerplay stats (0-6 overs)
                    SUM(CASE WHEN d.over < 6 THEN 1 ELSE 0 END) as pp_balls,
                    SUM(CASE WHEN d.over < 6 THEN d.runs_off_bat + d.extras ELSE 0 END) as pp_runs,
                    SUM(CASE WHEN d.over < 6 AND d.wicket_type IS NOT NULL 
                        AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                    THEN 1 ELSE 0 END) as pp_wickets,
                    SUM(CASE WHEN d.over < 6 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as pp_dots,
                    SUM(CASE WHEN d.over < 6 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as pp_boundaries,
                    
                    -- Middle overs stats (6-15 overs)
                    SUM(CASE WHEN d.over >= 6 AND d.over < 15 THEN 1 ELSE 0 END) as middle_balls,
                    SUM(CASE WHEN d.over >= 6 AND d.over < 15 THEN d.runs_off_bat + d.extras ELSE 0 END) as middle_runs,
                    SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.wicket_type IS NOT NULL 
                        AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                    THEN 1 ELSE 0 END) as middle_wickets,
                    SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as middle_dots,
                    SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as middle_boundaries,
                    
                    -- Death overs stats (15-20 overs)
                    SUM(CASE WHEN d.over >= 15 THEN 1 ELSE 0 END) as death_balls,
                    SUM(CASE WHEN d.over >= 15 THEN d.runs_off_bat + d.extras ELSE 0 END) as death_runs,
                    SUM(CASE WHEN d.over >= 15 AND d.wicket_type IS NOT NULL 
                        AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                    THEN 1 ELSE 0 END) as death_wickets,
                    SUM(CASE WHEN d.over >= 15 AND d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as death_dots,
                    SUM(CASE WHEN d.over >= 15 AND d.runs_off_bat >= 4 THEN 1 ELSE 0 END) as death_boundaries
                    
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                JOIN players p ON d.bowler = p.name
                JOIN BowlerTypes bt ON p.name = bt.name
                WHERE d.batter = ANY(:players)
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                GROUP BY d.batter, bt.bowler_type
            ),
            PlayerTotals AS (
                SELECT
                    batter,
                    SUM(balls) as total_balls,
                    SUM(pp_balls) as total_pp_balls,
                    CAST(SUM(pp_balls) * 100.0 / NULLIF(SUM(balls), 0) AS DECIMAL(10,2)) as pp_percentage
                FROM PlayerStats
                GROUP BY batter
            )
            SELECT
                ps.batter,
                ps.bowler_type,
                pt.pp_percentage,
                
                -- All relevant stats fields for each phase
                ps.balls, ps.runs, ps.wickets, ps.dots, ps.boundaries,
                ps.pp_balls, ps.pp_runs, ps.pp_wickets, ps.pp_dots, ps.pp_boundaries,
                ps.middle_balls, ps.middle_runs, ps.middle_wickets, ps.middle_dots, ps.middle_boundaries,
                ps.death_balls, ps.death_runs, ps.death_wickets, ps.death_dots, ps.death_boundaries,
                
                -- Calculated metrics for each phase
                CAST((ps.runs * 100.0) / NULLIF(ps.balls, 0) AS DECIMAL(10,2)) as strike_rate,
                CAST(ps.runs / NULLIF(ps.wickets, 0) AS DECIMAL(10,2)) as average,
                CAST((ps.dots * 100.0) / NULLIF(ps.balls, 0) AS DECIMAL(10,2)) as dot_percentage,
                CAST((ps.boundaries * 100.0) / NULLIF(ps.balls, 0) AS DECIMAL(10,2)) as boundary_percentage,
                
                CAST((ps.pp_runs * 100.0) / NULLIF(ps.pp_balls, 0) AS DECIMAL(10,2)) as pp_strike_rate,
                CAST(ps.pp_runs / NULLIF(ps.pp_wickets, 0) AS DECIMAL(10,2)) as pp_average,
                CAST((ps.pp_dots * 100.0) / NULLIF(ps.pp_balls, 0) AS DECIMAL(10,2)) as pp_dot_percentage,
                CAST((ps.pp_boundaries * 100.0) / NULLIF(ps.pp_balls, 0) AS DECIMAL(10,2)) as pp_boundary_percentage,
                
                CAST((ps.middle_runs * 100.0) / NULLIF(ps.middle_balls, 0) AS DECIMAL(10,2)) as middle_strike_rate,
                CAST(ps.middle_runs / NULLIF(ps.middle_wickets, 0) AS DECIMAL(10,2)) as middle_average,
                CAST((ps.middle_dots * 100.0) / NULLIF(ps.middle_balls, 0) AS DECIMAL(10,2)) as middle_dot_percentage,
                CAST((ps.middle_boundaries * 100.0) / NULLIF(ps.middle_balls, 0) AS DECIMAL(10,2)) as middle_boundary_percentage,
                
                CAST((ps.death_runs * 100.0) / NULLIF(ps.death_balls, 0) AS DECIMAL(10,2)) as death_strike_rate,
                CAST(ps.death_runs / NULLIF(ps.death_wickets, 0) AS DECIMAL(10,2)) as death_average,
                CAST((ps.death_dots * 100.0) / NULLIF(ps.death_balls, 0) AS DECIMAL(10,2)) as death_dot_percentage,
                CAST((ps.death_boundaries * 100.0) / NULLIF(ps.death_balls, 0) AS DECIMAL(10,2)) as death_boundary_percentage
                
            FROM PlayerStats ps
            JOIN PlayerTotals pt ON ps.batter = pt.batter
            ORDER BY pt.pp_percentage DESC, ps.batter, ps.bowler_type
        """)
        
        # Execute the query
        results = db.execute(query, params).fetchall()
        
        # Transform the results into a structured format
        players_data = {}
        bowling_types = set()
        
        for row in results:
            player = row.batter
            bowling_type = row.bowler_type
            
            bowling_types.add(bowling_type)
            
            if player not in players_data:
                players_data[player] = {
                    "pp_percentage": float(row.pp_percentage) if row.pp_percentage else 0,
                    "bowling_types": {}
                }
            
            # Select the appropriate stats based on the requested phase
            if phase == "overall":
                stats = {
                    "balls": row.balls,
                    "runs": row.runs,
                    "wickets": row.wickets,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                    "average": float(row.average) if row.average else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
                }
            elif phase == "powerplay":
                stats = {
                    "balls": row.pp_balls,
                    "runs": row.pp_runs,
                    "wickets": row.pp_wickets,
                    "strike_rate": float(row.pp_strike_rate) if row.pp_strike_rate else 0,
                    "average": float(row.pp_average) if row.pp_average else 0,
                    "dot_percentage": float(row.pp_dot_percentage) if row.pp_dot_percentage else 0,
                    "boundary_percentage": float(row.pp_boundary_percentage) if row.pp_boundary_percentage else 0
                }
            elif phase == "middle":
                stats = {
                    "balls": row.middle_balls,
                    "runs": row.middle_runs,
                    "wickets": row.middle_wickets,
                    "strike_rate": float(row.middle_strike_rate) if row.middle_strike_rate else 0,
                    "average": float(row.middle_average) if row.middle_average else 0,
                    "dot_percentage": float(row.middle_dot_percentage) if row.middle_dot_percentage else 0,
                    "boundary_percentage": float(row.middle_boundary_percentage) if row.middle_boundary_percentage else 0
                }
            elif phase == "death":
                stats = {
                    "balls": row.death_balls,
                    "runs": row.death_runs,
                    "wickets": row.death_wickets,
                    "strike_rate": float(row.death_strike_rate) if row.death_strike_rate else 0,
                    "average": float(row.death_average) if row.death_average else 0,
                    "dot_percentage": float(row.death_dot_percentage) if row.death_dot_percentage else 0,
                    "boundary_percentage": float(row.death_boundary_percentage) if row.death_boundary_percentage else 0
                }
            
            players_data[player]["bowling_types"][bowling_type] = stats
        
        # Convert to the final response format
        response = {
            "players": [
                {
                    "name": player,
                    "pp_percentage": data["pp_percentage"],
                    "bowling_types": data["bowling_types"]
                }
                for player, data in players_data.items()
            ],
            "bowling_types": sorted(list(bowling_types)),
            "phase": phase
        }
        
        return response
        
    except Exception as e:
        logging.error(f"Error getting bowling type matchups: {str(e)}")
        logging.error("Traceback:", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/venues/{venue}/teams/{team1}/{team2}/fantasy_stats")
def get_venue_team_fantasy_stats(
    venue: str,
    team1: str,
    team2: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_session)
):
    try:
        # Get all possible team name variations
        team1_names = get_all_team_name_variations(team1)
        team2_names = get_all_team_name_variations(team2)
        
        # Common query structure to combine batting and bowling stats for a team
        fantasy_query = """
        WITH venue_matches AS (
            SELECT id FROM matches 
            WHERE venue = :venue
            AND (:start_date IS NULL OR date >= :start_date)
            AND (:end_date IS NULL OR date <= :end_date)
        ),
        batting_stats_agg AS (
            -- Aggregate batting stats
            SELECT 
                bs.striker as player_name,
                bs.batting_team as team,
                COUNT(DISTINCT bs.match_id) as matches_played,
                ROUND(AVG(bs.fantasy_points)::numeric, 2) as avg_fantasy_points,
                ROUND(AVG(bs.batting_points)::numeric, 2) as avg_batting_points,
                ROUND(AVG(bs.bowling_points)::numeric, 2) as avg_bowling_points,
                ROUND(AVG(bs.fielding_points)::numeric, 2) as avg_fielding_points
            FROM 
                batting_stats bs
            JOIN 
                venue_matches vm ON bs.match_id = vm.id
            WHERE 
                bs.batting_team = ANY(:team_names)
            GROUP BY 
                bs.striker, bs.batting_team
        ),
        bowling_stats_agg AS (
            -- Aggregate bowling stats for the same players
            SELECT 
                bw.bowler as player_name,
                bw.bowling_team as team,
                COUNT(DISTINCT bw.match_id) as matches_played,
                ROUND(AVG(bw.fantasy_points)::numeric, 2) as avg_fantasy_points,
                ROUND(AVG(bw.batting_points)::numeric, 2) as avg_batting_points,
                ROUND(AVG(bw.bowling_points)::numeric, 2) as avg_bowling_points,
                ROUND(AVG(bw.fielding_points)::numeric, 2) as avg_fielding_points
            FROM 
                bowling_stats bw
            JOIN 
                venue_matches vm ON bw.match_id = vm.id
            WHERE 
                bw.bowling_team = ANY(:team_names)
            GROUP BY 
                bw.bowler, bw.bowling_team
        ),
        combined_stats AS (
            -- Use COALESCE to handle players who only bat or only bowl
            SELECT 
                COALESCE(bat.player_name, bowl.player_name) as player_name,
                COALESCE(bat.team, bowl.team) as team,
                GREATEST(COALESCE(bat.matches_played, 0), COALESCE(bowl.matches_played, 0)) as matches_played,
                COALESCE(bat.avg_fantasy_points, 0) + COALESCE(bowl.avg_fantasy_points, 0) as avg_fantasy_points,
                COALESCE(bat.avg_batting_points, 0) as avg_batting_points,
                COALESCE(bowl.avg_bowling_points, 0) as avg_bowling_points,
                COALESCE(bat.avg_fielding_points, bowl.avg_fielding_points, 0) as avg_fielding_points
            FROM 
                batting_stats_agg bat
            FULL OUTER JOIN
                bowling_stats_agg bowl ON bat.player_name = bowl.player_name AND bat.team = bowl.team
        )
        SELECT * FROM combined_stats
        ORDER BY avg_fantasy_points DESC NULLS LAST
        """
        
        # Execute for team 1
        team1_result = db.execute(
            text(fantasy_query),
            {
                "venue": venue, 
                "team_names": team1_names,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()

        # Execute for team 2
        team2_result = db.execute(
            text(fantasy_query),
            {
                "venue": venue, 
                "team_names": team2_names,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()

        # Format results for JSON response
        team1_stats = [
            {
                "player_name": row.player_name,
                "team": row.team,
                "matches_played": row.matches_played,
                "avg_fantasy_points": float(row.avg_fantasy_points) if row.avg_fantasy_points else 0,
                "avg_batting_points": float(row.avg_batting_points) if row.avg_batting_points else 0,
                "avg_bowling_points": float(row.avg_bowling_points) if row.avg_bowling_points else 0,
                "avg_fielding_points": float(row.avg_fielding_points) if row.avg_fielding_points else 0
            }
            for row in team1_result
        ]

        team2_stats = [
            {
                "player_name": row.player_name,
                "team": row.team,
                "matches_played": row.matches_played,
                "avg_fantasy_points": float(row.avg_fantasy_points) if row.avg_fantasy_points else 0,
                "avg_batting_points": float(row.avg_batting_points) if row.avg_batting_points else 0,
                "avg_bowling_points": float(row.avg_bowling_points) if row.avg_bowling_points else 0,
                "avg_fielding_points": float(row.avg_fielding_points) if row.avg_fielding_points else 0
            }
            for row in team2_result
        ]
        
        return {
            "team1_players": team1_stats,
            "team2_players": team2_stats
        }
        
    except Exception as e:
        logging.error(f"Error getting venue team fantasy stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/venues/{venue}/players/fantasy_history")
def get_venue_player_fantasy_history(
    venue: str,
    team1: Optional[str] = None,
    team2: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_session)
):
    try:
        # Get all possible team name variations if teams are specified
        team1_names = get_all_team_name_variations(team1) if team1 else []
        team2_names = get_all_team_name_variations(team2) if team2 else []
        
        # Combined query to get both batting and bowling stats
        combined_query = """
        WITH venue_matches AS (
            SELECT id FROM matches 
            WHERE venue = :venue
            AND (:start_date IS NULL OR date >= :start_date)
            AND (:end_date IS NULL OR date <= :end_date)
        ),
        player_teams AS (
            -- Get current team for each player (assuming most recent team)
            SELECT DISTINCT ON (player_name) 
                CASE 
                    WHEN team = ANY(:team1_names) THEN :team1 
                    WHEN team = ANY(:team2_names) THEN :team2
                    ELSE team 
                END as team,
                player_name
            FROM (
                SELECT bs.striker as player_name, bs.batting_team as team, m.date
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE (:team1 IS NULL OR :team2 IS NULL OR 
                      (bs.batting_team = ANY(:team1_names) OR bs.batting_team = ANY(:team2_names)))
                ORDER BY m.date DESC
            ) recent_teams
        ),
        batting_stats_agg AS (
            -- Aggregate batting stats
            SELECT 
                bs.striker as player_name,
                COUNT(DISTINCT bs.match_id) as matches_played,
                ROUND(AVG(bs.fantasy_points)::numeric, 2) as avg_fantasy_points,
                ROUND(AVG(bs.batting_points)::numeric, 2) as avg_batting_points,
                ROUND(AVG(bs.bowling_points)::numeric, 2) as avg_bowling_points,
                ROUND(AVG(bs.fielding_points)::numeric, 2) as avg_fielding_points
            FROM 
                batting_stats bs
            JOIN 
                venue_matches vm ON bs.match_id = vm.id
            GROUP BY 
                bs.striker
        ),
        bowling_stats_agg AS (
            -- Aggregate bowling stats for the same players
            SELECT 
                bw.bowler as player_name,
                COUNT(DISTINCT bw.match_id) as matches_played,
                ROUND(AVG(bw.fantasy_points)::numeric, 2) as avg_fantasy_points,
                ROUND(AVG(bw.batting_points)::numeric, 2) as avg_batting_points,
                ROUND(AVG(bw.bowling_points)::numeric, 2) as avg_bowling_points,
                ROUND(AVG(bw.fielding_points)::numeric, 2) as avg_fielding_points
            FROM 
                bowling_stats bw
            JOIN 
                venue_matches vm ON bw.match_id = vm.id
            GROUP BY 
                bw.bowler
        ),
        combined_stats AS (
            -- Combine batting and bowling stats
            SELECT 
                COALESCE(bat.player_name, bowl.player_name) as player_name,
                GREATEST(COALESCE(bat.matches_played, 0), COALESCE(bowl.matches_played, 0)) as matches_played,
                COALESCE(bat.avg_fantasy_points, 0) + COALESCE(bowl.avg_fantasy_points, 0) as avg_fantasy_points,
                COALESCE(bat.avg_batting_points, 0) as avg_batting_points,
                COALESCE(bowl.avg_bowling_points, 0) as avg_bowling_points,
                COALESCE(bat.avg_fielding_points, bowl.avg_fielding_points, 0) as avg_fielding_points
            FROM 
                batting_stats_agg bat
            FULL OUTER JOIN
                bowling_stats_agg bowl ON bat.player_name = bowl.player_name
        )
        SELECT 
            cs.player_name,
            pt.team,
            cs.matches_played,
            cs.avg_fantasy_points,
            cs.avg_batting_points,
            cs.avg_bowling_points,
            cs.avg_fielding_points
        FROM 
            combined_stats cs
        JOIN
            player_teams pt ON cs.player_name = pt.player_name
        WHERE
            (:team1 IS NULL OR :team2 IS NULL OR pt.team IN (:team1, :team2))
        ORDER BY 
            cs.avg_fantasy_points DESC NULLS LAST
        """
        
        # Execute the query
        results = db.execute(
            text(combined_query),
            {
                "venue": venue,
                "team1": team1,
                "team2": team2,
                "team1_names": team1_names,
                "team2_names": team2_names,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()
        
        # Format results for JSON response
        player_stats = [
            {
                "player_name": row.player_name,
                "team": row.team,
                "matches_played": row.matches_played,
                "avg_fantasy_points": float(row.avg_fantasy_points) if row.avg_fantasy_points else 0,
                "avg_batting_points": float(row.avg_batting_points) if row.avg_batting_points else 0,
                "avg_bowling_points": float(row.avg_bowling_points) if row.avg_bowling_points else 0,
                "avg_fielding_points": float(row.avg_fielding_points) if row.avg_fielding_points else 0
            }
            for row in results
        ]
        
        return {
            "players": player_stats
        }
        
    except Exception as e:
        logging.error(f"Error getting venue player fantasy history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/teams/{team1}/{team2}/fantasy_stats")
def get_team_fantasy_stats(
    team1: str,
    team2: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_session)
):
    try:
        # Get all possible team name variations
        team1_names = get_all_team_name_variations(team1)
        team2_names = get_all_team_name_variations(team2)
        
        # Common query structure to combine batting and bowling stats for a team
        fantasy_query = """
        WITH match_filter AS (
            SELECT id FROM matches 
            WHERE (:start_date IS NULL OR date >= :start_date)
            AND (:end_date IS NULL OR date <= :end_date)
        ),
        batting_stats_agg AS (
            -- Aggregate batting stats
            SELECT 
                bs.striker as player_name,
                bs.batting_team as team,
                COUNT(DISTINCT bs.match_id) as matches_played,
                ROUND(AVG(bs.fantasy_points)::numeric, 2) as avg_fantasy_points,
                ROUND(AVG(bs.batting_points)::numeric, 2) as avg_batting_points,
                ROUND(AVG(bs.bowling_points)::numeric, 2) as avg_bowling_points,
                ROUND(AVG(bs.fielding_points)::numeric, 2) as avg_fielding_points
            FROM 
                batting_stats bs
            JOIN 
                match_filter mf ON bs.match_id = mf.id
            WHERE 
                bs.batting_team = ANY(:team_names)
            GROUP BY 
                bs.striker, bs.batting_team
        ),
        bowling_stats_agg AS (
            -- Aggregate bowling stats for the same players
            SELECT 
                bw.bowler as player_name,
                bw.bowling_team as team,
                COUNT(DISTINCT bw.match_id) as matches_played,
                ROUND(AVG(bw.fantasy_points)::numeric, 2) as avg_fantasy_points,
                ROUND(AVG(bw.batting_points)::numeric, 2) as avg_batting_points,
                ROUND(AVG(bw.bowling_points)::numeric, 2) as avg_bowling_points,
                ROUND(AVG(bw.fielding_points)::numeric, 2) as avg_fielding_points
            FROM 
                bowling_stats bw
            JOIN 
                match_filter mf ON bw.match_id = mf.id
            WHERE 
                bw.bowling_team = ANY(:team_names)
            GROUP BY 
                bw.bowler, bw.bowling_team
        ),
        combined_stats AS (
            -- Use COALESCE to handle players who only bat or only bowl
            SELECT 
                COALESCE(bat.player_name, bowl.player_name) as player_name,
                COALESCE(bat.team, bowl.team) as team,
                GREATEST(COALESCE(bat.matches_played, 0), COALESCE(bowl.matches_played, 0)) as matches_played,
                COALESCE(bat.avg_fantasy_points, 0) + COALESCE(bowl.avg_fantasy_points, 0) as avg_fantasy_points,
                COALESCE(bat.avg_batting_points, 0) as avg_batting_points,
                COALESCE(bowl.avg_bowling_points, 0) as avg_bowling_points,
                COALESCE(bat.avg_fielding_points, bowl.avg_fielding_points, 0) as avg_fielding_points
            FROM 
                batting_stats_agg bat
            FULL OUTER JOIN
                bowling_stats_agg bowl ON bat.player_name = bowl.player_name AND bat.team = bowl.team
        )
        SELECT * FROM combined_stats
        ORDER BY avg_fantasy_points DESC NULLS LAST
        """
        
        # Execute for team 1
        team1_result = db.execute(
            text(fantasy_query),
            {
                "team_names": team1_names,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()

        # Execute for team 2
        team2_result = db.execute(
            text(fantasy_query),
            {
                "team_names": team2_names,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()

        # Format results for JSON response
        team1_stats = [
            {
                "player_name": row.player_name,
                "team": row.team,
                "matches_played": row.matches_played,
                "avg_fantasy_points": float(row.avg_fantasy_points) if row.avg_fantasy_points else 0,
                "avg_batting_points": float(row.avg_batting_points) if row.avg_batting_points else 0,
                "avg_bowling_points": float(row.avg_bowling_points) if row.avg_bowling_points else 0,
                "avg_fielding_points": float(row.avg_fielding_points) if row.avg_fielding_points else 0
            }
            for row in team1_result
        ]

        team2_stats = [
            {
                "player_name": row.player_name,
                "team": row.team,
                "matches_played": row.matches_played,
                "avg_fantasy_points": float(row.avg_fantasy_points) if row.avg_fantasy_points else 0,
                "avg_batting_points": float(row.avg_batting_points) if row.avg_batting_points else 0,
                "avg_bowling_points": float(row.avg_bowling_points) if row.avg_bowling_points else 0,
                "avg_fielding_points": float(row.avg_fielding_points) if row.avg_fielding_points else 0
            }
            for row in team2_result
        ]
        
        return {
            "team1_players": team1_stats,
            "team2_players": team2_stats
        }
        
    except Exception as e:
        logging.error(f"Error getting team fantasy stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/custom-matchups/fantasy_stats")
def get_custom_matchup_fantasy_stats(
    team1_players: List[str] = Query(...),
    team2_players: List[str] = Query(...),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_session)
):
    try:
        # Query for retrieving fantasy stats for a list of players
        player_query = """
        WITH match_filter AS (
            SELECT id FROM matches 
            WHERE (:start_date IS NULL OR date >= :start_date)
            AND (:end_date IS NULL OR date <= :end_date)
        ),
        batting_stats_agg AS (
            -- Aggregate batting stats
            SELECT 
                bs.striker as player_name,
                COUNT(DISTINCT bs.match_id) as matches_played,
                ROUND(AVG(bs.fantasy_points)::numeric, 2) as avg_fantasy_points,
                ROUND(AVG(bs.batting_points)::numeric, 2) as avg_batting_points,
                ROUND(AVG(bs.bowling_points)::numeric, 2) as avg_bowling_points,
                ROUND(AVG(bs.fielding_points)::numeric, 2) as avg_fielding_points
            FROM 
                batting_stats bs
            JOIN 
                match_filter mf ON bs.match_id = mf.id
            WHERE 
                bs.striker = ANY(:player_list)
            GROUP BY 
                bs.striker
        ),
        bowling_stats_agg AS (
            -- Aggregate bowling stats for the same players
            SELECT 
                bw.bowler as player_name,
                COUNT(DISTINCT bw.match_id) as matches_played,
                ROUND(AVG(bw.fantasy_points)::numeric, 2) as avg_fantasy_points,
                ROUND(AVG(bw.batting_points)::numeric, 2) as avg_batting_points,
                ROUND(AVG(bw.bowling_points)::numeric, 2) as avg_bowling_points,
                ROUND(AVG(bw.fielding_points)::numeric, 2) as avg_fielding_points
            FROM 
                bowling_stats bw
            JOIN 
                match_filter mf ON bw.match_id = mf.id
            WHERE 
                bw.bowler = ANY(:player_list)
            GROUP BY 
                bw.bowler
        ),
        player_latest_team AS (
            -- Get the most recent team for each player
            SELECT DISTINCT ON (player_name) 
                player_name, team
            FROM (
                SELECT 
                    bs.striker as player_name, 
                    bs.batting_team as team,
                    m.date
                FROM 
                    batting_stats bs
                JOIN 
                    matches m ON bs.match_id = m.id
                WHERE 
                    bs.striker = ANY(:player_list)
                UNION ALL
                SELECT 
                    bw.bowler as player_name, 
                    bw.bowling_team as team,
                    m.date
                FROM 
                    bowling_stats bw
                JOIN 
                    matches m ON bw.match_id = m.id
                WHERE 
                    bw.bowler = ANY(:player_list)
            ) all_teams
            ORDER BY player_name, date DESC
        ),
        combined_stats AS (
            -- Combine batting and bowling stats
            SELECT 
                COALESCE(bat.player_name, bowl.player_name) as player_name,
                GREATEST(COALESCE(bat.matches_played, 0), COALESCE(bowl.matches_played, 0)) as matches_played,
                COALESCE(bat.avg_fantasy_points, 0) + COALESCE(bowl.avg_fantasy_points, 0) as avg_fantasy_points,
                COALESCE(bat.avg_batting_points, 0) as avg_batting_points,
                COALESCE(bowl.avg_bowling_points, 0) as avg_bowling_points,
                COALESCE(bat.avg_fielding_points, bowl.avg_fielding_points, 0) as avg_fielding_points
            FROM 
                batting_stats_agg bat
            FULL OUTER JOIN
                bowling_stats_agg bowl ON bat.player_name = bowl.player_name
        )
        SELECT 
            cs.player_name,
            plt.team,
            cs.matches_played,
            cs.avg_fantasy_points,
            cs.avg_batting_points,
            cs.avg_bowling_points,
            cs.avg_fielding_points
        FROM 
            combined_stats cs
        LEFT JOIN
            player_latest_team plt ON cs.player_name = plt.player_name
        ORDER BY 
            cs.avg_fantasy_points DESC NULLS LAST
        """
        
        # Execute for team 1 players
        team1_result = db.execute(
            text(player_query),
            {
                "player_list": team1_players,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()

        # Execute for team 2 players
        team2_result = db.execute(
            text(player_query),
            {
                "player_list": team2_players,
                "start_date": start_date,
                "end_date": end_date
            }
        ).fetchall()

        # Format results for JSON response
        team1_stats = [
            {
                "player_name": row.player_name,
                "team": row.team,
                "matches_played": row.matches_played,
                "avg_fantasy_points": float(row.avg_fantasy_points) if row.avg_fantasy_points else 0,
                "avg_batting_points": float(row.avg_batting_points) if row.avg_batting_points else 0,
                "avg_bowling_points": float(row.avg_bowling_points) if row.avg_bowling_points else 0,
                "avg_fielding_points": float(row.avg_fielding_points) if row.avg_fielding_points else 0
            }
            for row in team1_result
        ]

        team2_stats = [
            {
                "player_name": row.player_name,
                "team": row.team,
                "matches_played": row.matches_played,
                "avg_fantasy_points": float(row.avg_fantasy_points) if row.avg_fantasy_points else 0,
                "avg_batting_points": float(row.avg_batting_points) if row.avg_batting_points else 0,
                "avg_bowling_points": float(row.avg_bowling_points) if row.avg_bowling_points else 0,
                "avg_fielding_points": float(row.avg_fielding_points) if row.avg_fielding_points else 0
            }
            for row in team2_result
        ]
        
        return {
            "team1_players": team1_stats,
            "team2_players": team2_stats
        }
        
    except Exception as e:
        logging.error(f"Error getting custom matchup fantasy stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def balls_to_overs(balls):
    """Convert balls to overs format (e.g., 9 balls = 1.3 overs)"""
    if not balls:
        return 0.0
    complete_overs = balls // 6
    remaining_balls = balls % 6
    return float(complete_overs) + (remaining_balls / 10.0)

def overs_to_balls(overs):
    """Convert overs to balls (e.g., 1.3 overs = 9 balls)"""
    if not overs:
        return 0
    complete_overs = int(overs)
    fractional_overs = overs - complete_overs
    return (complete_overs * 6) + int(fractional_overs * 10)

@app.get("/player/{player_name}/bowling_stats")
def get_player_bowling_stats(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    db: Session = Depends(get_session)
):
    try:
        logger.info(f"Received params for bowling stats - start_date: {start_date}, end_date: {end_date}, leagues: {leagues}, include_international: {include_international}")

        params = {
            "player_name": player_name,
            "start_date": start_date,
            "end_date": end_date,
            "venue": venue,
            "has_leagues": bool(leagues),
            "include_international": include_international,
            "top_teams": top_teams is not None,
            "top_team_list": INTERNATIONAL_TEAMS_RANKED[:top_teams] if top_teams else []
        }
        
        # If leagues are provided, expand them to include full names
        if leagues:
            params["leagues"] = expand_league_abbreviations(leagues)
        else:
            params["leagues"] = []

        match_filter = """
            AND (
                (:has_leagues AND m.match_type = 'league' AND m.competition = ANY(:leagues))
                OR (:include_international AND m.match_type = 'international' 
                    AND (:top_teams IS NULL OR 
                        (m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list))
                    )
                )
            )
        """

        # SIMPLIFIED: Overall bowling stats using pre-calculated data + legal deliveries count
        overall_query = text(f"""
            WITH legal_balls_summary AS (
                SELECT 
                    bs.bowler,
                    COUNT(*) as total_legal_balls,
                    SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries
                FROM bowling_stats bs
                JOIN deliveries d ON bs.match_id = d.match_id AND bs.bowler = d.bowler AND bs.innings = d.innings
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.bowler = :player_name
                AND d.wides = 0 AND d.noballs = 0  -- Only legal deliveries
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                AND (:venue IS NULL OR m.venue = :venue)
                {match_filter}
                GROUP BY bs.bowler
            )
            SELECT
                COUNT(DISTINCT bs.match_id) as matches,
                SUM(bs.runs_conceded) as runs_conceded,
                SUM(bs.wickets) as wickets,
                SUM(bs.dots) as dots,
                COUNT(CASE WHEN bs.wickets >= 3 AND bs.wickets < 5 THEN 1 END) as three_wicket_hauls,
                COUNT(CASE WHEN bs.wickets >= 5 THEN 1 END) as five_wicket_hauls,
                lbs.total_legal_balls as legal_balls,
                lbs.boundaries,
                -- Pre-calculated metrics
                CAST(SUM(bs.runs_conceded) AS FLOAT) / NULLIF(SUM(bs.wickets), 0) as bowling_average,
                CAST(lbs.total_legal_balls AS FLOAT) / NULLIF(SUM(bs.wickets), 0) as bowling_strike_rate,
                CAST(SUM(bs.runs_conceded) * 6.0 AS FLOAT) / NULLIF(lbs.total_legal_balls, 0) as economy_rate,
                CAST(SUM(bs.dots) * 100.0 AS FLOAT) / NULLIF(lbs.total_legal_balls, 0) as dot_percentage
            FROM bowling_stats bs
            JOIN matches m ON bs.match_id = m.id
            JOIN legal_balls_summary lbs ON bs.bowler = lbs.bowler
            WHERE bs.bowler = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            GROUP BY lbs.total_legal_balls, lbs.boundaries
        """)

        # SIMPLIFIED: Maidens calculation - more efficient approach
        maidens_query = text(f"""
            SELECT COUNT(DISTINCT CONCAT(d.match_id, '_', d.innings, '_', d.over)) as maidens
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE d.bowler = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            AND d.match_id || '_' || d.innings || '_' || d.over IN (
                -- Only complete overs with 6 legal balls and 0 runs
                SELECT CONCAT(match_id, '_', innings, '_', over)
                FROM deliveries
                WHERE bowler = :player_name AND wides = 0 AND noballs = 0
                GROUP BY match_id, innings, over
                HAVING COUNT(*) = 6 AND SUM(runs_off_bat + extras) = 0
            )
        """)

        # SIMPLIFIED: Phase stats using pre-calculated columns + legal ball counts
        phase_query = text(f"""
            WITH phase_legal_balls AS (
                SELECT 
                    SUM(CASE WHEN d.over < 6 THEN 1 ELSE 0 END) as pp_legal_balls,
                    SUM(CASE WHEN d.over >= 6 AND d.over < 15 THEN 1 ELSE 0 END) as middle_legal_balls,
                    SUM(CASE WHEN d.over >= 15 THEN 1 ELSE 0 END) as death_legal_balls
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.bowler = :player_name
                AND d.wides = 0 AND d.noballs = 0  -- Only legal deliveries
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                AND (:venue IS NULL OR m.venue = :venue)
                {match_filter}
            )
            SELECT 
                -- Use pre-calculated phase stats from bowling_stats
                SUM(bs.pp_runs) as pp_runs,
                SUM(bs.pp_wickets) as pp_wickets,
                SUM(bs.pp_dots) as pp_dots,
                SUM(bs.pp_boundaries) as pp_boundaries,
                
                SUM(bs.middle_runs) as middle_runs,
                SUM(bs.middle_wickets) as middle_wickets,
                SUM(bs.middle_dots) as middle_dots,
                SUM(bs.middle_boundaries) as middle_boundaries,
                
                SUM(bs.death_runs) as death_runs,
                SUM(bs.death_wickets) as death_wickets,
                SUM(bs.death_dots) as death_dots,
                SUM(bs.death_boundaries) as death_boundaries,
                
                -- Legal ball counts from CTE
                plb.pp_legal_balls,
                plb.middle_legal_balls,
                plb.death_legal_balls
            FROM bowling_stats bs
            JOIN matches m ON bs.match_id = m.id
            CROSS JOIN phase_legal_balls plb
            WHERE bs.bowler = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            GROUP BY plb.pp_legal_balls, plb.middle_legal_balls, plb.death_legal_balls
        """)

        # SIMPLIFIED: Over distribution - already efficient, minor cleanup
        over_distribution_query = text(f"""
            SELECT 
                d.over as over_number,
                COUNT(DISTINCT CONCAT(d.match_id, '_', d.innings)) as instances_bowled,
                SUM(d.runs_off_bat + d.extras) as runs,
                COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) as legal_balls,
                SUM(CASE WHEN d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                COUNT(DISTINCT d.match_id) as matches_bowled_in
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE d.bowler = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            GROUP BY d.over
            ORDER BY d.over
        """)

        # SIMPLIFIED: Batter handedness with legal balls only
        batter_handedness_query = text(f"""
            SELECT 
                p.batting_hand,
                COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) as legal_balls,
                SUM(d.runs_off_bat + d.extras) as runs,
                SUM(CASE WHEN d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                
                -- Phase-wise legal balls only
                COUNT(CASE WHEN d.over < 6 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as pp_legal_balls,
                SUM(CASE WHEN d.over < 6 THEN d.runs_off_bat + d.extras ELSE 0 END) as pp_runs,
                SUM(CASE WHEN d.over < 6 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as pp_wickets,
                
                COUNT(CASE WHEN d.over >= 6 AND d.over < 15 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as middle_legal_balls,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 THEN d.runs_off_bat + d.extras ELSE 0 END) as middle_runs,
                SUM(CASE WHEN d.over >= 6 AND d.over < 15 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as middle_wickets,
                
                COUNT(CASE WHEN d.over >= 15 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as death_legal_balls,
                SUM(CASE WHEN d.over >= 15 THEN d.runs_off_bat + d.extras ELSE 0 END) as death_runs,
                SUM(CASE WHEN d.over >= 15 AND d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                THEN 1 ELSE 0 END) as death_wickets
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            JOIN players p ON d.batter = p.name
            WHERE d.bowler = :player_name
            AND p.batting_hand IS NOT NULL
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            GROUP BY p.batting_hand
        """)

        # SIMPLIFIED: Innings query using bowling_stats + legal ball counts
        innings_query = text(f"""
            WITH innings_legal_balls AS (
                SELECT 
                    d.match_id,
                    d.innings,
                    COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) as legal_balls,
                    COUNT(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 END) as boundaries,
                    -- Phase-wise legal balls
                    COUNT(CASE WHEN d.over < 6 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as pp_legal_balls,
                    COUNT(CASE WHEN d.over >= 6 AND d.over < 15 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as middle_legal_balls,
                    COUNT(CASE WHEN d.over >= 15 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as death_legal_balls
                FROM deliveries d
                WHERE d.bowler = :player_name
                GROUP BY d.match_id, d.innings
            )
            SELECT 
                m.id as match_id,
                m.date,
                m.venue,
                m.competition,
                m.winner,
                bs.*,
                ilb.legal_balls,
                ilb.boundaries,
                ilb.pp_legal_balls,
                ilb.middle_legal_balls,
                ilb.death_legal_balls,
                CASE 
                    WHEN m.team1 = bs.bowling_team THEN m.team2 
                    ELSE m.team1 
                END as batting_team
            FROM bowling_stats bs
            JOIN matches m ON bs.match_id = m.id
            JOIN innings_legal_balls ilb ON bs.match_id = ilb.match_id AND bs.innings = ilb.innings
            WHERE bs.bowler = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            ORDER BY m.date DESC
        """)

        # SIMPLIFIED: Maidens per innings
        innings_maidens_query = text(f"""
            SELECT 
                d.match_id,
                d.innings,
                COUNT(DISTINCT d.over) as maidens
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE d.bowler = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            AND CONCAT(d.match_id, '_', d.innings, '_', d.over) IN (
                SELECT CONCAT(match_id, '_', innings, '_', over)
                FROM deliveries
                WHERE bowler = :player_name AND wides = 0 AND noballs = 0
                GROUP BY match_id, innings, over
                HAVING COUNT(*) = 6 AND SUM(runs_off_bat + extras) = 0
            )
            GROUP BY d.match_id, d.innings
        """)

        # SIMPLIFIED: Over combinations - keep existing logic but optimize
        over_combinations_query = text(f"""
            WITH bowler_overs AS (
                SELECT 
                    d.match_id,
                    d.innings,
                    d.over,
                    COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) as legal_balls,
                    SUM(d.runs_off_bat + d.extras) as runs_in_over,
                    SUM(CASE WHEN d.wicket_type IS NOT NULL 
                        AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                    THEN 1 ELSE 0 END) as wickets_in_over
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.bowler = :player_name
                AND (:start_date IS NULL OR m.date >= :start_date)
                AND (:end_date IS NULL OR m.date <= :end_date)
                AND (:venue IS NULL OR m.venue = :venue)
                {match_filter}
                GROUP BY d.match_id, d.innings, d.over
                HAVING COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) >= 5
            ),
            innings_overs AS (
                SELECT 
                    match_id,
                    innings,
                    ARRAY_AGG(over ORDER BY over) as overs_bowled,
                    COUNT(*) as num_overs,
                    SUM(runs_in_over) as total_runs,
                    SUM(wickets_in_over) as total_wickets
                FROM bowler_overs
                GROUP BY match_id, innings
                HAVING COUNT(*) = 4
            ),
            over_combinations AS (
                SELECT 
                    overs_bowled,
                    COUNT(*) as frequency,
                    SUM(total_runs) as runs,
                    SUM(total_wickets) as wickets
                FROM innings_overs
                GROUP BY overs_bowled
                ORDER BY frequency DESC, overs_bowled
            )
            SELECT 
                overs_bowled,
                frequency,
                runs,
                wickets,
                CAST(runs * 1.0 / (frequency * 4) AS DECIMAL(10,2)) as economy,
                CAST(wickets * 1.0 / frequency AS DECIMAL(10,2)) as wickets_per_innings
            FROM over_combinations
            ORDER BY frequency DESC, economy ASC
        """)

        # Execute all queries
        overall = db.execute(overall_query, params).fetchone()
        maidens = db.execute(maidens_query, params).fetchone()
        phase_stats = db.execute(phase_query, params).fetchone()
        over_distribution = db.execute(over_distribution_query, params).fetchall()
        batter_handedness = db.execute(batter_handedness_query, params).fetchall()
        innings_data = db.execute(innings_query, params).fetchall()
        innings_maidens_data = db.execute(innings_maidens_query, params).fetchall()
        over_combinations = db.execute(over_combinations_query, params).fetchall()

        # Create a dictionary of match_id -> maidens for easy lookup
        innings_maidens_dict = {}
        for im in innings_maidens_data:
            key = f"{im.match_id}_{im.innings}"
            innings_maidens_dict[key] = im.maidens

        # SIMPLIFIED: Format innings data with direct calculations
        formatted_innings = []
        for inning in innings_data:
            match_innings_key = f"{inning.match_id}_{inning.innings}"
            maidens_in_innings = innings_maidens_dict.get(match_innings_key, 0)
            
            # Use legal balls directly from query
            legal_deliveries = inning.legal_balls
            corrected_overs = balls_to_overs(legal_deliveries)
            
            formatted_innings.append({
                "match_id": inning.match_id,
                "date": inning.date.isoformat(),
                "venue": inning.venue,
                "competition": inning.competition,
                "bowling_team": inning.bowling_team,
                "batting_team": inning.batting_team,
                "winner": inning.winner,
                
                # Basic stats
                "overs": corrected_overs,
                "balls": legal_deliveries,
                "runs": inning.runs_conceded or 0,
                "wickets": inning.wickets or 0,
                "economy": round((inning.runs_conceded * 6) / legal_deliveries, 2) if legal_deliveries else 0,
                "maidens": maidens_in_innings,
                "dots": inning.dots or 0,
                "dot_percentage": round((inning.dots * 100) / legal_deliveries, 2) if legal_deliveries else 0,
                "boundaries": inning.boundaries or 0,
                "boundary_percentage": round((inning.boundaries * 100) / legal_deliveries, 2) if legal_deliveries else 0,

                # Phase details using pre-calculated stats + legal balls
                "phase_details": {
                    "powerplay": {
                        "overs": balls_to_overs(inning.pp_legal_balls),
                        "balls": inning.pp_legal_balls,
                        "runs": inning.pp_runs or 0,
                        "wickets": inning.pp_wickets or 0,
                        "economy": round((inning.pp_runs * 6) / inning.pp_legal_balls, 2) if inning.pp_legal_balls else 0,
                        "dots": inning.pp_dots or 0,
                        "dot_percentage": round((inning.pp_dots * 100) / inning.pp_legal_balls, 2) if inning.pp_legal_balls else 0,
                        "boundaries": inning.pp_boundaries or 0,
                        "boundary_percentage": round((inning.pp_boundaries * 100) / inning.pp_legal_balls, 2) if inning.pp_legal_balls else 0
                    },
                    "middle": {
                        "overs": balls_to_overs(inning.middle_legal_balls),
                        "balls": inning.middle_legal_balls,
                        "runs": inning.middle_runs or 0,
                        "wickets": inning.middle_wickets or 0,
                        "economy": round((inning.middle_runs * 6) / inning.middle_legal_balls, 2) if inning.middle_legal_balls else 0,
                        "dots": inning.middle_dots or 0,
                        "dot_percentage": round((inning.middle_dots * 100) / inning.middle_legal_balls, 2) if inning.middle_legal_balls else 0,
                        "boundaries": inning.middle_boundaries or 0,
                        "boundary_percentage": round((inning.middle_boundaries * 100) / inning.middle_legal_balls, 2) if inning.middle_legal_balls else 0
                    },
                    "death": {
                        "overs": balls_to_overs(inning.death_legal_balls),
                        "balls": inning.death_legal_balls,
                        "runs": inning.death_runs or 0,
                        "wickets": inning.death_wickets or 0,
                        "economy": round((inning.death_runs * 6) / inning.death_legal_balls, 2) if inning.death_legal_balls else 0,
                        "dots": inning.death_dots or 0,
                        "dot_percentage": round((inning.death_dots * 100) / inning.death_legal_balls, 2) if inning.death_legal_balls else 0,
                        "boundaries": inning.death_boundaries or 0,
                        "boundary_percentage": round((inning.death_boundaries * 100) / inning.death_legal_balls, 2) if inning.death_legal_balls else 0,
                    }
                }
            })

        def calculate_phase_metrics(data, is_bowling=True):
            """SIMPLIFIED: Direct calculation using legal balls"""
            if is_bowling:
                legal_deliveries = data.get("legal_deliveries", 0)
                corrected_overs = balls_to_overs(legal_deliveries)
                
                return {
                    "overs": corrected_overs,
                    "balls": legal_deliveries,
                    "runs": data["runs"],
                    "wickets": data["wickets"],
                    "economy": round((data["runs"] * 6) / legal_deliveries, 2) if legal_deliveries else 0,
                    "bowling_average": round(data["runs"] / data["wickets"], 2) if data["wickets"] else 999.99,
                    "bowling_strike_rate": round(legal_deliveries / data["wickets"], 2) if data["wickets"] else 999.99,
                    "dot_percentage": round((data["dots"] * 100) / legal_deliveries, 2) if legal_deliveries else 0,
                    "boundary_percentage": round((data["boundaries"] * 100) / legal_deliveries, 2) if legal_deliveries and "boundaries" in data else 0
                }

        # Format over distribution
        formatted_over_distribution = []
        for over in over_distribution:
            formatted_over_distribution.append({
                "over_number": over.over_number,
                "instances_bowled": over.instances_bowled,
                "matches_percentage": round((over.matches_bowled_in * 100) / overall.matches, 2) if overall.matches else 0,
                "runs": over.runs,
                "balls": over.legal_balls,  # Use legal balls only
                "wickets": over.wickets,
                "economy": round((over.runs * 6) / over.legal_balls, 2) if over.legal_balls else 0,
                "bowling_strike_rate": round(over.legal_balls / over.wickets, 2) if over.wickets else 999.99,
                "dot_percentage": round((over.dots * 100) / over.legal_balls, 2) if over.legal_balls else 0,
                "boundary_percentage": round((over.boundaries * 100) / over.legal_balls, 2) if over.legal_balls else 0
            })

        # Format batting handedness data
        formatted_handedness = {}
        for hand in batter_handedness:
            hand_data = {
                "overall": calculate_phase_metrics({
                    "legal_deliveries": hand.legal_balls or 0,
                    "runs": hand.runs or 0,
                    "wickets": hand.wickets or 0,
                    "dots": hand.dots or 0,
                    "boundaries": hand.boundaries or 0
                }, is_bowling=True),
                "powerplay": calculate_phase_metrics({
                    "legal_deliveries": hand.pp_legal_balls or 0,
                    "runs": hand.pp_runs or 0,
                    "wickets": hand.pp_wickets or 0,
                    "dots": 0,  # Would need separate tracking
                    "boundaries": 0  # Would need separate tracking
                }, is_bowling=True),
                "middle": calculate_phase_metrics({
                    "legal_deliveries": hand.middle_legal_balls or 0,
                    "runs": hand.middle_runs or 0,
                    "wickets": hand.middle_wickets or 0,
                    "dots": 0,  # Would need separate tracking
                    "boundaries": 0  # Would need separate tracking
                }, is_bowling=True),
                "death": calculate_phase_metrics({
                    "legal_deliveries": hand.death_legal_balls or 0,
                    "runs": hand.death_runs or 0,
                    "wickets": hand.death_wickets or 0,
                    "dots": 0,  # Would need separate tracking
                    "boundaries": 0  # Would need separate tracking
                }, is_bowling=True)
            }
            formatted_handedness[hand.batting_hand] = hand_data

        # Format the over combinations results
        formatted_over_combinations = []
        for combo in over_combinations:
            # Convert the PostgreSQL array to a Python list
            overs_list = list(combo.overs_bowled) if hasattr(combo, "overs_bowled") else []
            
            formatted_over_combinations.append({
                "overs": overs_list,
                "frequency": combo.frequency,
                "percentage": round((combo.frequency * 100) / overall.matches, 2) if overall.matches else 0,
                "runs": combo.runs,
                "wickets": combo.wickets,
                "economy": float(combo.economy) if combo.economy else 0,
                "wickets_per_innings": float(combo.wickets_per_innings) if combo.wickets_per_innings else 0
            })

        # SIMPLIFIED: Calculate corrected overall overs based on legal deliveries
        legal_deliveries = overall.legal_balls if hasattr(overall, "legal_balls") and overall.legal_balls else 0
        corrected_overall_overs = balls_to_overs(legal_deliveries)
        
        response = {
            "overall": {
                "matches": overall.matches,
                "overs": corrected_overall_overs,
                "balls": legal_deliveries,
                "runs": overall.runs_conceded or 0,
                "wickets": overall.wickets or 0,
                "maidens": maidens.maidens or 0,
                "bowling_average": round(overall.bowling_average, 2) if overall.bowling_average else 999.99,
                "bowling_strike_rate": round(legal_deliveries / overall.wickets, 2) if overall.wickets and legal_deliveries else 999.99,
                "economy_rate": round((overall.runs_conceded * 6) / legal_deliveries, 2) if overall.runs_conceded and legal_deliveries else 0,
                "dot_percentage": round((overall.dots * 100) / legal_deliveries, 2) if overall.dots and legal_deliveries else 0,
                "boundary_percentage": round((overall.boundaries * 100) / legal_deliveries, 2) if hasattr(overall, "boundaries") and overall.boundaries and legal_deliveries else 0,
                "three_wicket_hauls": overall.three_wicket_hauls or 0,
                "five_wicket_hauls": overall.five_wicket_hauls or 0
            },
            "phase_stats": {
                "powerplay": calculate_phase_metrics({
                    "legal_deliveries": phase_stats.pp_legal_balls or 0,
                    "runs": phase_stats.pp_runs or 0,
                    "wickets": phase_stats.pp_wickets or 0,
                    "dots": phase_stats.pp_dots or 0,
                    "boundaries": phase_stats.pp_boundaries or 0
                }, is_bowling=True),
                "middle": calculate_phase_metrics({
                    "legal_deliveries": phase_stats.middle_legal_balls or 0,
                    "runs": phase_stats.middle_runs or 0,
                    "wickets": phase_stats.middle_wickets or 0,
                    "dots": phase_stats.middle_dots or 0,
                    "boundaries": phase_stats.middle_boundaries or 0
                }, is_bowling=True),
                "death": calculate_phase_metrics({
                    "legal_deliveries": phase_stats.death_legal_balls or 0,
                    "runs": phase_stats.death_runs or 0,
                    "wickets": phase_stats.death_wickets or 0,
                    "dots": phase_stats.death_dots or 0,
                    "boundaries": phase_stats.death_boundaries or 0
                }, is_bowling=True)
            },
            "over_distribution": formatted_over_distribution,
            "batter_handedness": formatted_handedness,
            "innings": formatted_innings,
            "over_combinations": formatted_over_combinations
        }

        return response

    except Exception as e:
        logger.error(f"Error in get_player_bowling_stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing bowling stats: {str(e)}")

@app.get("/player/{player_name}/bowling_ball_stats")
def get_player_bowling_ball_stats(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    db: Session = Depends(get_session)
):
    try:
        params = {
            "player_name": player_name,
            "start_date": start_date,
            "end_date": end_date,
            "venue": venue,
            "has_leagues": bool(leagues),
            "leagues": leagues if leagues else [],
            "include_international": include_international,
            "top_teams": top_teams is not None,
            "top_team_list": INTERNATIONAL_TEAMS_RANKED[:top_teams] if top_teams else []
        }

        match_filter = """
            AND (
                (:has_leagues AND m.match_type = 'league' AND m.competition = ANY(:leagues))
                OR (:include_international AND m.match_type = 'international' 
                    AND (:top_teams IS NULL OR 
                        (m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list))
                    )
                )
            )
        """

        # SIMPLIFIED: Ball position stats with legal deliveries only
        ball_position_query = text(f"""
            SELECT 
                d.ball as ball_position,
                COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) as legal_balls,
                COUNT(*) as total_balls,
                SUM(d.runs_off_bat + d.extras) as runs,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                SUM(CASE WHEN d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                THEN 1 ELSE 0 END) as wickets,
                
                -- Phase distribution of legal balls only
                COUNT(CASE WHEN d.over < 6 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as pp_legal_balls,
                COUNT(CASE WHEN d.over >= 6 AND d.over < 15 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as middle_legal_balls,
                COUNT(CASE WHEN d.over >= 15 AND d.wides = 0 AND d.noballs = 0 THEN 1 END) as death_legal_balls
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE d.bowler = :player_name
            AND (:start_date IS NULL OR m.date >= :start_date)
            AND (:end_date IS NULL OR m.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
            GROUP BY d.ball
            ORDER BY d.ball
        """)

        # Execute query
        ball_stats = db.execute(ball_position_query, params).fetchall()

        return {
            "ball_position_stats": [
                {
                    "ball_position": row.ball_position,
                    "legal_balls": row.legal_balls,  # Use legal balls for calculations
                    "total_balls": row.total_balls,  # Still show total for reference
                    "runs": row.runs,
                    "dots": row.dots,
                    "boundaries": row.boundaries,
                    "wickets": row.wickets,
                    "economy_rate": round((row.runs * 6) / row.legal_balls, 2) if row.legal_balls else 0,
                    "bowling_strike_rate": round(row.legal_balls / row.wickets, 2) if row.wickets else 999.99,
                    "bowling_average": round(row.runs / row.wickets, 2) if row.wickets else 999.99,
                    "dot_percentage": round((row.dots * 100) / row.legal_balls, 2) if row.legal_balls else 0,
                    "phase_distribution": {
                        "powerplay": row.pp_legal_balls,
                        "middle": row.middle_legal_balls,
                        "death": row.death_legal_balls
                    }
                }
                for row in ball_stats
            ]
        }

    except Exception as e:
        logging.error(f"Error in get_player_bowling_ball_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))