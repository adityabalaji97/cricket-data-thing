from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from models import Match, Delivery, BattingStats, BowlingStats, teams_mapping
import logging
from tqdm import tqdm
from database import get_database_connection
from fantasy_points_v2 import FantasyPointsCalculator

class StatsProcessor:
    def __init__(self, session: Session):
        self.session = session
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def process_all_statistics(self, incremental: bool = True, force_update: bool = False, standardize_teams: bool = True):
        """
        Process statistics for matches in the database.
        Args:
            incremental: If True, only process matches without existing stats
            force_update: If True, recalculate all stats even if they exist
        """
        try:
            # Get matches that need processing
            if incremental and not force_update:
                # Get matches without stats
                processed_matches = (self.session.query(Match.id)
                    .join(BattingStats, Match.id == BattingStats.match_id)
                    .distinct())
                
                matches = (self.session.query(Match.id)
                    .filter(~Match.id.in_(processed_matches))
                    .all())
                
                if not matches:
                    self.logger.info("No new matches found to process")
                    return
            else:
                matches = self.session.query(Match.id).all()
            
            total_matches = len(matches)
            self.logger.info(f"Processing statistics for {total_matches} matches")
            
            # Process each match with a progress bar
            for match in tqdm(matches, desc="Processing matches"):
                self.process_match_statistics(match.id, force_update, standardize_teams)
                
            self.session.commit()
            self.logger.info("Successfully processed match statistics")
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing statistics: {str(e)}")
            raise
    
    def process_match_statistics(self, match_id: str, force_update: bool = False, standardize_teams: bool = True):
        """Process or update statistics for a single match"""
        try:
            # Check if stats exist for this match and if we need to update
            if not force_update:
                existing_batting = self.session.query(BattingStats).filter(
                    BattingStats.match_id == match_id
                ).first()
                
                existing_bowling = self.session.query(BowlingStats).filter(
                    BowlingStats.match_id == match_id
                ).first()
                
                if existing_batting and existing_bowling:
                    return
            
            # Get all deliveries for the match
            deliveries = self.session.query(Delivery).filter(
                Delivery.match_id == match_id
            ).order_by(Delivery.innings, Delivery.over, Delivery.ball).all()
            
            if not deliveries:
                self.logger.warning(f"No deliveries found for match {match_id}")
                return
            
            # Process batting stats
            self._process_batting_stats(match_id, deliveries)
            
            # Process bowling stats
            self._process_bowling_stats(match_id, deliveries)
            
            # Update team names to ensure uniformity if standardize_teams is True
            if standardize_teams:
                self._standardize_team_names(match_id)
            
            # Commit after each match
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing match {match_id}: {str(e)}")
            raise
    
    def _process_batting_stats(self, match_id: str, deliveries: List[Delivery]):
        """Process batting statistics for all batters in a match"""
        for innings in [1, 2]:
            innings_deliveries = [d for d in deliveries if d.innings == innings]
            batters = set(d.batter for d in innings_deliveries)
            
            for batter in batters:
                # Calculate batting stats
                stats = self._calculate_batting_stats(match_id, innings, batter, innings_deliveries)
                
                # Update or create stats record
                existing = self.session.query(BattingStats).filter(
                    BattingStats.match_id == match_id,
                    BattingStats.innings == innings,
                    BattingStats.striker == batter
                ).first()
                
                if existing:
                    # Update all fields
                    for key, value in stats.__dict__.items():
                        if not key.startswith('_'):
                            setattr(existing, key, value)
                else:
                    self.session.add(stats)
    
    def _process_bowling_stats(self, match_id: str, deliveries: List[Delivery]):
        """Process bowling statistics for all bowlers in a match"""
        for innings in [1, 2]:
            innings_deliveries = [d for d in deliveries if d.innings == innings]
            bowlers = set(d.bowler for d in innings_deliveries)
            
            for bowler in bowlers:
                # Calculate bowling stats
                stats = self._calculate_bowling_stats(match_id, innings, bowler, innings_deliveries)
                
                # Update or create stats record
                existing = self.session.query(BowlingStats).filter(
                    BowlingStats.match_id == match_id,
                    BowlingStats.innings == innings,
                    BowlingStats.bowler == bowler
                ).first()
                
                if existing:
                    # Update all fields
                    for key, value in stats.__dict__.items():
                        if not key.startswith('_'):
                            setattr(existing, key, value)
                else:
                    self.session.add(stats)
    
    def _calculate_batting_stats(self, match_id: str, innings: int, batter: str, 
                               innings_deliveries: List[Delivery]) -> BattingStats:
        """Calculate detailed batting statistics"""
        # Filter deliveries for this batter
        batter_deliveries = [d for d in innings_deliveries if d.batter == batter]
        
        if not batter_deliveries:
            self.logger.warning(f"No deliveries found for batter {batter} in match {match_id} innings {innings}")
            return None
            
        # Get the team name and standardize it if it exists in teams_mapping
        batting_team = batter_deliveries[0].batting_team
        
        stats = BattingStats(
            match_id=match_id,
            innings=innings,
            striker=batter,
            batting_team=batting_team
        )
        
        # Initialize fantasy points (will be set later)
        stats.fantasy_points = 0
        
        # Calculate basic stats
        stats.runs = sum(d.runs_off_bat for d in batter_deliveries)
        stats.balls_faced = len(batter_deliveries)
        stats.wickets = sum(1 for d in batter_deliveries if d.player_dismissed == d.batter)
        stats.dots = sum(1 for d in batter_deliveries if d.runs_off_bat == 0)
        stats.ones = sum(1 for d in batter_deliveries if d.runs_off_bat == 1)
        stats.twos = sum(1 for d in batter_deliveries if d.runs_off_bat == 2)
        stats.threes = sum(1 for d in batter_deliveries if d.runs_off_bat == 3)
        stats.fours = sum(1 for d in batter_deliveries if d.runs_off_bat == 4)
        stats.sixes = sum(1 for d in batter_deliveries if d.runs_off_bat == 6)
        
        if stats.balls_faced > 0:
            stats.strike_rate = (stats.runs * 100.0) / stats.balls_faced
        
        # Calculate phase-wise stats
        pp_deliveries = [d for d in batter_deliveries if d.over < 6]
        middle_deliveries = [d for d in batter_deliveries if 6 <= d.over < 15]
        death_deliveries = [d for d in batter_deliveries if d.over >= 15]
        
        # Powerplay stats
        stats.pp_runs = sum(d.runs_off_bat for d in pp_deliveries)
        stats.pp_balls = len(pp_deliveries)
        stats.pp_dots = sum(1 for d in pp_deliveries if d.runs_off_bat == 0)
        stats.pp_wickets = sum(1 for d in pp_deliveries if d.player_dismissed == d.batter)
        stats.pp_boundaries = sum(1 for d in pp_deliveries if d.runs_off_bat in [4, 6])
        if stats.pp_balls > 0:
            stats.pp_strike_rate = (stats.pp_runs * 100.0) / stats.pp_balls
        
        # Middle overs stats
        stats.middle_runs = sum(d.runs_off_bat for d in middle_deliveries)
        stats.middle_balls = len(middle_deliveries)
        stats.middle_dots = sum(1 for d in middle_deliveries if d.runs_off_bat == 0)
        stats.middle_wickets = sum(1 for d in middle_deliveries if d.player_dismissed == d.batter)
        stats.middle_boundaries = sum(1 for d in middle_deliveries if d.runs_off_bat in [4, 6])
        if stats.middle_balls > 0:
            stats.middle_strike_rate = (stats.middle_runs * 100.0) / stats.middle_balls
        
        # Death overs stats
        stats.death_runs = sum(d.runs_off_bat for d in death_deliveries)
        stats.death_balls = len(death_deliveries)
        stats.death_dots = sum(1 for d in death_deliveries if d.runs_off_bat == 0)
        stats.death_wickets = sum(1 for d in death_deliveries if d.player_dismissed == d.batter)
        stats.death_boundaries = sum(1 for d in death_deliveries if d.runs_off_bat in [4, 6])
        if stats.death_balls > 0:
            stats.death_strike_rate = (stats.death_runs * 100.0) / stats.death_balls
        
        # Calculate comparative team stats
        other_batters_deliveries = [d for d in innings_deliveries if d.batter != batter]
        stats.team_runs_excl_batter = sum(d.runs_off_bat for d in other_batters_deliveries)
        stats.team_balls_excl_batter = len(other_batters_deliveries)
        
        if stats.team_balls_excl_batter > 0:
            stats.team_sr_excl_batter = (stats.team_runs_excl_batter * 100.0) / stats.team_balls_excl_batter
            stats.sr_diff = stats.strike_rate - stats.team_sr_excl_batter
        
        # Calculate batting position and entry stats
        if batter_deliveries:
            first_ball = min(batter_deliveries, key=lambda x: (x.over, x.ball))
            stats.batting_position = len(set(
                d.batter for d in innings_deliveries 
                if d.over < first_ball.over or (d.over == first_ball.over and d.ball <= first_ball.ball)
            ))
            
            stats.entry_overs = first_ball.over + (first_ball.ball / 6)
            stats.entry_runs = sum(d.runs_off_bat for d in innings_deliveries if 
                                 d.over < first_ball.over or (d.over == first_ball.over and d.ball < first_ball.ball))
            stats.entry_balls = sum(1 for d in innings_deliveries if 
                                  d.over < first_ball.over or (d.over == first_ball.over and d.ball < first_ball.ball))
        
        # Calculate fantasy points
        fantasy_calculator = FantasyPointsCalculator()
        stats.fantasy_points = fantasy_calculator.calculate_batting_points(stats)
        self.logger.info(f"Fantasy points for {batter} in match {match_id}, innings {innings}: {stats.fantasy_points}")
        
        return stats
    
    def standardize_all_team_names(self):
        """Standardize team names in all batting_stats and bowling_stats records"""
        try:
            self.logger.info("Starting team name standardization for all records")
            
            # Get all teams that map to the same abbreviation
            team_groups = {}
            for team_name, abbrev in teams_mapping.items():
                if abbrev not in team_groups:
                    team_groups[abbrev] = []
                team_groups[abbrev].append(team_name)
            
            # Process each abbreviation group
            for abbrev, team_names in team_groups.items():
                if len(team_names) <= 1:
                    continue  # No need to standardize if there's only one name
                    
                # Use the first team name in the group for consistency
                standard_name = team_names[0]
                
                # Update batting_stats
                for team_name in team_names[1:]:  # Skip the first one as it's our standard
                    count = self.session.query(BattingStats).filter(BattingStats.batting_team == team_name).count()
                    if count > 0:
                        self.session.query(BattingStats)\
                            .filter(BattingStats.batting_team == team_name)\
                            .update({BattingStats.batting_team: standard_name})
                        self.logger.info(f"Updated {count} batting records: '{team_name}' -> '{standard_name}'")
                
                # Update bowling_stats
                for team_name in team_names[1:]:  # Skip the first one as it's our standard
                    count = self.session.query(BowlingStats).filter(BowlingStats.bowling_team == team_name).count()
                    if count > 0:
                        self.session.query(BowlingStats)\
                            .filter(BowlingStats.bowling_team == team_name)\
                            .update({BowlingStats.bowling_team: standard_name})
                        self.logger.info(f"Updated {count} bowling records: '{team_name}' -> '{standard_name}'")
            
            # Commit all changes
            self.session.commit()
            self.logger.info("Completed team name standardization for all records")
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error standardizing team names: {str(e)}")
            raise
    
    def _standardize_team_names(self, match_id: str):
        """Update team names in batting_stats and bowling_stats to use standardized names from teams_mapping"""
        try:
            # Get all teams that map to the same abbreviation
            team_groups = {}
            for team_name, abbrev in teams_mapping.items():
                if abbrev not in team_groups:
                    team_groups[abbrev] = []
                team_groups[abbrev].append(team_name)
            
            # Update batting_stats
            for abbrev, team_names in team_groups.items():
                # First, find any records with these team names
                for team_name in team_names:
                    # Use the first team name in the group for consistency
                    standard_name = team_names[0]
                    
                    # Update team names for all matches
                    self.session.query(BattingStats)\
                        .filter(BattingStats.match_id == match_id)\
                        .filter(BattingStats.batting_team == team_name)\
                        .update({BattingStats.batting_team: standard_name})
            
            # Update bowling_stats
            for abbrev, team_names in team_groups.items():
                # First, find any records with these team names
                for team_name in team_names:
                    # Use the first team name in the group for consistency
                    standard_name = team_names[0]
                    
                    # Update team names for all matches
                    self.session.query(BowlingStats)\
                        .filter(BowlingStats.match_id == match_id)\
                        .filter(BowlingStats.bowling_team == team_name)\
                        .update({BowlingStats.bowling_team: standard_name})
            
            self.logger.info(f"Standardized team names for match {match_id}")
        except Exception as e:
            self.logger.error(f"Error standardizing team names for match {match_id}: {str(e)}")
            raise
    
    def _calculate_bowling_stats(self, match_id: str, innings: int, bowler: str, 
                               innings_deliveries: List[Delivery]) -> BowlingStats:
        """Calculate detailed bowling statistics"""
        # Filter deliveries for this bowler
        bowler_deliveries = [d for d in innings_deliveries if d.bowler == bowler]
        
        if not bowler_deliveries:
            self.logger.warning(f"No deliveries found for bowler {bowler} in match {match_id} innings {innings}")
            return None
            
        # Get the team name and standardize it if it exists in teams_mapping
        bowling_team = bowler_deliveries[0].bowling_team
        
        stats = BowlingStats(
            match_id=match_id,
            innings=innings,
            bowler=bowler,
            bowling_team=bowling_team
        )
        
        # Initialize fantasy points (will be set later)
        stats.fantasy_points = 0
        
        # Calculate basic stats
        stats.overs = len(bowler_deliveries) / 6
        stats.runs_conceded = sum(d.runs_off_bat + d.extras for d in bowler_deliveries)
        stats.wickets = sum(1 for d in bowler_deliveries if d.wicket_type in [
            'bowled', 'caught', 'lbw', 'caught and bowled', 'stumped', 'hit wicket'
        ])
        stats.dots = sum(1 for d in bowler_deliveries if d.runs_off_bat == 0 and d.extras == 0)
        stats.fours_conceded = sum(1 for d in bowler_deliveries if d.runs_off_bat == 4)
        stats.sixes_conceded = sum(1 for d in bowler_deliveries if d.runs_off_bat == 6)
        stats.extras = sum(d.extras for d in bowler_deliveries)
        
        if stats.overs > 0:
            stats.economy = stats.runs_conceded / stats.overs
        
        # Calculate phase-wise stats
        pp_deliveries = [d for d in bowler_deliveries if d.over < 6]
        middle_deliveries = [d for d in bowler_deliveries if 6 <= d.over < 15]
        death_deliveries = [d for d in bowler_deliveries if d.over >= 15]
        
        # Powerplay stats
        stats.pp_overs = len(pp_deliveries) / 6
        stats.pp_runs = sum(d.runs_off_bat + d.extras for d in pp_deliveries)
        stats.pp_wickets = sum(1 for d in pp_deliveries if d.wicket_type in [
            'bowled', 'caught', 'lbw', 'caught and bowled', 'stumped', 'hit wicket'
        ])
        stats.pp_dots = sum(1 for d in pp_deliveries if d.runs_off_bat == 0 and d.extras == 0)
        stats.pp_boundaries = sum(1 for d in pp_deliveries if d.runs_off_bat in [4, 6])
        if stats.pp_overs > 0:
            stats.pp_economy = stats.pp_runs / stats.pp_overs
        
        # Middle overs stats
        stats.middle_overs = len(middle_deliveries) / 6
        stats.middle_runs = sum(d.runs_off_bat + d.extras for d in middle_deliveries)
        stats.middle_wickets = sum(1 for d in middle_deliveries if d.wicket_type in [
            'bowled', 'caught', 'lbw', 'caught and bowled', 'stumped', 'hit wicket'
        ])
        stats.middle_dots = sum(1 for d in middle_deliveries if d.runs_off_bat == 0 and d.extras == 0)
        stats.middle_boundaries = sum(1 for d in middle_deliveries if d.runs_off_bat in [4, 6])
        if stats.middle_overs > 0:
            stats.middle_economy = stats.middle_runs / stats.middle_overs
        
        # Death overs stats
        stats.death_overs = len(death_deliveries) / 6
        stats.death_runs = sum(d.runs_off_bat + d.extras for d in death_deliveries)
        stats.death_wickets = sum(1 for d in death_deliveries if d.wicket_type in [
            'bowled', 'caught', 'lbw', 'caught and bowled', 'stumped', 'hit wicket'
        ])
        stats.death_dots = sum(1 for d in death_deliveries if d.runs_off_bat == 0 and d.extras == 0)
        stats.death_boundaries = sum(1 for d in death_deliveries if d.runs_off_bat in [4, 6])
        if stats.death_overs > 0:
            stats.death_economy = stats.death_runs / stats.death_overs
        
        # Calculate comparative team stats
        other_bowlers_deliveries = [d for d in innings_deliveries if d.bowler != bowler]
        stats.team_runs_excl_bowler = sum(d.runs_off_bat + d.extras for d in other_bowlers_deliveries)
        stats.team_overs_excl_bowler = len(other_bowlers_deliveries) / 6
        
        if stats.team_overs_excl_bowler > 0:
            stats.team_economy_excl_bowler = stats.team_runs_excl_bowler / stats.team_overs_excl_bowler
            stats.economy_diff = stats.economy - stats.team_economy_excl_bowler
        
        # Calculate fantasy points
        fantasy_calculator = FantasyPointsCalculator()
        stats.fantasy_points = fantasy_calculator.calculate_bowling_points(stats)
        self.logger.info(f"Fantasy points for bowler {bowler} in match {match_id}, innings {innings}: {stats.fantasy_points}")
        
        return stats

def main():
    engine, SessionLocal = get_database_connection()

    # Process all statistics
    with SessionLocal() as session:
        processor = StatsProcessor(session)
        
        try:
            # Choose one of the following processing options:
            
            # Option 1: Process all matches (force_update=True to recalculate everything)
            # processor.process_all_statistics(force_update=True)

            # Option 2: Process only new matches
            processor.process_all_statistics(incremental=True, force_update=False)
            
            # Option 3: Process a specific match
            # processor.process_match_statistics("match_id_here")
            
            # Option 4: Standardize team names in all existing statistics
            # processor.standardize_all_team_names()
            
        except Exception as e:
            logging.error(f"Error in main processing: {str(e)}")
            raise

if __name__ == "__main__":
    main()