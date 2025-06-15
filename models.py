# models.py
from sqlalchemy import create_engine, Column, Integer, String, Date, JSON, ForeignKey, Float, Boolean, DECIMAL, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

def get_match_result(match_dict: dict, team: str) -> str:
    """Get match result from perspective of given team"""
    if not match_dict.get('winner'):
        return 'NR'
    return 'W' if match_dict['winner'] == team else 'L'

def format_score(runs: int, wickets: int) -> str:
    """Format cricket score"""
    if runs is None:
        return ''
    if wickets is None:
        return str(runs)
    return f"{runs}/{wickets}"

# Add the teams mapping at the top level
teams_mapping = {
    'Chennai Super Kings': 'CSK',
    'Mumbai Indians': 'MI', 
    'Kolkata Knight Riders': 'KKR',
    'Gujarat Titans': 'GT',
    'Lucknow Super Giants': 'LSG',
    'Punjab Kings': 'PBKS',
    'Kings XI Punjab': 'PBKS',
    'Royal Challengers Bangalore': 'RCB',
    'Royal Challengers Bengaluru': 'RCB',
    'Delhi Capitals': 'DC',
    'Delhi Daredevils': 'DC',
    'Sunrisers Hyderabad': 'SRH',
    'Rajasthan Royals': 'RR',
    'Rising Pune Supergiants': 'RPSG',
    'Rising Pune Supergiant': 'RPSG',
    'Gujarat Lions': 'GL',
    'Deccan Chargers': 'DCh',
    'Kochi Tuskers Kerala': 'KTK'
}

leagues_mapping = {
    "Indian Premier League": "IPL",
    "Big Bash League": "BBL", 
    "Pakistan Super League": "PSL",
    "Caribbean Premier League": "CPL",
    "SA20": "SA20",
    "International League T20": "ILT20",
    "Bangladesh Premier League": "BPL",
    "Lanka Premier League": "LPL"
}

# Additional mapping for leagues with name changes over time
league_aliases = {
    "HRV Cup": "Super Smash",
    "HRV Twenty20": "Super Smash",
    "NatWest T20 Blast": "Vitality Blast"
}

INTERNATIONAL_TEAMS_RANKED = [
    'India', 'Australia', 'England', 'West Indies', 'New Zealand',
    'South Africa', 'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan',
    'Ireland', 'Zimbabwe', 'Scotland', 'Netherlands', 'Namibia',
    'UAE', 'Nepal', 'USA', 'Oman', 'Papua New Guinea'
]

def get_league_abbreviation(league_name: str) -> str:
    return leagues_mapping.get(league_name, league_name)

def get_full_league_name(abbrev: str) -> str:
    """Get the full league name for an abbreviation"""
    reverse_mapping = {v: k for k, v in leagues_mapping.items()}
    return reverse_mapping.get(abbrev, abbrev)

def get_team_abbreviation(team_name: str) -> str:
    return teams_mapping.get(team_name, team_name)

class Match(Base):
    __tablename__ = 'matches'
    id = Column(String, primary_key=True)
    date = Column(Date, nullable=False)  # This should be required
    venue = Column(String, nullable=True)  # Make nullable
    city = Column(String, nullable=True)  # Make nullable
    event_name = Column(String, nullable=True)
    event_match_number = Column(Integer, nullable=True)
    team1 = Column(String, nullable=False)  # Teams should be required
    team2 = Column(String, nullable=False)
    toss_winner = Column(String, nullable=True)
    toss_decision = Column(String, nullable=True)
    winner = Column(String, nullable=True)
    outcome = Column(JSON, nullable=True)
    player_of_match = Column(String, nullable=True)
    overs = Column(Integer, nullable=True)
    balls_per_over = Column(Integer, nullable=True)
    win_toss_win_match = Column(Boolean, nullable=True)
    bat_first = Column(String, nullable=True)
    bowl_first = Column(String, nullable=True)
    won_batting_first = Column(Boolean, nullable=True)
    won_fielding_first = Column(Boolean, nullable=True)
    match_type = Column(String, nullable=False)  # 'league' or 'international'
    competition = Column(String, nullable=False)  # e.g. 'IPL', 'T20I', 'BBL', etc.

    def to_dict(self) -> dict:
        """Convert match to dictionary with formatted scores"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'venue': self.venue,
            'team1': teams_mapping.get(self.team1, self.team1),
            'team2': teams_mapping.get(self.team2, self.team2),
            'winner': teams_mapping.get(self.winner, self.winner) if self.winner else None,
            'toss_winner': teams_mapping.get(self.toss_winner, self.toss_winner) if self.toss_winner else None,
            'toss_decision': self.toss_decision
        }

class Delivery(Base):
    __tablename__ = 'deliveries'
    id = Column(Integer, primary_key=True)
    match_id = Column(String, ForeignKey('matches.id'))
    innings = Column(Integer)
    over = Column(Integer)
    ball = Column(Integer)
    batter = Column(String)
    non_striker = Column(String)
    bowler = Column(String)
    runs_off_bat = Column(Integer)
    extras = Column(Integer)
    wides = Column(Integer)
    noballs = Column(Integer)
    byes = Column(Integer)
    legbyes = Column(Integer)
    penalty = Column(Integer)
    wicket_type = Column(String)
    player_dismissed = Column(String)
    fielder = Column(String)
    batting_team = Column(String)
    bowling_team = Column(String)
    
    # WPA (Win Probability Added) columns for per-delivery impact analysis
    wpa_batter = Column(DECIMAL(6,3), nullable=True)  # WPA for batter (-2.0 to +2.0)
    wpa_bowler = Column(DECIMAL(6,3), nullable=True)  # WPA for bowler (inverse of batter)
    wpa_computed_date = Column(TIMESTAMP, nullable=True)  # When WPA was calculated
    
    # Phase 1: Left-Right Analysis Columns
    striker_batter_type = Column(String(10), nullable=True)  # LHB/RHB for striker
    non_striker_batter_type = Column(String(10), nullable=True)  # LHB/RHB for non-striker  
    bowler_type = Column(String(10), nullable=True)  # LO/LM/RL/RM/RO/etc for bowler
    
    # Phase 2: Derived Analysis Columns
    crease_combo = Column(String(20), nullable=True)  # rhb_rhb/lhb_lhb/lhb_rhb/unknown
    ball_direction = Column(String(20), nullable=True)  # intoBatter/awayFromBatter/unknown
    
    def to_dict(self):
        """Convert delivery to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'match_id': self.match_id,
            'innings': self.innings,
            'over': self.over,
            'ball': self.ball,
            'batter': self.batter,
            'bowler': self.bowler,
            'runs_off_bat': self.runs_off_bat,
            'extras': self.extras,
            'wicket_type': self.wicket_type,
            'player_dismissed': self.player_dismissed,
            'batting_team': self.batting_team,
            'bowling_team': self.bowling_team,
            'wpa_batter': float(self.wpa_batter) if self.wpa_batter else None,
            'wpa_bowler': float(self.wpa_bowler) if self.wpa_bowler else None,
            'wpa_computed_date': self.wpa_computed_date.isoformat() if self.wpa_computed_date else None,
            'striker_batter_type': self.striker_batter_type,
            'non_striker_batter_type': self.non_striker_batter_type,
            'bowler_type': self.bowler_type,
            'crease_combo': self.crease_combo,
            'ball_direction': self.ball_direction
        }
    
    def has_wpa_calculated(self) -> bool:
        """Check if WPA has been calculated for this delivery"""
        return self.wpa_batter is not None and self.wpa_bowler is not None

