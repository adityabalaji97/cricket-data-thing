"""
Wrapped 2025 Service Layer

This module contains all the data fetching logic for the Wrapped 2025 feature.
Each function corresponds to a specific card in the wrapped experience.
"""

from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import team rankings for top_teams filter
try:
    from config.teams import INTERNATIONAL_TEAMS_RANKED
except ImportError:
    INTERNATIONAL_TEAMS_RANKED = [
        'India', 'Australia', 'England', 'South Africa', 'New Zealand',
        'Pakistan', 'West Indies', 'Sri Lanka', 'Bangladesh', 'Afghanistan',
        'Ireland', 'Zimbabwe', 'Scotland', 'Netherlands', 'Namibia',
        'UAE', 'Nepal', 'USA', 'Oman', 'Papua New Guinea'
    ]

# Default settings
DEFAULT_TOP_TEAMS = 20


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_leagues_from_db(db: Session) -> List[str]:
    """Fetch all available leagues from the database."""
    query = text("""
        SELECT DISTINCT competition
        FROM matches 
        WHERE competition IS NOT NULL 
        AND match_type = 'league'
    """)
    result = db.execute(query).fetchall()
    return [row[0] for row in result if row[0]]


def build_competition_filter(
    leagues: List[str], 
    include_international: bool,
    top_teams: Optional[int] = None
) -> str:
    """Build the competition filter clause used across all queries."""
    conditions = []
    
    if leagues:
        conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
    
    if include_international:
        if top_teams:
            conditions.append(
                "(m.match_type = 'international' "
                "AND m.team1 = ANY(:top_team_list) "
                "AND m.team2 = ANY(:top_team_list))"
            )
        else:
            conditions.append("(m.match_type = 'international')")
    
    if conditions:
        return " AND (" + " OR ".join(conditions) + ")"
    else:
        return " AND FALSE"


def get_base_params(
    start_date: str, 
    end_date: str, 
    leagues: List[str],
    top_teams: Optional[int] = None
) -> Dict:
    """Returns base parameters used in most queries."""
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "leagues": leagues if leagues else []
    }
    
    if top_teams:
        params["top_team_list"] = INTERNATIONAL_TEAMS_RANKED[:top_teams]
    
    return params


# ============================================================================
# WRAPPED SERVICE CLASS
# ============================================================================

