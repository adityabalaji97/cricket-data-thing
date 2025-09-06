from typing import List, Dict, Tuple, Optional
from models import BattingStats, BowlingStats, Delivery
from sqlalchemy.orm import Session
import logging

class FantasyPointsCalculator:
    def __init__(self):
        # Constants for fantasy points
        # Batting points
        self.RUN_POINT = 1
        self.BOUNDARY_BONUS = 4
        self.SIX_BONUS = 6
        self.RUNS_25_BONUS = 4
        self.RUNS_50_BONUS = 8
        self.RUNS_75_BONUS = 12
        self.RUNS_100_BONUS = 16
        self.DUCK_PENALTY = -2

        # Bowling points
        self.DOT_BALL_POINT = 1
        self.WICKET_POINT = 25
        self.LBW_BOWLED_BONUS = 8
        self.WICKETS_3_BONUS = 4
        self.WICKETS_4_BONUS = 8
        self.WICKETS_5_BONUS = 12
        self.MAIDEN_OVER_POINT = 12

        # Fielding points
        self.CATCH_POINT = 8
        self.CATCHES_3_BONUS = 4
        self.STUMPING_POINT = 12
        self.RUNOUT_DIRECT_POINT = 12
        self.RUNOUT_INDIRECT_POINT = 6

        # Economy rate points (min 2 overs)
        self.ECONOMY_BELOW_5 = 6
        self.ECONOMY_5_TO_6 = 4
        self.ECONOMY_6_TO_7 = 2
        self.ECONOMY_10_TO_11 = -2
        self.ECONOMY_11_TO_12 = -4
        self.ECONOMY_ABOVE_12 = -6

        # Strike rate points (min 10 balls)
        self.SR_ABOVE_170 = 6
        self.SR_150_TO_170 = 4
        self.SR_130_TO_150 = 2
        self.SR_60_TO_70 = -2
        self.SR_50_TO_60 = -4
        self.SR_BELOW_50 = -6
        
        # Logger setup
        self.logger = logging.getLogger(__name__)

    def calculate_batting_points(self, stats: BattingStats) -> float:
        """
        Calculate fantasy points for a batter's batting performance only
        
        Args:
            stats (BattingStats): Batting statistics object
        
        Returns:
            float: Batting fantasy points
        """
        points = 0
        point_breakdown = {}
        
        # Base run points
        run_points = stats.runs * self.RUN_POINT
        points += run_points
        point_breakdown['run_points'] = run_points
        
        # Boundary bonuses
        boundary_points = stats.fours * self.BOUNDARY_BONUS
        points += boundary_points
        point_breakdown['boundary_points'] = boundary_points
        
        six_points = stats.sixes * self.SIX_BONUS
        points += six_points
        point_breakdown['six_points'] = six_points
        
        # Run milestones
        milestone_points = 0
        if stats.runs >= 100:
            milestone_points = self.RUNS_100_BONUS
            point_breakdown['milestone'] = 'century'
        elif stats.runs >= 75:
            milestone_points = self.RUNS_75_BONUS
            point_breakdown['milestone'] = '75_runs'
        elif stats.runs >= 50:
            milestone_points = self.RUNS_50_BONUS
            point_breakdown['milestone'] = 'half_century'
        elif stats.runs >= 25:
            milestone_points = self.RUNS_25_BONUS
            point_breakdown['milestone'] = '25_runs'
        
        points += milestone_points
        point_breakdown['milestone_points'] = milestone_points
        
        # Duck penalty
        duck_points = 0
        if stats.runs == 0 and stats.wickets > 0:
            duck_points = self.DUCK_PENALTY
            points += duck_points
        point_breakdown['duck_points'] = duck_points
        
        # Strike rate points (min 10 balls)
        sr_points = 0
        if stats.balls_faced >= 10:
            sr = stats.strike_rate
            if sr > 170:
                sr_points = self.SR_ABOVE_170
                point_breakdown['sr_category'] = '>170'
            elif 150 < sr <= 170:
                sr_points = self.SR_150_TO_170
                point_breakdown['sr_category'] = '150-170'
            elif 130 <= sr <= 150:
                sr_points = self.SR_130_TO_150
                point_breakdown['sr_category'] = '130-150'
            elif 60 <= sr < 70:
                sr_points = self.SR_60_TO_70
                point_breakdown['sr_category'] = '60-70'
            elif 50 <= sr < 60:
                sr_points = self.SR_50_TO_60
                point_breakdown['sr_category'] = '50-60'
            elif sr < 50:
                sr_points = self.SR_BELOW_50
                point_breakdown['sr_category'] = '<50'
        
        points += sr_points
        point_breakdown['sr_points'] = sr_points
        
        self.logger.debug(f"Batting points for {stats.striker}: {points}, breakdown: {point_breakdown}")
        return points
    
    def calculate_bowling_points(self, stats: BowlingStats) -> float:
        """
        Calculate fantasy points for a bowler's bowling performance only
        
        Args:
            stats (BowlingStats): Bowling statistics object
        
        Returns:
            float: Bowling fantasy points
        """
        points = 0
        point_breakdown = {}
        
        # Dots
        dot_points = stats.dots * self.DOT_BALL_POINT
        points += dot_points
        point_breakdown['dot_points'] = dot_points
        
        # Wickets
        wicket_points = stats.wickets * self.WICKET_POINT
        points += wicket_points
        point_breakdown['wicket_points'] = wicket_points
        
        # Wicket milestones
        milestone_points = 0
        if stats.wickets >= 5:
            milestone_points = self.WICKETS_5_BONUS
            point_breakdown['milestone'] = '5_wickets'
        elif stats.wickets >= 4:
            milestone_points = self.WICKETS_4_BONUS
            point_breakdown['milestone'] = '4_wickets'
        elif stats.wickets >= 3:
            milestone_points = self.WICKETS_3_BONUS
            point_breakdown['milestone'] = '3_wickets'
        
        points += milestone_points
        point_breakdown['milestone_points'] = milestone_points
        
        # Economy rate points (min 2 overs)
        economy_points = 0
        if stats.overs >= 2:
            economy = stats.economy
            if economy < 5:
                economy_points = self.ECONOMY_BELOW_5
                point_breakdown['economy_category'] = '<5'
            elif 5 <= economy < 6:
                economy_points = self.ECONOMY_5_TO_6
                point_breakdown['economy_category'] = '5-6'
            elif 6 <= economy <= 7:
                economy_points = self.ECONOMY_6_TO_7
                point_breakdown['economy_category'] = '6-7'
            elif 10 <= economy < 11:
                economy_points = self.ECONOMY_10_TO_11
                point_breakdown['economy_category'] = '10-11'
            elif 11 <= economy < 12:
                economy_points = self.ECONOMY_11_TO_12
                point_breakdown['economy_category'] = '11-12'
            elif economy >= 12:
                economy_points = self.ECONOMY_ABOVE_12
                point_breakdown['economy_category'] = '>12'
        
        points += economy_points
        point_breakdown['economy_points'] = economy_points
        
        self.logger.debug(f"Bowling points for {stats.bowler}: {points}, breakdown: {point_breakdown}")
        return points
    
    def calculate_fielding_points(self, player_name: str, innings_deliveries: List[Delivery]) -> Dict:
        """
        Calculate fielding points for a player
        
        Args:
            player_name (str): Player name
            innings_deliveries (List[Delivery]): All deliveries in the innings
        
        Returns:
            Dict: Fielding points breakdown
        """
        stats = {
            'catches': 0,
            'stumpings': 0,
            'run_outs': 0,
            'total_points': 0
        }
        
        # Count catches
        stats['catches'] = sum(1 for d in innings_deliveries 
                    if d.fielder == player_name and d.wicket_type == 'caught')
        
        # Count stumpings
        stats['stumpings'] = sum(1 for d in innings_deliveries 
                      if d.fielder == player_name and d.wicket_type == 'stumped')
        
        # Count run outs
        stats['run_outs'] = sum(1 for d in innings_deliveries 
                    if d.fielder == player_name and d.wicket_type == 'run out')
        
        # Calculate points
        catch_points = stats['catches'] * self.CATCH_POINT
        catch_bonus = self.CATCHES_3_BONUS if stats['catches'] >= 3 else 0
        stumping_points = stats['stumpings'] * self.STUMPING_POINT
        # For simplicity, assume all run outs are indirect
        runout_points = stats['run_outs'] * self.RUNOUT_INDIRECT_POINT
        
        total_points = catch_points + catch_bonus + stumping_points + runout_points
        stats['total_points'] = total_points
        
        return stats
    
    def calculate_lbw_bowled_bonus(self, bowler: str, innings_deliveries: List[Delivery]) -> float:
        """
        Calculate LBW/Bowled bonus points for a bowler
        
        Args:
            bowler (str): Bowler name
            innings_deliveries (List[Delivery]): All deliveries in the innings
        
        Returns:
            float: LBW/Bowled bonus points
        """
        # Count LBW/Bowled wickets
        bowler_deliveries = [d for d in innings_deliveries if d.bowler == bowler]
        lbw_bowled_wickets = sum(1 for d in bowler_deliveries if d.wicket_type in ['bowled', 'lbw'])
        
        # Calculate bonus points
        lbw_bowled_points = lbw_bowled_wickets * self.LBW_BOWLED_BONUS
        
        return lbw_bowled_points
    
    def calculate_maidens(self, bowler: str, innings_deliveries: List[Delivery]) -> int:
        """
        Calculate the number of maiden overs bowled
        
        Args:
            bowler (str): Bowler name
            innings_deliveries (List[Delivery]): All deliveries in the innings
        
        Returns:
            int: Number of maiden overs
        """
        # Group deliveries by over
        overs = {}
        for d in innings_deliveries:
            if d.bowler == bowler:
                if d.over not in overs:
                    overs[d.over] = []
                overs[d.over].append(d)
        
        # Count maiden overs (overs with no runs conceded, including extras)
        maidens = 0
        for over_num, deliveries in overs.items():
            # Check if this is a complete over (6 balls)
            if len(deliveries) == 6:
                runs_in_over = sum(d.runs_off_bat + d.extras for d in deliveries)
                if runs_in_over == 0:
                    maidens += 1
        
        return maidens
    
    def calculate_player_points(self, match_id: str, player_name: str, all_deliveries: List[Delivery], 
                               batting_stats: Optional[BattingStats] = None, 
                               bowling_stats: Optional[BowlingStats] = None) -> Dict:
        """
        Calculate total fantasy points for a player including batting, bowling and fielding
        
        Args:
            match_id (str): Match ID
            player_name (str): Player name
            all_deliveries (List[Delivery]): All deliveries in the match
            batting_stats (Optional[BattingStats]): Batting statistics
            bowling_stats (Optional[BowlingStats]): Bowling statistics
        
        Returns:
            Dict: Fantasy points breakdown
        """
        result = {
            'player': player_name,
            'match_id': match_id,
            'batting_points': 0,
            'bowling_points': 0,
            'fielding_points': 0,
            'total_points': 0,
            'fielding_breakdown': {
                'catches': 0,
                'stumpings': 0,
                'run_outs': 0
            },
            'role': 'Fielding'  # Default role, will be updated based on contributions
        }
        
        # Calculate batting points
        if batting_stats:
            result['batting_points'] = self.calculate_batting_points(batting_stats)
            result['role'] = 'Batting'
        
        # Calculate bowling points
        if bowling_stats:
            # Basic bowling points
            bowling_points = self.calculate_bowling_points(bowling_stats)
            
            # Calculate additional bowling points
            innings_deliveries = [d for d in all_deliveries if d.innings == bowling_stats.innings]
            
            # LBW/Bowled bonus
            lbw_bowled_points = self.calculate_lbw_bowled_bonus(player_name, innings_deliveries)
            
            # Maiden overs
            maidens = self.calculate_maidens(player_name, innings_deliveries)
            maiden_points = maidens * self.MAIDEN_OVER_POINT
            
            # Total bowling points
            result['bowling_points'] = bowling_points + lbw_bowled_points + maiden_points
            
            # Update role
            if result['role'] == 'Batting':
                result['role'] = 'All-round'
            else:
                result['role'] = 'Bowling'
        
        # Calculate fielding points
        fielding_stats = self.calculate_fielding_points(player_name, all_deliveries)
        result['fielding_points'] = fielding_stats['total_points']
        result['fielding_breakdown'] = {
            'catches': fielding_stats['catches'],
            'stumpings': fielding_stats['stumpings'],
            'run_outs': fielding_stats['run_outs']
        }
        
        # Calculate total points
        result['total_points'] = result['batting_points'] + result['bowling_points'] + result['fielding_points']
        
        return result

    def calculate_match_fantasy_points(self, match_id: str, session: Session) -> Dict[str, Dict]:
        """
        Calculate fantasy points for all players in a match
        
        Args:
            match_id (str): Match ID
            session (Session): Database session
        
        Returns:
            Dict[str, Dict]: Fantasy points by player
        """
        from models import BattingStats, BowlingStats, Delivery
        
        # Get all deliveries for the match
        all_deliveries = session.query(Delivery).filter(
            Delivery.match_id == match_id
        ).order_by(Delivery.innings, Delivery.over, Delivery.ball).all()
        
        # Get batting stats
        batting_stats = session.query(BattingStats).filter(
            BattingStats.match_id == match_id
        ).all()
        
        # Get bowling stats
        bowling_stats = session.query(BowlingStats).filter(
            BowlingStats.match_id == match_id
        ).all()
        
        # Create dictionaries for quick lookup
        batting_by_player = {stats.striker: stats for stats in batting_stats}
        bowling_by_player = {stats.bowler: stats for stats in bowling_stats}
        
        # Get all unique players (batters, bowlers, and fielders)
        all_players = set()
        for stats in batting_stats:
            all_players.add(stats.striker)
        for stats in bowling_stats:
            all_players.add(stats.bowler)
        for delivery in all_deliveries:
            if delivery.fielder:
                all_players.add(delivery.fielder)
        
        # Calculate points for each player
        results = {}
        for player in all_players:
            batting = batting_by_player.get(player)
            bowling = bowling_by_player.get(player)
            
            player_points = self.calculate_player_points(
                match_id, player, all_deliveries, batting, bowling
            )
            
            results[player] = player_points
        
        return results

    def calculate_expected_batting_points_from_matchup(self, matchup_stats: Dict) -> Dict:
        """
        Calculate expected fantasy points from matchup statistics
        
        Args:
            matchup_stats (Dict): Matchup statistics containing runs, balls, wickets, etc.
        
        Returns:
            Dict: Expected fantasy points breakdown
        """
        if not matchup_stats or matchup_stats.get('balls', 0) == 0:
            return {
                'expected_batting_points': 0,
                'confidence': 0,
                'breakdown': {}
            }
        
        # Extract stats
        runs = matchup_stats.get('runs', 0)
        balls = matchup_stats.get('balls', 0)
        wickets = matchup_stats.get('wickets', 0)
        boundaries = matchup_stats.get('boundaries', 0)
        strike_rate = matchup_stats.get('strike_rate', 0)
        
        # Estimate fours and sixes (simplified assumption: 70% fours, 30% sixes)
        estimated_fours = int(boundaries * 0.7)
        estimated_sixes = int(boundaries * 0.3)
        
        points = 0
        breakdown = {}
        
        # Base run points
        run_points = runs * self.RUN_POINT
        points += run_points
        breakdown['run_points'] = run_points
        
        # Boundary bonuses
        boundary_points = estimated_fours * self.BOUNDARY_BONUS
        points += boundary_points
        breakdown['boundary_points'] = boundary_points
        
        six_points = estimated_sixes * self.SIX_BONUS
        points += six_points
        breakdown['six_points'] = six_points
        
        # Run milestones
        milestone_points = 0
        if runs >= 100:
            milestone_points = self.RUNS_100_BONUS
            breakdown['milestone'] = 'century'
        elif runs >= 75:
            milestone_points = self.RUNS_75_BONUS
            breakdown['milestone'] = '75_runs'
        elif runs >= 50:
            milestone_points = self.RUNS_50_BONUS
            breakdown['milestone'] = 'half_century'
        elif runs >= 25:
            milestone_points = self.RUNS_25_BONUS
            breakdown['milestone'] = '25_runs'
        
        points += milestone_points
        breakdown['milestone_points'] = milestone_points
        
        # Duck penalty (if wickets > 0 and runs = 0)
        duck_points = 0
        if runs == 0 and wickets > 0:
            duck_points = self.DUCK_PENALTY
            points += duck_points
        breakdown['duck_points'] = duck_points
        
        # Strike rate points (min 10 balls)
        sr_points = 0
        if balls >= 10:
            if strike_rate > 170:
                sr_points = self.SR_ABOVE_170
                breakdown['sr_category'] = '>170'
            elif 150 < strike_rate <= 170:
                sr_points = self.SR_150_TO_170
                breakdown['sr_category'] = '150-170'
            elif 130 <= strike_rate <= 150:
                sr_points = self.SR_130_TO_150
                breakdown['sr_category'] = '130-150'
            elif 60 <= strike_rate < 70:
                sr_points = self.SR_60_TO_70
                breakdown['sr_category'] = '60-70'
            elif 50 <= strike_rate < 60:
                sr_points = self.SR_50_TO_60
                breakdown['sr_category'] = '50-60'
            elif strike_rate < 50:
                sr_points = self.SR_BELOW_50
                breakdown['sr_category'] = '<50'
        
        points += sr_points
        breakdown['sr_points'] = sr_points
        
        # Calculate confidence based on sample size
        confidence = min(balls / 30.0, 1.0)  # Full confidence at 30+ balls
        
        return {
            'expected_batting_points': round(points, 2),
            'confidence': round(confidence, 2),
            'breakdown': breakdown
        }
    
    def calculate_expected_bowling_points_from_matchup(self, matchup_stats: Dict) -> Dict:
        """
        Calculate expected bowling fantasy points from matchup statistics
        
        Args:
            matchup_stats (Dict): Bowling matchup statistics
        
        Returns:
            Dict: Expected bowling fantasy points breakdown
        """
        if not matchup_stats or matchup_stats.get('balls', 0) == 0:
            return {
                'expected_bowling_points': 0,
                'confidence': 0,
                'breakdown': {}
            }
        
        # Extract stats
        runs = matchup_stats.get('runs', 0)
        balls = matchup_stats.get('balls', 0)
        wickets = matchup_stats.get('wickets', 0)
        dots = matchup_stats.get('dots', 0)
        economy = matchup_stats.get('economy', 0)
        
        # Calculate overs
        overs = balls / 6.0
        
        points = 0
        breakdown = {}
        
        # Dot ball points
        dot_points = dots * self.DOT_BALL_POINT
        points += dot_points
        breakdown['dot_points'] = dot_points
        
        # Wicket points
        wicket_points = wickets * self.WICKET_POINT
        points += wicket_points
        breakdown['wicket_points'] = wicket_points
        
        # Wicket milestones
        milestone_points = 0
        if wickets >= 5:
            milestone_points = self.WICKETS_5_BONUS
            breakdown['milestone'] = '5_wickets'
        elif wickets >= 4:
            milestone_points = self.WICKETS_4_BONUS
            breakdown['milestone'] = '4_wickets'
        elif wickets >= 3:
            milestone_points = self.WICKETS_3_BONUS
            breakdown['milestone'] = '3_wickets'
        
        points += milestone_points
        breakdown['milestone_points'] = milestone_points
        
        # Economy rate points (min 2 overs)
        economy_points = 0
        if overs >= 2:
            if economy < 5:
                economy_points = self.ECONOMY_BELOW_5
                breakdown['economy_category'] = '<5'
            elif 5 <= economy < 6:
                economy_points = self.ECONOMY_5_TO_6
                breakdown['economy_category'] = '5-6'
            elif 6 <= economy <= 7:
                economy_points = self.ECONOMY_6_TO_7
                breakdown['economy_category'] = '6-7'
            elif 10 <= economy < 11:
                economy_points = self.ECONOMY_10_TO_11
                breakdown['economy_category'] = '10-11'
            elif 11 <= economy < 12:
                economy_points = self.ECONOMY_11_TO_12
                breakdown['economy_category'] = '11-12'
            elif economy >= 12:
                economy_points = self.ECONOMY_ABOVE_12
                breakdown['economy_category'] = '>12'
        
        points += economy_points
        breakdown['economy_points'] = economy_points
        
        # Calculate confidence based on sample size
        confidence = min(balls / 24.0, 1.0)  # Full confidence at 24+ balls (4 overs)
        
        return {
            'expected_bowling_points': round(points, 2),
            'confidence': round(confidence, 2),
            'breakdown': breakdown
        }
