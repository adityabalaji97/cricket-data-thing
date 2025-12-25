"""
2025 In Hindsight Service Layer

This module contains all the data fetching logic for the 2025 In Hindsight feature.
Each function corresponds to a specific card in the hindsight experience.
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
    """Build the competition filter clause for matches table queries."""
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
    """Returns base parameters used in most queries (matches table)."""
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "leagues": leagues if leagues else []
    }
    
    if top_teams:
        params["top_team_list"] = INTERNATIONAL_TEAMS_RANKED[:top_teams]
    
    return params


def build_dd_competition_filter(
    leagues: List[str], 
    include_international: bool,
    top_teams: Optional[int] = None
) -> str:
    """Build the competition filter clause for delivery_details table.
    
    Note: delivery_details uses 'competition' column directly and
    'team_bat'/'team_bowl' for team filtering.
    """
    conditions = []
    
    if leagues:
        conditions.append("dd.competition = ANY(:leagues)")
    
    if include_international:
        if top_teams:
            conditions.append(
                "(dd.competition = 'T20I' "
                "AND dd.team_bat = ANY(:top_team_list) "
                "AND dd.team_bowl = ANY(:top_team_list))"
            )
        else:
            conditions.append("dd.competition = 'T20I'")
    
    if conditions:
        return " AND (" + " OR ".join(conditions) + ")"
    else:
        return " AND FALSE"


def get_dd_base_params(
    start_date: str, 
    end_date: str, 
    leagues: List[str],
    top_teams: Optional[int] = None
) -> Dict:
    """Returns base parameters for delivery_details queries."""
    params = {
        "start_year": int(start_date[:4]),
        "end_year": int(end_date[:4]),
        "leagues": leagues if leagues else []
    }
    
    if top_teams:
        params["top_team_list"] = INTERNATIONAL_TEAMS_RANKED[:top_teams]
    
    return params


# ============================================================================
# WRAPPED SERVICE CLASS
# ============================================================================

class WrappedService:
    """Service class for all 2025 In Hindsight data operations."""
    
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
        
        # Card 7.5: Middle Overs Squeeze (NEW - bowlers)
        try:
            cards.append(self.get_middle_overs_squeeze_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching middle overs squeeze: {e}")
            cards.append({"card_id": "middle_overs_squeeze", "error": str(e)})
        
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
        
        # Card 10: Controlled Aggression (NEW - uses delivery_details)
        try:
            cards.append(self.get_controlled_aggression_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching controlled aggression: {e}")
            cards.append({"card_id": "controlled_aggression", "error": str(e)})
        
        # Card 11: 360° Batters (NEW - uses delivery_details wagon_zone)
        try:
            cards.append(self.get_360_batters_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching 360 batters: {e}")
            cards.append({"card_id": "360_batters", "error": str(e)})
        
        # Card 12: Batter Hand Breakdown (NEW - uses delivery_details bat_hand/crease_combo)
        try:
            cards.append(self.get_batter_hand_breakdown_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching batter hand breakdown: {e}")
            cards.append({"card_id": "batter_hand_breakdown", "error": str(e)})
        
        # Card 13: Length Masters (NEW - uses delivery_details length)
        try:
            cards.append(self.get_length_masters_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching length masters: {e}")
            cards.append({"card_id": "length_masters", "error": str(e)})
        
        # Card 14: Rare Shot Specialists
        try:
            cards.append(self.get_rare_shot_specialists_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching rare shot specialists: {e}")
            cards.append({"card_id": "rare_shot_specialists", "error": str(e)})
        
        # Card 15: Bowler Type Dominance (NEW - uses delivery_details bowl_kind/bowl_style)
        try:
            cards.append(self.get_bowler_type_dominance_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching bowler type dominance: {e}")
            cards.append({"card_id": "bowler_type_dominance", "error": str(e)})
        
        # Card 16: Sweep Evolution (NEW - uses delivery_details shot)
        try:
            cards.append(self.get_sweep_evolution_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching sweep evolution: {e}")
            cards.append({"card_id": "sweep_evolution", "error": str(e)})
        
        # Card 17: Needle Movers (NEW - uses delivery_details pred_score)
        try:
            cards.append(self.get_needle_movers_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching needle movers: {e}")
            cards.append({"card_id": "needle_movers", "error": str(e)})
        
        # Card 18: Chase Masters (NEW - uses delivery_details win_prob)
        try:
            cards.append(self.get_chase_masters_data(start_date, end_date, leagues, include_international, db, top_teams=top_teams))
        except Exception as e:
            logger.error(f"Error fetching chase masters: {e}")
            cards.append({"card_id": "chase_masters", "error": str(e)})
        
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
            "middle_overs_squeeze": self.get_middle_overs_squeeze_data,
            "elo_movers": self.get_elo_movers_data,
            "venue_vibes": self.get_venue_vibes_data,
            "controlled_aggression": self.get_controlled_aggression_data,
            "360_batters": self.get_360_batters_data,
            "batter_hand_breakdown": self.get_batter_hand_breakdown_data,
            "length_masters": self.get_length_masters_data,
            "rare_shot_specialists": self.get_rare_shot_specialists_data,
            "bowler_type_dominance": self.get_bowler_type_dominance_data,
            "sweep_evolution": self.get_sweep_evolution_data,
            "needle_movers": self.get_needle_movers_data,
            "chase_masters": self.get_chase_masters_data,
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
        """Card 1: Global run rate and wicket cost by phase - using delivery_details."""
        
        dd_filter = build_dd_competition_filter(leagues, include_international, top_teams)
        params = get_dd_base_params(start_date, end_date, leagues, top_teams)
        
        query = text(f"""
            WITH phase_data AS (
                SELECT 
                    CASE 
                        WHEN dd.over < 6 THEN 'powerplay'
                        WHEN dd.over >= 6 AND dd.over < 15 THEN 'middle'
                        ELSE 'death'
                    END as phase,
                    COUNT(*) as balls,
                    SUM(dd.score) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != ''
                        AND dd.dismissal NOT IN ('run out', 'retired hurt', 'retired out')
                        THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                {dd_filter}
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
        
        # Get total matches count from delivery_details
        matches_query = text(f"""
            SELECT COUNT(DISTINCT dd.p_match) as total_matches
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            {dd_filter}
        """)
        
        matches_result = db.execute(matches_query, params).fetchone()
        
        # Get batting first vs chase win statistics using delivery_details
        toss_query = text(f"""
            WITH match_results AS (
                SELECT DISTINCT 
                    dd.p_match,
                    dd.winner,
                    FIRST_VALUE(dd.team_bat) OVER (
                        PARTITION BY dd.p_match 
                        ORDER BY dd.inns, dd.over, dd.ball
                    ) as batting_first_team
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.winner IS NOT NULL
                AND dd.winner != ''
                {dd_filter}
            )
            SELECT 
                SUM(CASE WHEN winner = batting_first_team THEN 1 ELSE 0 END) as bat_first_wins,
                SUM(CASE WHEN winner != batting_first_team THEN 1 ELSE 0 END) as chase_wins,
                COUNT(DISTINCT p_match) as total_decided
            FROM match_results
        """)
        
        toss_result = db.execute(toss_query, params).fetchone()
        
        # Calculate percentages
        bat_first_wins = toss_result.bat_first_wins if toss_result and toss_result.bat_first_wins else 0
        chase_wins = toss_result.chase_wins if toss_result and toss_result.chase_wins else 0
        total_decided = bat_first_wins + chase_wins
        bat_first_pct = round((bat_first_wins * 100.0 / total_decided), 1) if total_decided > 0 else 50.0
        
        return {
            "card_id": "intro",
            "card_title": "2025 in One Breath",
            "card_subtitle": "The rhythm of T20 cricket",
            "total_matches": matches_result.total_matches if matches_result else 0,
            "toss_stats": {
                "bat_first_wins": bat_first_wins,
                "chase_wins": chase_wins,
                "total_decided": total_decided,
                "bat_first_pct": bat_first_pct
            },
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
        """Card 2: Top batters in powerplay by strike rate - using delivery_details."""
        
        dd_filter = build_dd_competition_filter(leagues, include_international, top_teams)
        params = {**get_dd_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_balls}
        
        query = text(f"""
            WITH powerplay_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    COUNT(DISTINCT dd.p_match) as innings
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.over < 6  -- Powerplay overs 0-5
                AND dd.bat_hand IN ('LHB', 'RHB')
                {dd_filter}
                GROUP BY dd.bat, dd.team_bat
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM powerplay_stats
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(wickets) as wickets,
                    SUM(dots) as dots,
                    SUM(boundaries) as boundaries,
                    SUM(innings) as innings
                FROM powerplay_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player, ppt.team, pt.balls, pt.runs, pt.wickets, pt.dots, pt.boundaries, pt.innings,
                ROUND(CAST(pt.runs * 100.0 / NULLIF(pt.balls, 0) AS numeric), 2) as strike_rate,
                ROUND(CAST(pt.runs AS numeric) / NULLIF(pt.wickets, 0), 2) as average,
                ROUND(CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as boundary_percentage
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY strike_rate DESC
            LIMIT 20
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "powerplay_bullies",
            "card_title": "Powerplay Bullies",
            "card_subtitle": f"Who dominated the first 6 overs (min {min_balls} balls)",
            "visualization_type": "scatter",
            "x_axis": "dot_percentage",
            "y_axis": "strike_rate",
            "players": [
                {
                    "name": row.player,
                    "team": row.team,
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
        """Card 3: Best middle-overs batters - prioritizing low dot% and high boundary%."""
        
        dd_filter = build_dd_competition_filter(leagues, include_international, top_teams)
        params = {**get_dd_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_balls}
        
        query = text(f"""
            WITH middle_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    COUNT(DISTINCT dd.p_match) as innings
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.over >= 6 AND dd.over < 15  -- Middle overs 6-14
                AND dd.bat_hand IN ('LHB', 'RHB')
                {dd_filter}
                GROUP BY dd.bat, dd.team_bat
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM middle_stats
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(wickets) as wickets,
                    SUM(dots) as dots,
                    SUM(boundaries) as boundaries,
                    SUM(innings) as innings
                FROM middle_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player, ppt.team, pt.balls, pt.runs, pt.wickets, pt.dots, pt.boundaries, pt.innings,
                ROUND(CAST(pt.runs * 100.0 / NULLIF(pt.balls, 0) AS numeric), 2) as strike_rate,
                ROUND(CAST(pt.runs AS numeric) / NULLIF(pt.wickets, 0), 2) as average,
                ROUND(CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as boundary_percentage,
                -- Composite score: high boundary%, low dot%, high SR
                ROUND(
                    (CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric) * 2) +
                    (50 - CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric)) +
                    (CAST(pt.runs * 100.0 / NULLIF(pt.balls, 0) AS numeric) - 100) / 10
                , 2) as middle_overs_score
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            WHERE pt.wickets > 0
            ORDER BY middle_overs_score DESC
            LIMIT 20
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "middle_merchants",
            "card_title": "Middle Merchants",
            "card_subtitle": f"Masters of overs 7-15 (min {min_balls} balls)",
            "visualization_type": "scatter",
            "x_axis": "dot_percentage",
            "y_axis": "boundary_percentage",
            "ranking_note": "Ranked by composite score: high boundary%, low dot%, high SR",
            "players": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "innings": row.innings,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                    "average": float(row.average) if row.average else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0,
                    "middle_overs_score": float(row.middle_overs_score) if row.middle_overs_score else 0
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
        """Card 4: Best death-overs hitters - prioritizing six-hitting."""
        
        dd_filter = build_dd_competition_filter(leagues, include_international, top_teams)
        params = {**get_dd_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_balls}
        
        query = text(f"""
            WITH death_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    SUM(CASE WHEN dd.batruns = 4 THEN 1 ELSE 0 END) as fours,
                    SUM(CASE WHEN dd.batruns = 6 THEN 1 ELSE 0 END) as sixes,
                    SUM(CASE WHEN dd.batruns = 6 THEN 6 ELSE 0 END) as runs_from_sixes,
                    COUNT(DISTINCT dd.p_match) as innings
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.over >= 15  -- Death overs 15-19
                AND dd.bat_hand IN ('LHB', 'RHB')
                {dd_filter}
                GROUP BY dd.bat, dd.team_bat
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM death_stats
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(wickets) as wickets,
                    SUM(dots) as dots,
                    SUM(boundaries) as boundaries,
                    SUM(fours) as fours,
                    SUM(sixes) as sixes,
                    SUM(runs_from_sixes) as runs_from_sixes,
                    SUM(innings) as innings
                FROM death_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player, ppt.team, pt.balls, pt.runs, pt.wickets, pt.dots, 
                pt.boundaries, pt.fours, pt.sixes, pt.innings,
                ROUND(CAST(pt.runs * 100.0 / NULLIF(pt.balls, 0) AS numeric), 2) as strike_rate,
                ROUND(CAST(pt.runs AS numeric) / NULLIF(pt.wickets, 0), 2) as average,
                ROUND(CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as boundary_percentage,
                ROUND(CAST(pt.runs_from_sixes * 100.0 / NULLIF(pt.runs, 0) AS numeric), 1) as six_runs_percentage,
                ROUND(CAST(pt.sixes AS numeric) / NULLIF(pt.innings, 0), 2) as sixes_per_innings
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            -- Order by composite of SR (60%) and six_runs_percentage (40%)
            ORDER BY 
                (CAST(pt.runs * 100.0 / NULLIF(pt.balls, 0) AS numeric) * 0.6 +
                 CAST(pt.runs_from_sixes * 100.0 / NULLIF(pt.runs, 0) AS numeric) * 0.4) DESC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "death_hitters",
            "card_title": "Death Hitters",
            "card_subtitle": f"Six-hitting finishers (min {min_balls} balls)",
            "visualization_type": "table_with_highlight",
            "ranking_note": "Ranked by strike rate (60%) + % runs from sixes (40%)",
            "players": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "innings": row.innings,
                    "sixes": row.sixes,
                    "fours": row.fours,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                    "average": float(row.average) if row.average else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0,
                    "six_runs_percentage": float(row.six_runs_percentage) if row.six_runs_percentage else 0,
                    "sixes_per_innings": float(row.sixes_per_innings) if row.sixes_per_innings else 0
                }
                for row in results
            ],
            "deep_links": {
                "comparison": f"/comparison?start_date={start_date}&end_date={end_date}",
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=15&over_max=19&group_by=batter&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 5: PACE VS SPIN (BATTERS)
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
        """Card 5: Batters who were pace-only vs spin-only monsters.
        
        Uses delivery_details.bowl_kind for reliable pace/spin classification.
        """
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_balls": min_balls
        }
        
        # Note: We don't filter by competition for delivery_details table
        # because competition values may not match matches table, and year filter is sufficient
        
        query = text(f"""
            WITH batter_vs_pace AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.bowl_kind = 'pace bowler'
                AND dd.bat_hand IN ('LHB', 'RHB')
                GROUP BY dd.bat, dd.team_bat
            ),
            batter_vs_spin AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.bowl_kind = 'spin bowler'
                AND dd.bat_hand IN ('LHB', 'RHB')
                GROUP BY dd.bat, dd.team_bat
            ),
            pace_totals AS (
                SELECT player, SUM(balls) as balls, SUM(runs) as runs
                FROM batter_vs_pace
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            ),
            spin_totals AS (
                SELECT player, SUM(balls) as balls, SUM(runs) as runs
                FROM batter_vs_spin
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM (
                    SELECT player, team, balls FROM batter_vs_pace
                    UNION ALL
                    SELECT player, team, balls FROM batter_vs_spin
                ) combined
                ORDER BY player, balls DESC
            )
            SELECT 
                COALESCE(p.player, s.player) as player,
                ppt.team,
                p.balls as pace_balls, p.runs as pace_runs,
                ROUND(CAST(p.runs * 100.0 / NULLIF(p.balls, 0) AS numeric), 2) as sr_vs_pace,
                s.balls as spin_balls, s.runs as spin_runs,
                ROUND(CAST(s.runs * 100.0 / NULLIF(s.balls, 0) AS numeric), 2) as sr_vs_spin,
                ROUND(CAST(p.runs * 100.0 / NULLIF(p.balls, 0) AS numeric) - 
                      CAST(s.runs * 100.0 / NULLIF(s.balls, 0) AS numeric), 2) as sr_delta
            FROM pace_totals p
            FULL OUTER JOIN spin_totals s ON p.player = s.player
            LEFT JOIN player_primary_team ppt ON COALESCE(p.player, s.player) = ppt.player
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
            "card_title": "Pace vs Spin",
            "card_subtitle": f"2025's split personality batters (min {min_balls} balls each)",
            "visualization_type": "diverging_bar",
            "pace_crushers": [
                {
                    "name": row.player,
                    "team": row.team,
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
                    "team": row.team,
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
        """Card 6: Best powerplay wicket-takers - using delivery_details."""
        
        dd_filter = build_dd_competition_filter(leagues, include_international, top_teams)
        params = {**get_dd_base_params(start_date, end_date, leagues, top_teams), "min_wickets": min_wickets}
        
        query = text(f"""
            WITH pp_bowling AS (
                SELECT 
                    dd.bowl as player,
                    dd.team_bowl as team,
                    COUNT(*) as balls,
                    SUM(dd.score) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' 
                        AND dd.dismissal NOT IN ('run out', 'retired hurt', 'retired out')
                        THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    COUNT(DISTINCT dd.p_match) as innings
                FROM delivery_details dd
                WHERE dd.year >= :start_year AND dd.year <= :end_year
                AND dd.over < 6  -- Powerplay overs 0-5
                {dd_filter}
                GROUP BY dd.bowl, dd.team_bowl
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM pp_bowling
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(wickets) as wickets,
                    SUM(dots) as dots,
                    SUM(boundaries) as boundaries,
                    SUM(innings) as innings
                FROM pp_bowling
                GROUP BY player
                HAVING SUM(wickets) >= :min_wickets
            )
            SELECT 
                pt.player, ppt.team, pt.balls, pt.runs, pt.wickets, pt.dots, pt.boundaries, pt.innings,
                ROUND(CAST(pt.balls AS numeric) / NULLIF(pt.wickets, 0), 2) as strike_rate,
                ROUND(CAST(pt.runs * 6.0 / NULLIF(pt.balls, 0) AS numeric), 2) as economy,
                ROUND(CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as boundary_percentage
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY strike_rate ASC, boundary_percentage ASC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "powerplay_thieves",
            "card_title": "PP Wicket Thieves",
            "card_subtitle": f"Early breakthrough specialists (min {min_wickets} wickets)",
            "visualization_type": "table",
            "highlight_metrics": ["dot_percentage", "boundary_percentage"],
            "bowlers": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "wickets": row.wickets,
                    "innings": row.innings,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 999,
                    "economy": float(row.economy) if row.economy else 0,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
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
        """Card 7: Bowlers who dominated death overs - using delivery_details."""
        
        dd_filter = build_dd_competition_filter(leagues, include_international, top_teams)
        params = {**get_dd_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_overs * 6}
        
        query = text(f"""
            WITH death_bowling AS (
                SELECT 
                    dd.bowl as player,
                    dd.team_bowl as team,
                    COUNT(*) as balls,
                    SUM(dd.score) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' 
                        AND dd.dismissal NOT IN ('run out', 'retired hurt', 'retired out')
                        THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    COUNT(DISTINCT dd.p_match) as innings
                FROM delivery_details dd
                WHERE dd.year >= :start_year AND dd.year <= :end_year
                AND dd.over >= 15  -- Death overs 15-19
                {dd_filter}
                GROUP BY dd.bowl, dd.team_bowl
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM death_bowling
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(wickets) as wickets,
                    SUM(dots) as dots,
                    SUM(boundaries) as boundaries,
                    SUM(innings) as innings
                FROM death_bowling
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player, ppt.team, pt.balls, pt.runs, pt.wickets, pt.dots, pt.boundaries, pt.innings,
                ROUND(CAST(pt.runs * 6.0 / NULLIF(pt.balls, 0) AS numeric), 2) as economy,
                ROUND(CAST(pt.balls AS numeric) / NULLIF(pt.wickets, 0), 2) as strike_rate,
                ROUND(CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as boundary_percentage,
                -- Composite score: low economy + high dot% + low boundary%
                ROUND(
                    (15 - CAST(pt.runs * 6.0 / NULLIF(pt.balls, 0) AS numeric)) * 5 +
                    (CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric)) * 0.5 +
                    (30 - CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric)) * 0.3 +
                    (CAST(pt.wickets AS numeric) / NULLIF(pt.innings, 0)) * 10
                , 2) as death_bowling_score
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY death_bowling_score DESC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "nineteenth_over_gods",
            "card_title": "Death Over Gods",
            "card_subtitle": f"Overs 16-20 bowling excellence (min {min_overs} overs)",
            "visualization_type": "table",
            "ranking_note": "Composite: economy + wickets + dot% + low boundary%",
            "bowlers": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "overs": round(row.balls / 6, 1),
                    "runs": row.runs,
                    "wickets": row.wickets,
                    "innings": row.innings,
                    "economy": float(row.economy) if row.economy else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 999,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0,
                    "death_bowling_score": float(row.death_bowling_score) if row.death_bowling_score else 0
                }
                for row in results
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=15&over_max=19&group_by=bowler"
            }
        }

    # ========================================================================
    # CARD 7.5: MIDDLE OVERS SQUEEZE (NEW)
    # ========================================================================
    
    def get_middle_overs_squeeze_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_overs: int = 15,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 7.5: Middle Overs Squeeze - Bowlers who strangled scoring in overs 7-15.
        
        Focuses on economy and dot ball percentage as primary metrics,
        with wickets as a bonus factor.
        """
        
        dd_filter = build_dd_competition_filter(leagues, include_international, top_teams)
        params = {**get_dd_base_params(start_date, end_date, leagues, top_teams), "min_balls": min_overs * 6}
        
        query = text(f"""
            WITH middle_bowling AS (
                SELECT 
                    dd.bowl as player,
                    dd.team_bowl as team,
                    COUNT(*) as balls,
                    SUM(dd.score) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' 
                        AND dd.dismissal NOT IN ('run out', 'retired hurt', 'retired out')
                        THEN 1 ELSE 0 END) as wickets,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    SUM(CASE WHEN dd.batruns = 1 OR dd.batruns = 2 THEN 1 ELSE 0 END) as singles_doubles,
                    COUNT(DISTINCT dd.p_match) as innings
                FROM delivery_details dd
                WHERE dd.year >= :start_year AND dd.year <= :end_year
                AND dd.over >= 6 AND dd.over < 15  -- Middle overs 6-14
                {dd_filter}
                GROUP BY dd.bowl, dd.team_bowl
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM middle_bowling
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(wickets) as wickets,
                    SUM(dots) as dots,
                    SUM(boundaries) as boundaries,
                    SUM(singles_doubles) as singles_doubles,
                    SUM(innings) as innings
                FROM middle_bowling
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player, ppt.team, pt.balls, pt.runs, pt.wickets, 
                pt.dots, pt.boundaries, pt.singles_doubles, pt.innings,
                ROUND(CAST(pt.runs * 6.0 / NULLIF(pt.balls, 0) AS numeric), 2) as economy,
                ROUND(CAST(pt.balls AS numeric) / NULLIF(pt.wickets, 0), 2) as strike_rate,
                ROUND(CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as dot_percentage,
                ROUND(CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as boundary_percentage,
                -- Squeeze score: low economy + high dot% + low boundary% + wicket bonus
                ROUND(
                    (10 - CAST(pt.runs * 6.0 / NULLIF(pt.balls, 0) AS numeric)) * 8 +
                    (CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric)) * 0.6 +
                    (20 - CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric)) * 0.5 +
                    (CAST(pt.wickets AS numeric) / NULLIF(pt.innings, 0)) * 8
                , 2) as squeeze_score
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY squeeze_score DESC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        return {
            "card_id": "middle_overs_squeeze",
            "card_title": "Middle Overs Squeeze",
            "card_subtitle": f"Who choked the scoring in overs 7-15 (min {min_overs} overs)",
            "visualization_type": "scatter",
            "x_axis": "dot_percentage",
            "y_axis": "economy",
            "invert_y": True,  # Lower economy is better, show at top
            "ranking_note": "Composite: economy + dot% + low boundary% + wickets",
            "bowlers": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "overs": round(row.balls / 6, 1),
                    "runs": row.runs,
                    "wickets": row.wickets,
                    "innings": row.innings,
                    "economy": float(row.economy) if row.economy else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 999,
                    "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                    "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0,
                    "squeeze_score": float(row.squeeze_score) if row.squeeze_score else 0
                }
                for row in results
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=6&over_max=14&group_by=bowler"
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
                "card_title": "ELO Movers",
                "card_subtitle": "Teams that transformed in 2025",
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
                "card_title": "ELO Movers",
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
        """Card 9: Venue leaderboard - par score + chase bias - using delivery_details."""
        
        dd_filter = build_dd_competition_filter(leagues, include_international, top_teams)
        params = {**get_dd_base_params(start_date, end_date, leagues, top_teams), "min_matches": min_matches}
        
        query = text(f"""
            WITH innings_totals AS (
                SELECT 
                    dd.p_match,
                    dd.ground as venue,
                    dd.inns,
                    dd.winner,
                    FIRST_VALUE(dd.team_bat) OVER (
                        PARTITION BY dd.p_match 
                        ORDER BY dd.inns, dd.over, dd.ball
                    ) as batting_first_team,
                    SUM(dd.score) OVER (PARTITION BY dd.p_match, dd.inns) as innings_total
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                {dd_filter}
            ),
            match_summary AS (
                SELECT DISTINCT
                    p_match,
                    venue,
                    winner,
                    batting_first_team,
                    MAX(CASE WHEN inns = 1 THEN innings_total END) OVER (PARTITION BY p_match) as first_innings_total
                FROM innings_totals
            ),
            venue_stats AS (
                SELECT 
                    venue,
                    COUNT(DISTINCT p_match) as matches,
                    SUM(CASE WHEN winner = batting_first_team AND winner IS NOT NULL AND winner != '' THEN 1 ELSE 0 END) as bat_first_wins,
                    SUM(CASE WHEN winner != batting_first_team AND winner IS NOT NULL AND winner != '' THEN 1 ELSE 0 END) as chase_wins,
                    AVG(first_innings_total) as avg_first_innings
                FROM match_summary
                WHERE winner IS NOT NULL AND winner != ''
                GROUP BY venue
                HAVING COUNT(DISTINCT p_match) >= :min_matches
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
            "card_title": "Venue Vibes",
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

    # ========================================================================
    # CARD 10: CONTROLLED AGGRESSION
    # ========================================================================
    
    def get_controlled_aggression_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 150,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 10: Controlled Aggression - composite metric combining control%, SR, boundary%, dot%."""
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_balls": min_balls
        }
        
        # Note: We don't filter by competition for delivery_details table
        # because competition values may not match matches table, and year filter is sufficient
        
        query = text(f"""
            WITH player_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs,
                    SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) as controlled_shots,
                    SUM(CASE WHEN dd.control IS NOT NULL THEN 1 ELSE 0 END) as control_data_balls
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.bat_hand IN ('LHB', 'RHB')
                GROUP BY dd.bat, dd.team_bat
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM player_stats
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(dots) as dots,
                    SUM(boundaries) as boundaries,
                    SUM(controlled_shots) as controlled_shots,
                    SUM(control_data_balls) as control_data_balls
                FROM player_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
                AND SUM(control_data_balls) >= 50  -- Need enough control data
            )
            SELECT 
                pt.player,
                ppt.team,
                pt.balls,
                pt.runs,
                ROUND(pt.runs * 100.0 / NULLIF(pt.balls, 0), 2) as strike_rate,
                ROUND(pt.dots * 100.0 / NULLIF(pt.balls, 0), 2) as dot_pct,
                ROUND(pt.boundaries * 100.0 / NULLIF(pt.balls, 0), 2) as boundary_pct,
                ROUND(pt.controlled_shots * 100.0 / NULLIF(pt.control_data_balls, 0), 2) as control_pct
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY pt.runs DESC
            LIMIT 50
        """)
        
        results = db.execute(query, params).fetchall()
        
        # Calculate Controlled Aggression score for each player
        def calc_ca_score(sr, dot_pct, boundary_pct, control_pct):
            """
            Controlled Aggression Score formula:
            - Control% contributes 25% (higher = better)
            - Strike Rate contributes 35% (higher = better, normalized from 100)
            - Boundary% contributes 25% (higher = better)
            - Anti-Dot (50 - dot%) contributes 15% (lower dot% = better)
            """
            if control_pct is None:
                control_pct = 70  # Default assumption
            
            control_score = (control_pct / 100) * 25
            sr_score = min(35, max(0, ((sr - 100) / 70) * 35))  # 100-170 SR maps to 0-35
            boundary_score = min(25, (boundary_pct / 25) * 25)  # 0-25% boundary maps to 0-25
            anti_dot_score = min(15, max(0, ((50 - dot_pct) / 30) * 15))  # 20-50% dot maps to 15-0
            
            return round(control_score + sr_score + boundary_score + anti_dot_score, 1)
        
        players_with_ca = []
        for row in results:
            ca_score = calc_ca_score(
                float(row.strike_rate) if row.strike_rate else 100,
                float(row.dot_pct) if row.dot_pct else 35,
                float(row.boundary_pct) if row.boundary_pct else 12,
                float(row.control_pct) if row.control_pct else 70
            )
            players_with_ca.append({
                "name": row.player,
                "team": row.team,
                "balls": row.balls,
                "runs": row.runs,
                "ca_score": ca_score,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                "dot_pct": float(row.dot_pct) if row.dot_pct else 0,
                "boundary_pct": float(row.boundary_pct) if row.boundary_pct else 0,
                "control_pct": float(row.control_pct) if row.control_pct else 0
            })
        
        # Sort by CA score
        players_with_ca.sort(key=lambda x: x['ca_score'], reverse=True)
        
        return {
            "card_id": "controlled_aggression",
            "card_title": "Controlled Chaos",
            "card_subtitle": f"The most efficient aggressors (min {min_balls} balls)",
            "visualization_type": "radar_comparison",
            "metric_weights": {
                "control_pct": 0.25,
                "strike_rate": 0.35,
                "boundary_pct": 0.25,
                "anti_dot": 0.15
            },
            "players": players_with_ca[:15],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 11: 360° BATTERS
    # ========================================================================
    
    def get_360_batters_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 200,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 11: 360° Batters - who scores evenly across all wagon wheel zones."""
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_balls": min_balls
        }
        
        # Note: We don't filter by competition for delivery_details table
        # because competition values may not match matches table, and year filter is sufficient
        
        # Query zones 1-8 (zone 0 is dots/no shot data)
        query = text(f"""
            WITH zone_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    dd.wagon_zone,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.wagon_zone IS NOT NULL
                AND dd.wagon_zone BETWEEN 1 AND 8
                AND dd.bat_hand IN ('LHB', 'RHB')
                GROUP BY dd.bat, dd.team_bat, dd.wagon_zone
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM zone_stats
                ORDER BY player, SUM(balls) OVER (PARTITION BY player, team) DESC
            ),
            player_zone_agg AS (
                SELECT 
                    player,
                    wagon_zone,
                    SUM(balls) as balls,
                    SUM(runs) as runs
                FROM zone_stats
                GROUP BY player, wagon_zone
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as total_balls,
                    SUM(runs) as total_runs,
                    COUNT(DISTINCT wagon_zone) as zones_used
                FROM player_zone_agg
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            ),
            player_zone_pcts AS (
                SELECT 
                    pza.player,
                    pza.wagon_zone,
                    pza.runs,
                    pza.balls,
                    pt.total_runs,
                    pt.total_balls,
                    pt.zones_used,
                    CASE WHEN pt.total_runs > 0 
                        THEN ROUND((pza.runs * 100.0 / pt.total_runs)::numeric, 2)
                        ELSE 0 END as run_pct
                FROM player_zone_agg pza
                JOIN player_totals pt ON pza.player = pt.player
            )
            SELECT 
                pzp.player,
                ppt.team,
                pzp.wagon_zone,
                pzp.runs,
                pzp.balls,
                pzp.run_pct,
                pzp.total_runs,
                pzp.total_balls,
                pzp.zones_used
            FROM player_zone_pcts pzp
            JOIN player_primary_team ppt ON pzp.player = ppt.player
            ORDER BY pzp.player, pzp.wagon_zone
        """)
        
        results = db.execute(query, params).fetchall()
        
        # Group by player and calculate 360 score
        from collections import defaultdict
        player_data = defaultdict(lambda: {
            "zones": {},
            "total_runs": 0,
            "total_balls": 0,
            "team": None,
            "zones_used": 0
        })
        
        for row in results:
            player = row.player
            player_data[player]["zones"][row.wagon_zone] = {
                "zone": row.wagon_zone,
                "runs": row.runs,
                "balls": row.balls,
                "run_pct": float(row.run_pct) if row.run_pct else 0
            }
            player_data[player]["total_runs"] = row.total_runs
            player_data[player]["total_balls"] = row.total_balls
            player_data[player]["team"] = row.team
            player_data[player]["zones_used"] = row.zones_used
        
        def calc_360_score(zones_data, total_runs):
            """
            360 Score = 100 - (StdDev of zone run percentages * scaling_factor)
            Perfect distribution = 12.5% per zone (100/8 zones)
            Lower std dev = higher score (more evenly spread)
            """
            if total_runs == 0 or len(zones_data) < 4:
                return 0
            
            # Get run percentages for all 8 zones (0 if not used)
            zone_pcts = []
            for zone in range(1, 9):  # Zones 1-8
                if zone in zones_data:
                    zone_pcts.append(zones_data[zone]["run_pct"])
                else:
                    zone_pcts.append(0)
            
            # Calculate standard deviation
            mean_pct = sum(zone_pcts) / 8  # Should be ~12.5 for perfect distribution
            variance = sum((pct - mean_pct) ** 2 for pct in zone_pcts) / 8
            std_dev = variance ** 0.5
            
            # Convert to 0-100 score (lower std_dev = higher score)
            # Max std_dev would be ~35 (all runs in one zone)
            score = max(0, min(100, 100 - (std_dev * 2.5)))
            return round(score, 1)
        
        # Calculate 360 score for each player
        players_with_360 = []
        for player, data in player_data.items():
            score_360 = calc_360_score(data["zones"], data["total_runs"])
            
            # Build zone breakdown list
            zone_breakdown = []
            for zone in range(1, 9):
                if zone in data["zones"]:
                    zone_breakdown.append(data["zones"][zone])
                else:
                    zone_breakdown.append({"zone": zone, "runs": 0, "balls": 0, "run_pct": 0})
            
            players_with_360.append({
                "name": player,
                "team": data["team"],
                "score_360": score_360,
                "total_runs": data["total_runs"],
                "total_balls": data["total_balls"],
                "zones_used": data["zones_used"],
                "strike_rate": round((data["total_runs"] * 100 / data["total_balls"]), 2) if data["total_balls"] > 0 else 0,
                "zone_breakdown": zone_breakdown
            })
        
        # Sort by 360 score
        players_with_360.sort(key=lambda x: x['score_360'], reverse=True)
        
        return {
            "card_id": "360_batters",
            "card_title": "360° Batters",
            "card_subtitle": f"Who scores all around the ground (min {min_balls} balls)",
            "visualization_type": "wagon_wheel",
            "zone_labels": {
                1: "Fine Leg",
                2: "Square Leg", 
                3: "Midwicket",
                4: "Long On",
                5: "Long Off",
                6: "Cover",
                7: "Point",
                8: "Third Man"
            },
            "players": players_with_360[:15],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter,wagon_zone&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 12: BATTER HAND BREAKDOWN
    # ========================================================================
    
    def get_batter_hand_breakdown_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 100,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 12: Batter Hand Breakdown - LHB vs RHB performance + crease combo analysis."""
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_balls": min_balls
        }
        
        # Note: We don't filter by competition for delivery_details table
        # because competition values may not match matches table, and year filter is sufficient
        
        # Query 1: Overall stats by bat_hand
        hand_query = text(f"""
            SELECT 
                dd.bat_hand,
                COUNT(*) as balls,
                SUM(dd.batruns) as runs,
                SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.bat_hand IN ('LHB', 'RHB')
            GROUP BY dd.bat_hand
        """)
        
        hand_results = db.execute(hand_query, params).fetchall()
        
        hand_stats = {}
        for row in hand_results:
            hand_stats[row.bat_hand] = {
                "bat_hand": row.bat_hand,
                "balls": row.balls,
                "runs": row.runs,
                "strike_rate": round((row.runs * 100 / row.balls), 2) if row.balls > 0 else 0,
                "dot_pct": round((row.dots * 100 / row.balls), 2) if row.balls > 0 else 0,
                "boundary_pct": round((row.boundaries * 100 / row.balls), 2) if row.balls > 0 else 0,
                "average": round((row.runs / row.wickets), 2) if row.wickets > 0 else 0
            }
        
        # Query 2: Stats by crease_combo (normalized)
        crease_query = text(f"""
            SELECT 
                CASE 
                    WHEN dd.crease_combo IN ('LHB_RHB', 'RHB_LHB') THEN 'Mixed'
                    WHEN dd.crease_combo = 'RHB_RHB' THEN 'RHB_RHB'
                    WHEN dd.crease_combo = 'LHB_LHB' THEN 'LHB_LHB'
                    ELSE 'Other'
                END as combo_normalized,
                COUNT(*) as balls,
                SUM(dd.batruns) as runs,
                SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.crease_combo IN ('LHB_RHB', 'RHB_LHB', 'RHB_RHB', 'LHB_LHB')
            GROUP BY combo_normalized
            ORDER BY balls DESC
        """)
        
        crease_results = db.execute(crease_query, params).fetchall()
        
        crease_stats = []
        for row in crease_results:
            crease_stats.append({
                "combo": row.combo_normalized,
                "balls": row.balls,
                "runs": row.runs,
                "strike_rate": round((row.runs * 100 / row.balls), 2) if row.balls > 0 else 0,
                "dot_pct": round((row.dots * 100 / row.balls), 2) if row.balls > 0 else 0,
                "boundary_pct": round((row.boundaries * 100 / row.balls), 2) if row.balls > 0 else 0
            })
        
        # Query 3: Top 5 performers per hand
        top_lhb_query = text(f"""
            WITH player_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.bat_hand = 'LHB'
                GROUP BY dd.bat, dd.team_bat
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM player_stats
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT player, SUM(balls) as balls, SUM(runs) as runs
                FROM player_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT pt.player, ppt.team, pt.balls, pt.runs,
                   ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY strike_rate DESC
            LIMIT 5
        """)
        
        top_rhb_query = text(f"""
            WITH player_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.bat_hand = 'RHB'
                GROUP BY dd.bat, dd.team_bat
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM player_stats
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT player, SUM(balls) as balls, SUM(runs) as runs
                FROM player_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT pt.player, ppt.team, pt.balls, pt.runs,
                   ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY strike_rate DESC
            LIMIT 5
        """)
        
        top_lhb = db.execute(top_lhb_query, params).fetchall()
        top_rhb = db.execute(top_rhb_query, params).fetchall()
        
        return {
            "card_id": "batter_hand_breakdown",
            "card_title": "Left vs Right",
            "card_subtitle": f"Batting hand breakdown (min {min_balls} balls)",
            "visualization_type": "comparison_with_crease",
            "hand_stats": hand_stats,
            "crease_combo_stats": crease_stats,
            "top_lhb": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0
                }
                for row in top_lhb
            ],
            "top_rhb": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0
                }
                for row in top_rhb
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=bat_hand&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 13: LENGTH MASTERS
    # ========================================================================
    
    def get_length_masters_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 150,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 13: Length Masters - batters who dominate across all bowling lengths."""
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_balls": min_balls
        }
        
        # Note: We don't filter by competition for delivery_details table
        # because competition values may not match matches table, and year filter is sufficient
        
        query = text(f"""
            WITH length_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    dd.length,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.length IS NOT NULL
                AND dd.bat_hand IN ('LHB', 'RHB')
                GROUP BY dd.bat, dd.team_bat, dd.length
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM length_stats
                ORDER BY player, SUM(balls) OVER (PARTITION BY player, team) DESC
            ),
            player_length_agg AS (
                SELECT player, length, SUM(balls) as balls, SUM(runs) as runs
                FROM length_stats
                GROUP BY player, length
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as total_balls,
                    SUM(runs) as total_runs,
                    COUNT(DISTINCT length) as lengths_faced
                FROM player_length_agg
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pla.player,
                ppt.team,
                pla.length,
                pla.balls,
                pla.runs,
                ROUND((pla.runs * 100.0 / NULLIF(pla.balls, 0))::numeric, 2) as strike_rate,
                pt.total_balls,
                pt.total_runs,
                pt.lengths_faced
            FROM player_length_agg pla
            JOIN player_totals pt ON pla.player = pt.player
            JOIN player_primary_team ppt ON pla.player = ppt.player
            ORDER BY pla.player, pla.length
        """)
        
        results = db.execute(query, params).fetchall()
        
        from collections import defaultdict
        player_data = defaultdict(lambda: {
            "lengths": {},
            "total_runs": 0,
            "total_balls": 0,
            "team": None,
            "lengths_faced": 0
        })
        
        for row in results:
            player = row.player
            player_data[player]["lengths"][row.length] = {
                "length": row.length,
                "balls": row.balls,
                "runs": row.runs,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0
            }
            player_data[player]["total_runs"] = row.total_runs
            player_data[player]["total_balls"] = row.total_balls
            player_data[player]["team"] = row.team
            player_data[player]["lengths_faced"] = row.lengths_faced
        
        # Length order and difficulty weights
        length_order = ['YORKER', 'GOOD_LENGTH', 'SHORT_OF_A_GOOD_LENGTH', 'FULL', 'SHORT', 'FULL_TOSS']
        # Weights: harder lengths worth more (yorker hardest, full toss easiest)
        length_weights = {
            'YORKER': 1.5,
            'GOOD_LENGTH': 1.2,
            'SHORT_OF_A_GOOD_LENGTH': 1.0,
            'FULL': 0.9,
            'SHORT': 0.8,
            'FULL_TOSS': 0.7
        }
        
        def calc_length_master_score(lengths_data, total_balls):
            if total_balls < 50:
                return 0
            
            weighted_sr_sum = 0
            weight_sum = 0
            
            for length, weight in length_weights.items():
                if length in lengths_data and lengths_data[length]['balls'] >= 10:
                    sr = lengths_data[length]['strike_rate']
                    weighted_sr_sum += sr * weight
                    weight_sum += weight
            
            if weight_sum == 0:
                return 0
            
            return round(weighted_sr_sum / weight_sum, 1)
        
        players_with_score = []
        for player, data in player_data.items():
            score = calc_length_master_score(data["lengths"], data["total_balls"])
            
            length_breakdown = []
            for length in length_order:
                if length in data["lengths"]:
                    length_breakdown.append(data["lengths"][length])
                else:
                    length_breakdown.append({"length": length, "balls": 0, "runs": 0, "strike_rate": 0})
            
            players_with_score.append({
                "name": player,
                "team": data["team"],
                "length_master_score": score,
                "total_runs": data["total_runs"],
                "total_balls": data["total_balls"],
                "overall_sr": round((data["total_runs"] * 100 / data["total_balls"]), 2) if data["total_balls"] > 0 else 0,
                "lengths_faced": data["lengths_faced"],
                "length_breakdown": length_breakdown
            })
        
        players_with_score.sort(key=lambda x: x['length_master_score'], reverse=True)
        
        return {
            "card_id": "length_masters",
            "card_title": "Length Masters",
            "card_subtitle": f"Versatile scorers across all lengths (min {min_balls} balls)",
            "visualization_type": "length_heatmap",
            "length_order": length_order,
            "length_labels": {
                "YORKER": "Yorker",
                "GOOD_LENGTH": "Good",
                "SHORT_OF_A_GOOD_LENGTH": "Back of Length",
                "FULL": "Full",
                "SHORT": "Short",
                "FULL_TOSS": "Full Toss"
            },
            "players": players_with_score[:15],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter,length&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 14: RARE SHOT SPECIALISTS
    # ========================================================================
    
    def get_rare_shot_specialists_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_plays: int = 10,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 14: Rare Shot Specialists - who excels at unconventional shots."""
        
        # Rare shots (bottom ~30% by frequency from data exploration)
        rare_shots = ['REVERSE_SCOOP', 'REVERSE_PULL', 'LATE_CUT', 'PADDLE_SWEEP', 'RAMP', 'HOOK', 'UPPER_CUT']
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_plays": min_plays,
            "rare_shots": rare_shots
        }
        
        # Note: We don't filter by competition for delivery_details table
        # because competition values may not match matches table, and year filter is sufficient
        
        query = text(f"""
            WITH rare_shot_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    dd.shot,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.shot = ANY(:rare_shots)
                AND dd.bat_hand IN ('LHB', 'RHB')
                GROUP BY dd.bat, dd.team_bat, dd.shot
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM rare_shot_stats
                ORDER BY player, SUM(balls) OVER (PARTITION BY player, team) DESC
            ),
            player_shot_agg AS (
                SELECT player, shot, SUM(balls) as balls, SUM(runs) as runs, SUM(boundaries) as boundaries
                FROM rare_shot_stats
                GROUP BY player, shot
                HAVING SUM(balls) >= :min_plays
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as total_rare_balls,
                    SUM(runs) as total_rare_runs,
                    SUM(boundaries) as total_boundaries,
                    COUNT(DISTINCT shot) as rare_shots_used
                FROM player_shot_agg
                GROUP BY player
            )
            SELECT 
                psa.player,
                ppt.team,
                psa.shot,
                psa.balls,
                psa.runs,
                psa.boundaries,
                ROUND((psa.runs * 100.0 / NULLIF(psa.balls, 0))::numeric, 2) as strike_rate,
                pt.total_rare_balls,
                pt.total_rare_runs,
                pt.rare_shots_used
            FROM player_shot_agg psa
            JOIN player_totals pt ON psa.player = pt.player
            JOIN player_primary_team ppt ON psa.player = ppt.player
            ORDER BY psa.player, psa.balls DESC
        """)
        
        results = db.execute(query, params).fetchall()
        
        from collections import defaultdict
        player_data = defaultdict(lambda: {
            "shots": {},
            "total_rare_balls": 0,
            "total_rare_runs": 0,
            "team": None,
            "rare_shots_used": 0
        })
        
        for row in results:
            player = row.player
            player_data[player]["shots"][row.shot] = {
                "shot": row.shot,
                "balls": row.balls,
                "runs": row.runs,
                "boundaries": row.boundaries,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0
            }
            player_data[player]["total_rare_balls"] = row.total_rare_balls
            player_data[player]["total_rare_runs"] = row.total_rare_runs
            player_data[player]["team"] = row.team
            player_data[player]["rare_shots_used"] = row.rare_shots_used
        
        players_list = []
        for player, data in player_data.items():
            overall_sr = round((data["total_rare_runs"] * 100 / data["total_rare_balls"]), 2) if data["total_rare_balls"] > 0 else 0
            
            # Best shot = highest SR with min 5 balls
            best_shot = None
            best_sr = 0
            for shot_name, shot_data in data["shots"].items():
                if shot_data["balls"] >= 5 and shot_data["strike_rate"] > best_sr:
                    best_sr = shot_data["strike_rate"]
                    best_shot = shot_name
            
            shot_breakdown = list(data["shots"].values())
            shot_breakdown.sort(key=lambda x: x["balls"], reverse=True)
            
            players_list.append({
                "name": player,
                "team": data["team"],
                "total_rare_balls": data["total_rare_balls"],
                "total_rare_runs": data["total_rare_runs"],
                "overall_rare_sr": overall_sr,
                "rare_shots_used": data["rare_shots_used"],
                "best_shot": best_shot,
                "best_shot_sr": best_sr,
                "shot_breakdown": shot_breakdown
            })
        
        # Sort by total rare runs (volume + quality)
        players_list.sort(key=lambda x: x['total_rare_runs'], reverse=True)
        
        return {
            "card_id": "rare_shot_specialists",
            "card_title": "Rare Shot Artists",
            "card_subtitle": f"Masters of unconventional shots (min {min_plays} plays)",
            "visualization_type": "shot_showcase",
            "rare_shots": rare_shots,
            "shot_labels": {
                "REVERSE_SCOOP": "Rev Scoop",
                "REVERSE_PULL": "Rev Pull",
                "LATE_CUT": "Late Cut",
                "PADDLE_SWEEP": "Paddle",
                "RAMP": "Ramp",
                "HOOK": "Hook",
                "UPPER_CUT": "Upper Cut"
            },
            "players": players_list[:15],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter,shot"
            }
        }

    # ========================================================================
    # CARD 15: BOWLER TYPE DOMINANCE
    # ========================================================================
    
    def get_bowler_type_dominance_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 200,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 15: Bowler Type Dominance - Pace vs Spin breakdown with style analysis."""
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_balls": min_balls
        }
        
        # Note: We don't filter by competition for delivery_details table
        # because competition values may not match matches table, and year filter is sufficient
        
        # Query 1: Overall pace vs spin stats
        kind_query = text(f"""
            SELECT 
                dd.bowl_kind,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.bowl_kind IN ('pace bowler', 'spin bowler')
            GROUP BY dd.bowl_kind
        """)
        
        kind_results = db.execute(kind_query, params).fetchall()
        
        kind_stats = {}
        for row in kind_results:
            kind = 'pace' if row.bowl_kind == 'pace bowler' else 'spin'
            kind_stats[kind] = {
                "kind": kind,
                "balls": row.balls,
                "runs": row.runs,
                "wickets": row.wickets,
                "economy": round((row.runs * 6 / row.balls), 2) if row.balls > 0 else 0,
                "strike_rate": round((row.balls / row.wickets), 2) if row.wickets > 0 else 999,
                "dot_pct": round((row.dots * 100 / row.balls), 2) if row.balls > 0 else 0,
                "boundary_pct": round((row.boundaries * 100 / row.balls), 2) if row.balls > 0 else 0
            }
        
        # Query 2: Stats by bowling style
        style_query = text(f"""
            SELECT 
                dd.bowl_style,
                dd.bowl_kind,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.bowl_style IS NOT NULL
            AND dd.bowl_kind IN ('pace bowler', 'spin bowler')
            GROUP BY dd.bowl_style, dd.bowl_kind
            HAVING COUNT(*) >= 500
            ORDER BY COUNT(*) DESC
        """)
        
        style_results = db.execute(style_query, params).fetchall()
        
        # Style labels
        style_labels = {
            'RF': 'Right Fast',
            'RFM': 'Right Fast-Medium',
            'RMF': 'Right Medium-Fast',
            'RM': 'Right Medium',
            'LF': 'Left Fast',
            'LFM': 'Left Fast-Medium',
            'LMF': 'Left Medium-Fast',
            'LM': 'Left Medium',
            'OB': 'Off Break',
            'LB': 'Leg Break',
            'LBG': 'Leg Break Googly',
            'SLA': 'Slow Left Arm',
            'LWS': 'Left Wrist Spin'
        }
        
        style_stats = []
        for row in style_results:
            kind = 'pace' if row.bowl_kind == 'pace bowler' else 'spin'
            style_stats.append({
                "style": row.bowl_style,
                "label": style_labels.get(row.bowl_style, row.bowl_style),
                "kind": kind,
                "balls": row.balls,
                "runs": row.runs,
                "wickets": row.wickets,
                "economy": round((row.runs * 6 / row.balls), 2) if row.balls > 0 else 0,
                "strike_rate": round((row.balls / row.wickets), 2) if row.wickets > 0 else 999,
                "dot_pct": round((row.dots * 100 / row.balls), 2) if row.balls > 0 else 0
            })
        
        # Query 3: Top bowlers by kind
        top_pace_query = text(f"""
            WITH bowler_stats AS (
                SELECT 
                    dd.bowl as player,
                    dd.team_bowl as team,
                    COUNT(*) as balls,
                    SUM(dd.score) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.bowl_kind = 'pace bowler'
                GROUP BY dd.bowl, dd.team_bowl
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM bowler_stats
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT player, SUM(balls) as balls, SUM(runs) as runs, SUM(wickets) as wickets
                FROM bowler_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT pt.player, ppt.team, pt.balls, pt.runs, pt.wickets,
                   ROUND((pt.runs * 6.0 / pt.balls)::numeric, 2) as economy,
                   ROUND((pt.balls::numeric / NULLIF(pt.wickets, 0)), 2) as strike_rate
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY pt.wickets DESC, economy ASC
            LIMIT 5
        """)
        
        top_spin_query = text(f"""
            WITH bowler_stats AS (
                SELECT 
                    dd.bowl as player,
                    dd.team_bowl as team,
                    COUNT(*) as balls,
                    SUM(dd.score) as runs,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.bowl_kind = 'spin bowler'
                GROUP BY dd.bowl, dd.team_bowl
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM bowler_stats
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT player, SUM(balls) as balls, SUM(runs) as runs, SUM(wickets) as wickets
                FROM bowler_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT pt.player, ppt.team, pt.balls, pt.runs, pt.wickets,
                   ROUND((pt.runs * 6.0 / pt.balls)::numeric, 2) as economy,
                   ROUND((pt.balls::numeric / NULLIF(pt.wickets, 0)), 2) as strike_rate
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY pt.wickets DESC, economy ASC
            LIMIT 5
        """)
        
        top_pace = db.execute(top_pace_query, params).fetchall()
        top_spin = db.execute(top_spin_query, params).fetchall()
        
        return {
            "card_id": "bowler_type_dominance",
            "card_title": "Pace vs Spin",
            "card_subtitle": f"The bowling arms race (min {min_balls} balls)",
            "visualization_type": "treemap_with_leaders",
            "kind_stats": kind_stats,
            "style_stats": style_stats[:10],  # Top 10 styles by volume
            "style_labels": style_labels,
            "top_pace": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "wickets": row.wickets,
                    "economy": float(row.economy) if row.economy else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 999
                }
                for row in top_pace
            ],
            "top_spin": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "wickets": row.wickets,
                    "economy": float(row.economy) if row.economy else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 999
                }
                for row in top_spin
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=bowler,bowl_kind&min_balls={min_balls}"
            }
        }

    # ========================================================================
    # CARD 16: SWEEP EVOLUTION
    # ========================================================================
    
    def get_sweep_evolution_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_plays: int = 20,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 16: Sweep Evolution - How sweep shots have been used in 2025."""
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_plays": min_plays
        }
        
        # Sweep shot variants
        sweep_shots = ['SWEEP', 'PADDLE_SWEEP', 'REVERSE_SWEEP', 'SLOG_SWEEP']
        params["sweep_shots"] = sweep_shots
        
        # Query 1: Overall sweep stats vs spin and pace
        sweep_vs_kind_query = text(f"""
            SELECT 
                dd.shot,
                dd.bowl_kind,
                COUNT(*) as balls,
                SUM(dd.batruns) as runs,
                SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.shot = ANY(:sweep_shots)
            AND dd.bowl_kind IN ('pace bowler', 'spin bowler')
            GROUP BY dd.shot, dd.bowl_kind
            ORDER BY dd.shot, dd.bowl_kind
        """)
        
        sweep_kind_results = db.execute(sweep_vs_kind_query, params).fetchall()
        
        # Build sweep stats by type and bowler kind
        sweep_stats = {}
        for row in sweep_kind_results:
            shot = row.shot
            kind = 'pace' if row.bowl_kind == 'pace bowler' else 'spin'
            
            if shot not in sweep_stats:
                sweep_stats[shot] = {'pace': None, 'spin': None, 'total_balls': 0}
            
            sweep_stats[shot][kind] = {
                'balls': row.balls,
                'runs': row.runs,
                'strike_rate': round((row.runs * 100 / row.balls), 2) if row.balls > 0 else 0,
                'boundary_pct': round((row.boundaries * 100 / row.balls), 2) if row.balls > 0 else 0,
                'wickets': row.wickets,
                'dismissal_pct': round((row.wickets * 100 / row.balls), 2) if row.balls > 0 else 0
            }
            sweep_stats[shot]['total_balls'] += row.balls
        
        # Query 2: Top sweep merchants
        top_sweepers_query = text(f"""
            WITH sweep_stats AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    dd.shot,
                    COUNT(*) as balls,
                    SUM(dd.batruns) as runs,
                    SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                    SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.shot = ANY(:sweep_shots)
                AND dd.bat_hand IN ('LHB', 'RHB')
                GROUP BY dd.bat, dd.team_bat, dd.shot
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM sweep_stats
                ORDER BY player, SUM(balls) OVER (PARTITION BY player, team) DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as total_balls,
                    SUM(runs) as total_runs,
                    SUM(boundaries) as total_boundaries,
                    SUM(wickets) as total_wickets,
                    COUNT(DISTINCT shot) as sweep_types_used
                FROM sweep_stats
                GROUP BY player
                HAVING SUM(balls) >= :min_plays
            )
            SELECT 
                pt.player,
                ppt.team,
                pt.total_balls,
                pt.total_runs,
                pt.total_boundaries,
                pt.total_wickets,
                pt.sweep_types_used,
                ROUND((pt.total_runs * 100.0 / pt.total_balls)::numeric, 2) as strike_rate,
                ROUND((pt.total_boundaries * 100.0 / pt.total_balls)::numeric, 2) as boundary_pct
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY pt.total_runs DESC
            LIMIT 10
        """)
        
        top_sweepers = db.execute(top_sweepers_query, params).fetchall()
        
        # Convert sweep_stats to list sorted by usage
        sweep_list = []
        for shot, stats in sweep_stats.items():
            sweep_list.append({
                'shot': shot,
                'total_balls': stats['total_balls'],
                'vs_pace': stats['pace'],
                'vs_spin': stats['spin']
            })
        sweep_list.sort(key=lambda x: x['total_balls'], reverse=True)
        
        return {
            "card_id": "sweep_evolution",
            "card_title": "Sweep Evolution",
            "card_subtitle": f"How sweeps conquered 2025 (min {min_plays} plays)",
            "visualization_type": "sweep_breakdown",
            "sweep_types": sweep_shots,
            "shot_labels": {
                "SWEEP": "Sweep",
                "PADDLE_SWEEP": "Paddle",
                "REVERSE_SWEEP": "Rev Sweep",
                "SLOG_SWEEP": "Slog Sweep"
            },
            "sweep_stats": sweep_list,
            "top_sweepers": [
                {
                    "name": row.player,
                    "team": row.team,
                    "total_balls": row.total_balls,
                    "total_runs": row.total_runs,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                    "boundary_pct": float(row.boundary_pct) if row.boundary_pct else 0,
                    "sweep_types_used": row.sweep_types_used
                }
                for row in top_sweepers
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter,shot"
            }
        }

    # ========================================================================
    # CARD 17: NEEDLE MOVERS (pred_score per-ball delta impact)
    # ========================================================================
    
    def get_needle_movers_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 100,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 17: Needle Movers - Who moved pred_score the most (per-ball delta).
        
        For each ball faced by a batter:
          delta = next_pred_score - current_pred_score
        
        This measures how much the predicted final score changed after each delivery.
        Positive delta = batter increased the predicted score (good for batting team).
        Sum of deltas across all balls = total impact on predicted score.
        """
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_balls": min_balls
        }
        
        # Per-ball delta approach: calculate pred_score change for each delivery
        query = text(f"""
            WITH ball_deltas AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    dd.p_match,
                    dd.inns,
                    dd.ball_id,
                    dd.batruns,
                    dd.pred_score,
                    LEAD(dd.pred_score) OVER (
                        PARTITION BY dd.p_match, dd.inns 
                        ORDER BY dd.ball_id
                    ) as next_pred_score
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.pred_score IS NOT NULL
                AND dd.pred_score != -1
                AND dd.bat_hand IN ('LHB', 'RHB')
            ),
            player_ball_impact AS (
                SELECT 
                    player,
                    team,
                    COUNT(*) as balls,
                    SUM(batruns) as runs,
                    SUM(CASE 
                        WHEN next_pred_score IS NOT NULL AND next_pred_score != -1 
                        THEN next_pred_score - pred_score 
                        ELSE 0 
                    END) as total_pred_delta
                FROM ball_deltas
                WHERE next_pred_score IS NOT NULL AND next_pred_score != -1
                GROUP BY player, team
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM player_ball_impact
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(total_pred_delta) as total_pred_delta
                FROM player_ball_impact
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player,
                ppt.team,
                pt.balls,
                pt.runs,
                ROUND(pt.total_pred_delta::numeric, 1) as pred_score_impact,
                ROUND((pt.total_pred_delta / pt.balls)::numeric, 2) as impact_per_ball,
                ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY pt.total_pred_delta DESC
            LIMIT 20
        """)
        
        results = db.execute(query, params).fetchall()
        
        # Split into positive and negative impact
        positive_impact = [r for r in results if r.pred_score_impact and r.pred_score_impact > 0][:7]
        
        # Get bottom performers
        bottom_query = text(f"""
            WITH ball_deltas AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    dd.p_match,
                    dd.inns,
                    dd.ball_id,
                    dd.batruns,
                    dd.pred_score,
                    LEAD(dd.pred_score) OVER (
                        PARTITION BY dd.p_match, dd.inns 
                        ORDER BY dd.ball_id
                    ) as next_pred_score
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.pred_score IS NOT NULL
                AND dd.pred_score != -1
                AND dd.bat_hand IN ('LHB', 'RHB')
            ),
            player_ball_impact AS (
                SELECT 
                    player,
                    team,
                    COUNT(*) as balls,
                    SUM(batruns) as runs,
                    SUM(CASE 
                        WHEN next_pred_score IS NOT NULL AND next_pred_score != -1 
                        THEN next_pred_score - pred_score 
                        ELSE 0 
                    END) as total_pred_delta
                FROM ball_deltas
                WHERE next_pred_score IS NOT NULL AND next_pred_score != -1
                GROUP BY player, team
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM player_ball_impact
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(total_pred_delta) as total_pred_delta
                FROM player_ball_impact
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player,
                ppt.team,
                pt.balls,
                pt.runs,
                ROUND(pt.total_pred_delta::numeric, 1) as pred_score_impact,
                ROUND((pt.total_pred_delta / pt.balls)::numeric, 2) as impact_per_ball,
                ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY pt.total_pred_delta ASC
            LIMIT 5
        """)
        
        bottom_results = db.execute(bottom_query, params).fetchall()
        negative_impact = [r for r in bottom_results if r.pred_score_impact and r.pred_score_impact < 0]
        
        # Get coverage stats
        coverage_query = text(f"""
            SELECT 
                COUNT(*) as total_balls,
                SUM(CASE WHEN pred_score IS NOT NULL AND pred_score != -1 THEN 1 ELSE 0 END) as balls_with_data
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
        """)
        
        coverage_result = db.execute(coverage_query, params).fetchone()
        coverage_pct = round((coverage_result.balls_with_data * 100 / coverage_result.total_balls), 1) if coverage_result.total_balls > 0 else 0
        
        return {
            "card_id": "needle_movers",
            "card_title": "Needle Movers",
            "card_subtitle": f"Who moved the predicted score most (min {min_balls} balls)",
            "visualization_type": "diverging_impact",
            "coverage_pct": coverage_pct,
            "data_note": f"Based on {coverage_pct}% of deliveries with pred_score data",
            "positive_impact": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "pred_score_impact": float(row.pred_score_impact) if row.pred_score_impact else 0,
                    "impact_per_ball": float(row.impact_per_ball) if row.impact_per_ball else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0
                }
                for row in positive_impact
            ],
            "negative_impact": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "pred_score_impact": float(row.pred_score_impact) if row.pred_score_impact else 0,
                    "impact_per_ball": float(row.impact_per_ball) if row.impact_per_ball else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0
                }
                for row in negative_impact
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter"
            }
        }

    # ========================================================================
    # CARD 18: CHASE MASTERS (win_prob per-ball delta impact)
    # ========================================================================
    
    def get_chase_masters_data(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        min_balls: int = 50,
        top_teams: int = DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """Card 18: Chase Masters - Who moved win probability the most in chases.
        
        For each ball faced by a batter in 2nd innings:
          delta = next_win_prob - current_win_prob
        
        This measures how much the batting team's win probability changed after each delivery.
        Positive delta = batter improved team's chances of winning.
        Sum of deltas = total win probability contribution.
        
        Note: win_prob is stored as percentage (0-100), so deltas are in percentage points.
        """
        
        params = {
            "start_year": int(start_date[:4]),
            "end_year": int(end_date[:4]),
            "min_balls": min_balls
        }
        
        # Per-ball delta approach for win probability in chases
        query = text(f"""
            WITH ball_deltas AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    dd.p_match,
                    dd.ball_id,
                    dd.batruns,
                    dd.win_prob,
                    LEAD(dd.win_prob) OVER (
                        PARTITION BY dd.p_match 
                        ORDER BY dd.ball_id
                    ) as next_win_prob
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.inns = 2
                AND dd.win_prob IS NOT NULL
                AND dd.win_prob != -1
                AND dd.bat_hand IN ('LHB', 'RHB')
            ),
            player_ball_impact AS (
                SELECT 
                    player,
                    team,
                    COUNT(*) as balls,
                    SUM(batruns) as runs,
                    SUM(CASE 
                        WHEN next_win_prob IS NOT NULL AND next_win_prob != -1 
                        THEN next_win_prob - win_prob 
                        ELSE 0 
                    END) as total_wp_delta,
                    AVG(win_prob) as avg_entry_wp
                FROM ball_deltas
                WHERE next_win_prob IS NOT NULL AND next_win_prob != -1
                GROUP BY player, team
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM player_ball_impact
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(total_wp_delta) as total_wp_delta,
                    AVG(avg_entry_wp) as avg_entry_wp
                FROM player_ball_impact
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player,
                ppt.team,
                pt.balls,
                pt.runs,
                ROUND(pt.total_wp_delta::numeric, 2) as wp_change_pct,
                ROUND((pt.total_wp_delta / pt.balls)::numeric, 3) as wp_per_ball,
                ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate,
                ROUND(pt.avg_entry_wp::numeric, 1) as avg_entry_wp_pct
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY pt.total_wp_delta DESC
            LIMIT 15
        """)
        
        results = db.execute(query, params).fetchall()
        
        # Split into clutch performers and pressure folders
        clutch_performers = [r for r in results if r.wp_change_pct and r.wp_change_pct > 0][:7]
        
        # Get bottom performers
        bottom_query = text(f"""
            WITH ball_deltas AS (
                SELECT 
                    dd.bat as player,
                    dd.team_bat as team,
                    dd.p_match,
                    dd.ball_id,
                    dd.batruns,
                    dd.win_prob,
                    LEAD(dd.win_prob) OVER (
                        PARTITION BY dd.p_match 
                        ORDER BY dd.ball_id
                    ) as next_win_prob
                FROM delivery_details dd
                WHERE dd.year >= :start_year
                AND dd.year <= :end_year
                AND dd.inns = 2
                AND dd.win_prob IS NOT NULL
                AND dd.win_prob != -1
                AND dd.bat_hand IN ('LHB', 'RHB')
            ),
            player_ball_impact AS (
                SELECT 
                    player,
                    team,
                    COUNT(*) as balls,
                    SUM(batruns) as runs,
                    SUM(CASE 
                        WHEN next_win_prob IS NOT NULL AND next_win_prob != -1 
                        THEN next_win_prob - win_prob 
                        ELSE 0 
                    END) as total_wp_delta
                FROM ball_deltas
                WHERE next_win_prob IS NOT NULL AND next_win_prob != -1
                GROUP BY player, team
            ),
            player_primary_team AS (
                SELECT DISTINCT ON (player) player, team
                FROM player_ball_impact
                ORDER BY player, balls DESC
            ),
            player_totals AS (
                SELECT 
                    player,
                    SUM(balls) as balls,
                    SUM(runs) as runs,
                    SUM(total_wp_delta) as total_wp_delta
                FROM player_ball_impact
                GROUP BY player
                HAVING SUM(balls) >= :min_balls
            )
            SELECT 
                pt.player,
                ppt.team,
                pt.balls,
                pt.runs,
                ROUND(pt.total_wp_delta::numeric, 2) as wp_change_pct,
                ROUND((pt.runs * 100.0 / pt.balls)::numeric, 2) as strike_rate
            FROM player_totals pt
            JOIN player_primary_team ppt ON pt.player = ppt.player
            ORDER BY pt.total_wp_delta ASC
            LIMIT 5
        """)
        
        bottom_results = db.execute(bottom_query, params).fetchall()
        pressure_folders = [r for r in bottom_results if r.wp_change_pct and r.wp_change_pct < 0]
        
        # Get coverage stats
        coverage_query = text(f"""
            SELECT 
                COUNT(*) as total_chase_balls,
                SUM(CASE WHEN win_prob IS NOT NULL AND win_prob != -1 THEN 1 ELSE 0 END) as balls_with_data
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.inns = 2
        """)
        
        coverage_result = db.execute(coverage_query, params).fetchone()
        coverage_pct = round((coverage_result.balls_with_data * 100 / coverage_result.total_chase_balls), 1) if coverage_result.total_chase_balls > 0 else 0
        
        return {
            "card_id": "chase_masters",
            "card_title": "Chase Masters",
            "card_subtitle": f"Who moves the needle in chases (min {min_balls} chase balls)",
            "visualization_type": "clutch_ranking",
            "coverage_pct": coverage_pct,
            "data_note": f"Based on {coverage_pct}% of chase deliveries with win probability",
            "clutch_performers": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "wp_change_pct": float(row.wp_change_pct) if row.wp_change_pct else 0,
                    "wp_per_ball": float(row.wp_per_ball) if row.wp_per_ball else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                    "avg_entry_wp_pct": float(row.avg_entry_wp_pct) if row.avg_entry_wp_pct else 0
                }
                for row in clutch_performers
            ],
            "pressure_folders": [
                {
                    "name": row.player,
                    "team": row.team,
                    "balls": row.balls,
                    "runs": row.runs,
                    "wp_change_pct": float(row.wp_change_pct) if row.wp_change_pct else 0,
                    "strike_rate": float(row.strike_rate) if row.strike_rate else 0
                }
                for row in pressure_folders
            ],
            "deep_links": {
                "query_builder": f"/query?start_date={start_date}&end_date={end_date}&innings=2&group_by=batter"
            }
        }