class WrappedService:
    """Service class for all Wrapped 2025 data operations."""
    
    def get_all_cards(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool = True,
        db: Session = None,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Fetch data for all wrapped cards.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            leagues: List of leagues to include. If empty, fetches all leagues from DB.
            include_international: Include international matches (default True)
            db: Database session
            top_teams: Number of top teams for international filtering (default 20)
        """
        # If no leagues specified, get all available leagues from DB
        if not leagues:
            leagues = get_all_leagues_from_db(db)
            logger.info(f"Using all available leagues: {len(leagues)} leagues found")
        
        cards = []
        
        # Card 1: Intro
        try:
            cards.append(self.get_intro_card_data(start_date, end_date, leagues, include_international, db, top_teams))
        except Exception as e:
            logger.error(f"Error fetching intro card: {e}")
            cards.append({"card_id": "intro", "error": str(e)})
        
        # Card 2: Powerplay Bullies
        try:
            cards.append(self.get_powerplay_bullies_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching powerplay bullies: {e}")
            cards.append({"card_id": "powerplay_bullies", "error": str(e)})
        
        # Card 3: Middle Merchants
        try:
            cards.append(self.get_middle_merchants_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching middle merchants: {e}")
            cards.append({"card_id": "middle_merchants", "error": str(e)})
        
        # Card 4: Death Hitters
        try:
            cards.append(self.get_death_hitters_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching death hitters: {e}")
            cards.append({"card_id": "death_hitters", "error": str(e)})
        
        # Card 5: Pace vs Spin
        try:
            cards.append(self.get_pace_vs_spin_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching pace vs spin: {e}")
            cards.append({"card_id": "pace_vs_spin", "error": str(e)})
        
        # Card 6: Powerplay Wicket Thieves
        try:
            cards.append(self.get_powerplay_wicket_thieves_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching powerplay thieves: {e}")
            cards.append({"card_id": "powerplay_thieves", "error": str(e)})
        
        # Card 7: 19th Over Gods
        try:
            cards.append(self.get_nineteenth_over_gods_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching 19th over gods: {e}")
            cards.append({"card_id": "nineteenth_over_gods", "error": str(e)})
        
        # Card 8: ELO Movers
        try:
            cards.append(self.get_elo_movers_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching elo movers: {e}")
            cards.append({"card_id": "elo_movers", "error": str(e)})
        
        # Card 9: Venue Vibes
        try:
            cards.append(self.get_venue_vibes_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching venue vibes: {e}")
            cards.append({"card_id": "venue_vibes", "error": str(e)})
        
        return {
            "year": 2025,
            "date_range": {"start": start_date, "end": end_date},
            "total_cards": len(cards),
            "cards": cards
        }
    
    def get_single_card(
        self,
        card_id: str,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool = True,
        db: Session = None,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Fetch data for a single card by ID."""
        # If no leagues specified, get all available leagues from DB
        if not leagues:
            leagues = get_all_leagues_from_db(db)
            logger.info(f"Using all available leagues: {len(leagues)} leagues found")
        
        card_methods = {
            "intro": self.get_intro_card_data,
            "powerplay_bullies": self.get_powerplay_bullies_data,
            "middle_merchants": self.get_middle_merchants_data,
            "death_hitters": self.get_death_hitters_data,
            "pace_vs_spin": self.get_pace_vs_spin_data,
            "powerplay_thieves": self.get_powerplay_wicket_thieves_data,
            "nineteenth_over_gods": self.get_nineteenth_over_gods_data,
            "elo_movers": self.get_elo_movers_data,
            "venue_vibes": self.get_venue_vibes_data,
        }
        
        if card_id not in card_methods:
            raise ValueError(f"Unknown card ID: {card_id}")
        
        return card_methods[card_id](start_date, end_date, leagues, include_international, db, top_teams=top_teams)

    # ========================================================================
    # CARD 1: INTRO - "2025 in One Breath"
    # ========================================================================
    
    def get_intro_card_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 1: Global run rate and wicket cost by phase."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = get_base_params(start_date, end_date, leagues, top_teams)
        
        query = text(f"""
            WITH phase_data AS (
                SELECT 
                    CASE 
                        WHEN d.over < 6 THEN 'powerplay'
                        WHEN d.over >= 6 AND d.over < 15 THEN 'middle'
                        ELSE 'death'
                    END as phase,
                    COUNT(*) as balls,
                    SUM(d.runs_off_bat + d.extras) as runs,
                    SUM(CASE WHEN d.wicket_type IS NOT NULL 
                        AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                        THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE m.date >= :start_date
                AND m.date <= :end_date
                {competition_filter}
                GROUP BY phase
            )
            SELECT 
                phase,
                balls,
                runs,
                wickets,
                dots,
                boundaries,
                ROUND(CAST(runs * 6.0 / NULLIF(balls, 0) AS numeric), 2) as run_rate,
                ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as runs_per_wicket,
                ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
            FROM phase_data
            ORDER BY 
                CASE phase 
                    WHEN 'powerplay' THEN 1 
                    WHEN 'middle' THEN 2 
                    WHEN 'death' THEN 3 
                END
        """)
        
        results = db.execute(query, params).fetchall()
        
        # Get total matches count
        matches_query = text(f"""
            SELECT COUNT(DISTINCT m.id) as total_matches
            FROM matches m
            WHERE m.date >= :start_date
            AND m.date <= :end_date
            {competition_filter}
        """)
        
        matches_result = db.execute(matches_query, params).fetchone()
        
        return {
            "card_id": "intro",
            "card_title": "2025 in One Breath",
            "card_subtitle": "The rhythm of T20 cricket",
            "total_matches": matches_result.total_matches if matches_result else 0,
            "phases": [
                {
                    "phase": row.phase,
                    "balls": row.balls,
                    "runs": row.runs,
                    "wickets": row.wickets,
                    "run_rate": float(row.run_rate) if row.run_rate else 0,
                    "runs_per_wicket": float(row.runs_per_wicket) if row.runs_per_wicket else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
                }
                for row in results
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=phase"
            }
        }

    # ========================================================================
    # CARD 2: POWERPLAY BULLIES
    # ========================================================================
    
    def get_powerplay_bullies_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 100,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 2: Top batters in powerplay by strike rate."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = {**get_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_balls}
        
        query = text(f"""
            WITH powerplay_stats AS (
                SELECT 
                    bs.striker as player,
                    SUM(bs.pp_balls) as balls,
                    SUM(bs.pp_runs) as runs,
                    SUM(bs.pp_wickets) as wickets,
                    SUM(bs.pp_dots) as dots,
                    SUM(bs.pp_boundaries) as boundaries,
                    COUNT(DISTINCT bs.match_id) as innings
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date >= :start_date
                AND m.date <= :end_date
                AND bs.pp_balls > 0
                {competition_filter}
                GROUP BY bs.striker
                HAVING SUM(bs.pp_balls) >= :min_balls
            )
            SELECT 
                player, balls, runs, wickets, dots, boundaries, innings,
                ROUND(CAST(runs * 100.0 / NULLIF(balls, 0) AS numeric), 2) as strike_rate,
                ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as average,
                ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
            FROM powerplay_stats
            ORDER BY strike_rate DESC
            LIMIT 20
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "powerplay_bullies",
            "card_title": "Powerplay Bullies of 2025",
            "card_subtitle": f"Min {min_balls} balls in powerplay",
            "visualization_type": "scatter",
            "x_axis": "dot_percentage",
            "y_axis": "strike_rate",
            "players": [
                {
                    "name": row.player,
                    "balls": row.balls,
                    "runs": row.runs,
                    "innings": row.innings,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                    "average": float(row.average) if row.average else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
                }
                for row in results
            ],
            "deep_links": {
                "comparison": f"/comparison?start_date={start_date}&end_date={end_date}",
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=0&over_max=5&group_by=batter&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 3: MIDDLE-OVERS MERCHANTS
    # ========================================================================
    
    def get_middle_merchants_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 150,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 3: Best middle-overs batters by average AND strike rate."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = {**get_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_balls}
        
        query = text(f"""
            WITH middle_stats AS (
                SELECT 
                    bs.striker as player,
                    SUM(bs.middle_balls) as balls,
                    SUM(bs.middle_runs) as runs,
                    SUM(bs.middle_wickets) as wickets,
                    SUM(bs.middle_dots) as dots,
                    SUM(bs.middle_boundaries) as boundaries,
                    COUNT(DISTINCT bs.match_id) as innings
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date >= :start_date
                AND m.date <= :end_date
                AND bs.middle_balls > 0
                {competition_filter}
                GROUP BY bs.striker
                HAVING SUM(bs.middle_balls) >= :min_balls
            )
            SELECT 
                player, balls, runs, wickets, dots, boundaries, innings,
                ROUND(CAST(runs * 100.0 / NULLIF(balls, 0) AS numeric), 2) as strike_rate,
                ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as average,
                ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
            FROM middle_stats
            WHERE wickets > 0
            ORDER BY (CAST(runs * 100.0 / NULLIF(balls, 0) AS numeric) * 
                     CAST(runs AS numeric) / NULLIF(wickets, 0)) / 100 DESC
            LIMIT 20
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "middle_merchants",
            "card_title": "Middle-Overs Merchants",
            "card_subtitle": f"Masters of overs 7-15 (min {min_balls} balls)",
            "visualization_type": "scatter",
            "x_axis": "average",
            "y_axis": "strike_rate",
            "players": [
                {
                    "name": row.player,
                    "balls": row.balls,
                    "runs": row.runs,
                    "innings": row.innings,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                    "average": float(row.average) if row.average else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
                }
                for row in results
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=6&over_max=14&group_by=batter&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 4: DEATH HITTERS
    # ========================================================================
    
    def get_death_hitters_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 75,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 4: Best death-overs hitters."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = {**get_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_balls}
        
        query = text(f"""
            WITH death_stats AS (
                SELECT 
                    bs.striker as player,
                    SUM(bs.death_balls) as balls,
                    SUM(bs.death_runs) as runs,
                    SUM(bs.death_wickets) as wickets,
                    SUM(bs.death_dots) as dots,
                    SUM(bs.death_boundaries) as boundaries,
                    COUNT(DISTINCT bs.match_id) as innings
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE m.date >= :start_date
                AND m.date <= :end_date
                AND bs.death_balls > 0
                {competition_filter}
                GROUP BY bs.striker
                HAVING SUM(bs.death_balls) >= :min_balls
            )
            SELECT 
                player, balls, runs, wickets, dots, boundaries, innings,
                ROUND(CAST(runs * 100.0 / NULLIF(balls, 0) AS numeric), 2) as strike_rate,
                ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as average,
                ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
            FROM death_stats
            ORDER BY strike_rate DESC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "death_hitters",
            "card_title": "Death is a Personality Trait",
            "card_subtitle": f"Finishers in overs 16-20 (min {min_balls} balls)",
            "visualization_type": "table_with_highlight",
            "players": [
                {
                    "name": row.player,
                    "balls": row.balls,
                    "runs": row.runs,
                    "innings": row.innings,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                    "average": float(row.average) if row.average else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
                }
                for row in results
            ],
            "deep_links": {
                "comparison": f"/comparison?start_date={start_date}&end_date={end_date}",
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=16&over_max=19&group_by=batter&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 5: PACE VS SPIN
    # ========================================================================
    
    def get_pace_vs_spin_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 100,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 5: Batters who were pace-only vs spin-only monsters."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = {**get_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_balls}
        
        query = text(f"""
            WITH pace_types AS (
                SELECT name FROM players 
                WHERE bowler_type IN ('RF', 'RFM', 'RM', 'LF', 'LFM', 'LM')
            ),
            spin_types AS (
                SELECT name FROM players 
                WHERE bowler_type IN ('RO', 'RL', 'LO', 'LC')
            ),
            batter_vs_pace AS (
                SELECT 
                    d.batter,
                    COUNT(*) as balls,
                    SUM(d.runs_off_bat + d.extras) as runs
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.bowler IN (SELECT name FROM pace_types)
                AND m.date >= :start_date AND m.date <= :end_date
                {competition_filter}
                GROUP BY d.batter
                HAVING COUNT(*) >= :min_balls
            ),
            batter_vs_spin AS (
                SELECT 
                    d.batter,
                    COUNT(*) as balls,
                    SUM(d.runs_off_bat + d.extras) as runs
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.bowler IN (SELECT name FROM spin_types)
                AND m.date >= :start_date AND m.date <= :end_date
                {competition_filter}
                GROUP BY d.batter
                HAVING COUNT(*) >= :min_balls
            )
            SELECT 
                COALESCE(p.batter, s.batter) as player,
                p.balls as pace_balls, p.runs as pace_runs,
                ROUND(CAST(p.runs * 100.0 / NULLIF(p.balls, 0) AS numeric), 2) as sr_vs_pace,
                s.balls as spin_balls, s.runs as spin_runs,
                ROUND(CAST(s.runs * 100.0 / NULLIF(s.balls, 0) AS numeric), 2) as sr_vs_spin,
                ROUND(CAST(p.runs * 100.0 / NULLIF(p.balls, 0) AS numeric) - 
                      CAST(s.runs * 100.0 / NULLIF(s.balls, 0) AS numeric), 2) as sr_delta
            FROM batter_vs_pace p
            FULL OUTER JOIN batter_vs_spin s ON p.batter = s.batter
            WHERE p.balls IS NOT NULL AND s.balls IS NOT NULL
            ORDER BY ABS(CAST(p.runs * 100.0 / NULLIF(p.balls, 0) AS numeric) - 
                        CAST(s.runs * 100.0 / NULLIF(s.balls, 0) AS numeric)) DESC
            LIMIT 20
        """)
        
        results = db.execute(query, params).fetchall()
        
        pace_crushers = [r for r in results if r.sr_delta and r.sr_delta > 0][:5]
        spin_crushers = [r for r in results if r.sr_delta and r.sr_delta < 0][:5]
        
        return {
            "card_id": "pace_vs_spin",
            "card_title": "Pace vs Spin: 2025's Split Brain",
            "card_subtitle": f"Who dominated which bowling type (min {min_balls} balls each)",
            "visualization_type": "diverging_bar",
            "pace_crushers": [
                {
                    "name": row.player,
                    "sr_vs_pace": float(row.sr_vs_pace) if row.sr_vs_pace else 0,
                    "sr_vs_spin": float(row.sr_vs_spin) if row.sr_vs_spin else 0,
                    "sr_delta": float(row.sr_delta) if row.sr_delta else 0,
                    "pace_balls": row.pace_balls,
                    "spin_balls": row.spin_balls
                }
                for row in pace_crushers
            ],
            "spin_crushers": [
                {
                    "name": row.player,
                    "sr_vs_pace": float(row.sr_vs_pace) if row.sr_vs_pace else 0,
                    "sr_vs_spin": float(row.sr_vs_spin) if row.sr_vs_spin else 0,
                    "sr_delta": float(row.sr_delta) if row.sr_delta else 0,
                    "pace_balls": row.pace_balls,
                    "spin_balls": row.spin_balls
                }
                for row in spin_crushers
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter,bowler_type&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 6: POWERPLAY WICKET THIEVES
    # ========================================================================
    
    def get_powerplay_wicket_thieves_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_wickets: int = 10,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 6: Best powerplay wicket-takers."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = {**get_base_params(start_date, end_date, leagues, top_teams), "min_wickets": min_wickets}
        
        query = text(f"""
            WITH pp_bowling AS (
                SELECT 
                    bw.bowler as player,
                    SUM(bw.pp_overs) * 6 as balls,
                    SUM(bw.pp_runs) as runs,
                    SUM(bw.pp_wickets) as wickets,
                    SUM(bw.pp_dots) as dots,
                    COUNT(DISTINCT bw.match_id) as innings
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE m.date >= :start_date AND m.date <= :end_date
                AND bw.pp_overs > 0
                {competition_filter}
                GROUP BY bw.bowler
                HAVING SUM(bw.pp_wickets) >= :min_wickets
            )
            SELECT 
                player, balls, runs, wickets, dots, innings,
                ROUND(CAST(balls AS numeric) / NULLIF(wickets, 0), 2) as strike_rate,
                ROUND(CAST(runs * 6.0 / NULLIF(balls, 0) AS numeric), 2) as economy,
                ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage
            FROM pp_bowling
            ORDER BY strike_rate ASC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "powerplay_thieves",
            "card_title": "Powerplay Wicket Thieves",
            "card_subtitle": f"Early breakthrough specialists (min {min_wickets} wickets)",
            "visualization_type": "table",
            "bowlers": [
                {
                    "name": row.player,
                    "balls": row.balls,
                    "runs": row.runs,
                    "wickets": row.wickets,
                    "innings": row.innings,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 999,
                    "economy": float(row.economy) if row.economy else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0
                }
                for row in results
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=0&over_max=5&group_by=bowler&min_balls=50"
            }
        }

    # ========================================================================
    # CARD 7: 19TH OVER GODS
    # ========================================================================
    
    def get_nineteenth_over_gods_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_overs: int = 10,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 7: Bowlers who dominated death overs."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = {**get_base_params(start_date, end_date, leagues, top_teams), "min_overs": min_overs}
        
        query = text(f"""
            WITH death_bowling AS (
                SELECT 
                    bw.bowler as player,
                    SUM(bw.death_overs) * 6 as balls,
                    SUM(bw.death_runs) as runs,
                    SUM(bw.death_wickets) as wickets,
                    SUM(bw.death_dots) as dots,
                    COUNT(DISTINCT bw.match_id) as innings
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE m.date >= :start_date AND m.date <= :end_date
                AND bw.death_overs > 0
                {competition_filter}
                GROUP BY bw.bowler
                HAVING SUM(bw.death_overs) >= :min_overs
            )
            SELECT 
                player, balls, runs, wickets, dots, innings,
                ROUND(CAST(runs * 6.0 / NULLIF(balls, 0) AS numeric), 2) as economy,
                ROUND(CAST(balls AS numeric) / NULLIF(wickets, 0), 2) as strike_rate,
                ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage
            FROM death_bowling
            ORDER BY economy ASC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "nineteenth_over_gods",
            "card_title": "The 19th Over Gods",
            "card_subtitle": f"Death overs excellence (min {min_overs} overs)",
            "visualization_type": "table",
            "bowlers": [
                {
                    "name": row.player,
                    "balls": row.balls,
                    "runs": row.runs,
                    "wickets": row.wickets,
                    "innings": row.innings,
                    "economy": float(row.economy) if row.economy else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 999,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0
                }
                for row in results
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=16&over_max=19&group_by=bowler"
            }
        }

    # ========================================================================
    # CARD 8: ELO MOVERS
    # ========================================================================
    
    def get_elo_movers_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 8: Biggest ELO risers/fallers."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = get_base_params(start_date, end_date, leagues, top_teams)
        
        query = text(f"""
            WITH team_matches AS (
                SELECT team, elo, date, 
                       ROW_NUMBER() OVER (PARTITION BY team ORDER BY date ASC) as rn_asc,
                       ROW_NUMBER() OVER (PARTITION BY team ORDER BY date DESC) as rn_desc
                FROM (
                    SELECT m.team1 as team, m.team1_elo as elo, m.date
                    FROM matches m
                    WHERE m.date >= :start_date AND m.date <= :end_date
                    AND m.team1_elo IS NOT NULL
                    {competition_filter}
                    UNION ALL
                    SELECT m.team2 as team, m.team2_elo as elo, m.date
                    FROM matches m
                    WHERE m.date >= :start_date AND m.date <= :end_date
                    AND m.team2_elo IS NOT NULL
                    {competition_filter}
                ) all_elos
            ),
            team_elo_summary AS (
                SELECT 
                    team,
                    MAX(CASE WHEN rn_asc = 1 THEN elo END) as start_elo,
                    MAX(CASE WHEN rn_desc = 1 THEN elo END) as end_elo,
                    MAX(elo) as peak_elo,
                    MIN(elo) as trough_elo
                FROM team_matches
                GROUP BY team
            )
            SELECT team, start_elo, end_elo, peak_elo, trough_elo,
                   (end_elo - start_elo) as elo_change
            FROM team_elo_summary
            WHERE start_elo IS NOT NULL AND end_elo IS NOT NULL
            ORDER BY ABS(end_elo - start_elo) DESC
            LIMIT 20
        """)
        
        try:
            results = db.execute(query, params).fetchall()
            
            risers = [r for r in results if r.elo_change and r.elo_change > 0][:5]
            fallers = [r for r in results if r.elo_change and r.elo_change < 0][:5]
            
            return {
                "card_id": "elo_movers",
                "card_title": "Teams That Became Different People",
                "card_subtitle": "Biggest ELO movements in 2025",
                "visualization_type": "diverging_bar",
                "risers": [
                    {
                        "team": row.team,
                        "start_elo": row.start_elo,
                        "end_elo": row.end_elo,
                        "elo_change": row.elo_change,
                        "peak_elo": row.peak_elo
                    }
                    for row in risers
                ],
                "fallers": [
                    {
                        "team": row.team,
                        "start_elo": row.start_elo,
                        "end_elo": row.end_elo,
                        "elo_change": row.elo_change,
                        "trough_elo": row.trough_elo
                    }
                    for row in fallers
                ],
                "deep_links": {
                    "team_profile": f"/team?start_date={start_date}&end_date={end_date}"
                }
            }
        except Exception as e:
            logger.error(f"Error fetching ELO data: {e}")
            return {
                "card_id": "elo_movers",
                "card_title": "Teams That Became Different People",
                "error": "ELO data not available for selected filters"
            }

    # ========================================================================
    # CARD 9: VENUE VIBES
    # ========================================================================
    
    def get_venue_vibes_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_matches: int = 5,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 9: Venue leaderboard - par score + chase bias."""
        
        competition_filter = build_competition_filter(leagues, include_international, top_teams)
        params = {**get_base_params(start_date, end_date, leagues, top_teams), "min_matches": min_matches}
        
        query = text(f"""
            WITH innings_totals AS (
                SELECT match_id, innings, SUM(runs_off_bat + extras) as total
                FROM deliveries
                GROUP BY match_id, innings
            ),
            venue_stats AS (
                SELECT 
                    m.venue,
                    COUNT(DISTINCT m.id) as matches,
                    SUM(CASE WHEN m.winner = m.team1 AND m.toss_decision = 'bat' THEN 1
                             WHEN m.winner = m.team2 AND m.toss_decision = 'field' THEN 1
                             ELSE 0 END) as bat_first_wins,
                    SUM(CASE WHEN m.winner = m.team1 AND m.toss_decision = 'field' THEN 1
                             WHEN m.winner = m.team2 AND m.toss_decision = 'bat' THEN 1
                             ELSE 0 END) as chase_wins,
                    AVG(CASE WHEN it.innings = 1 THEN it.total END) as avg_first_innings
                FROM matches m
                LEFT JOIN innings_totals it ON m.id = it.match_id
                WHERE m.date >= :start_date AND m.date <= :end_date
                AND m.winner IS NOT NULL
                {competition_filter}
                GROUP BY m.venue
                HAVING COUNT(DISTINCT m.id) >= :min_matches
            )
            SELECT 
                venue, matches, bat_first_wins, chase_wins,
                ROUND(CAST(avg_first_innings AS numeric), 0) as par_score,
                ROUND(CAST(chase_wins * 100.0 / NULLIF(bat_first_wins + chase_wins, 0) AS numeric), 1) as chase_win_pct
            FROM venue_stats
            ORDER BY matches DESC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "venue_vibes",
            "card_title": "Venues Had Vibes",
            "card_subtitle": f"Par scores and chase bias (min {min_matches} matches)",
            "visualization_type": "scatter",
            "x_axis": "par_score",
            "y_axis": "chase_win_pct",
            "venues": [
                {
                    "name": row.venue,
                    "matches": row.matches,
                    "par_score": int(row.par_score) if row.par_score else 0,
                    "chase_win_pct": float(row.chase_win_pct) if row.chase_win_pct else 50,
                    "bat_first_wins": row.bat_first_wins,
                    "chase_wins": row.chase_wins
                }
                for row in results
            ],
            "deep_links": {
                "venue_analysis": f"/venue?start_date={start_date}&end_date={end_date}"
            }
        }