class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    batting_hand = Column(String)  # LHB/RHB
    bowling_type = Column(String)  # RF/RM/RO etc.
    nationality = Column(String)
    batter_type = Column(String)
    bowler_type = Column(String)
    bowl_hand = Column(String)
    bowl_type = Column(String)
    league_teams = Column(String)

class BattingStats(Base):
    __tablename__ = 'batting_stats'
    id = Column(Integer, primary_key=True)
    match_id = Column(String, ForeignKey('matches.id'))
    innings = Column(Integer)
    striker = Column(String)
    batting_team = Column(String)
    
    # Basic stats
    runs = Column(Integer)
    balls_faced = Column(Integer)
    wickets = Column(Integer)
    fours = Column(Integer)
    sixes = Column(Integer)
    dots = Column(Integer)
    ones = Column(Integer)
    twos = Column(Integer)
    threes = Column(Integer)
    strike_rate = Column(Float)
    
    # Fantasy points
    fantasy_points = Column(Float)
    batting_points = Column(Float)
    bowling_points = Column(Float)
    fielding_points = Column(Float)
    
    # Phase-wise stats
    pp_runs = Column(Integer)
    pp_balls = Column(Integer)
    pp_wickets = Column(Integer)
    pp_dots = Column(Integer)
    pp_boundaries = Column(Integer)
    pp_strike_rate = Column(Float)
    
    middle_runs = Column(Integer)
    middle_balls = Column(Integer)
    middle_wickets = Column(Integer)
    middle_dots = Column(Integer)
    middle_boundaries = Column(Integer)
    middle_strike_rate = Column(Float)
    
    death_runs = Column(Integer)
    death_balls = Column(Integer)
    death_wickets = Column(Integer)
    death_dots = Column(Integer)
    death_boundaries = Column(Integer)
    death_strike_rate = Column(Float)
    
    # Team comparison stats
    team_runs_excl_batter = Column(Integer)
    team_balls_excl_batter = Column(Integer)
    team_sr_excl_batter = Column(Float)
    sr_diff = Column(Float)
    
    # Batting position and entry stats
    batting_position = Column(Integer)
    entry_runs = Column(Integer)
    entry_balls = Column(Integer)
    entry_overs = Column(Float)

class BowlingStats(Base):
    __tablename__ = 'bowling_stats'
    id = Column(Integer, primary_key=True)
    match_id = Column(String, ForeignKey('matches.id'))
    innings = Column(Integer)
    bowler = Column(String)
    bowling_team = Column(String)
    
    # Basic stats
    overs = Column(Float)
    runs_conceded = Column(Integer)
    wickets = Column(Integer)
    dots = Column(Integer)
    fours_conceded = Column(Integer)
    sixes_conceded = Column(Integer)
    extras = Column(Integer)
    economy = Column(Float)
    
    # Fantasy points
    fantasy_points = Column(Float)
    batting_points = Column(Float)
    bowling_points = Column(Float)
    fielding_points = Column(Float)
    
    # Phase-wise stats
    pp_overs = Column(Float)
    pp_runs = Column(Integer)
    pp_wickets = Column(Integer)
    pp_dots = Column(Integer)
    pp_economy = Column(Float)
    pp_boundaries = Column(Integer)
    
    middle_overs = Column(Float)
    middle_runs = Column(Integer)
    middle_wickets = Column(Integer)
    middle_dots = Column(Integer)
    middle_economy = Column(Float)
    middle_boundaries = Column(Integer)
    
    death_overs = Column(Float)
    death_runs = Column(Integer)
    death_wickets = Column(Integer)
    death_dots = Column(Integer)
    death_economy = Column(Float)
    death_boundaries = Column(Integer)
    
    # Team comparison stats
    team_runs_excl_bowler = Column(Integer)
    team_overs_excl_bowler = Column(Float)
    team_economy_excl_bowler = Column(Float)
    economy_diff = Column(Float)