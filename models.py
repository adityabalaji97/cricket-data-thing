# models.py
from sqlalchemy import create_engine, Column, Integer, String, Date, JSON, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base

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
    
    # ELO rating columns - store pre-match ratings
    team1_elo = Column(Integer, nullable=True)  # Team1's ELO rating before this match
    team2_elo = Column(Integer, nullable=True)  # Team2's ELO rating before this match

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
    
    # Enhancement columns for left-right analysis
    striker_batter_type = Column(String(10), nullable=True)
    non_striker_batter_type = Column(String(10), nullable=True)
    bowler_type = Column(String(10), nullable=True)
    crease_combo = Column(String(20), nullable=True)
    ball_direction = Column(String(20), nullable=True)

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


class PlayerAlias(Base):
    """Maps player names between deliveries (old) and delivery_details (new) tables."""
    __tablename__ = 'player_aliases'
    
    id = Column(Integer, primary_key=True)
    player_name = Column(String, nullable=False)  # Name in deliveries table (old)
    alias_name = Column(String, nullable=False)   # Name in delivery_details table (new)
    source = Column(String, default='bbb_dataset')


class DeliveryDetails(Base):
    """Enhanced ball-by-ball data with wagon wheel, shot, and line/length info."""
    __tablename__ = 'delivery_details'
    
    id = Column(Integer, primary_key=True)
    match_id = Column(String, ForeignKey('matches.id'), nullable=False)
    innings = Column(Integer, nullable=False)
    over = Column(Integer, nullable=False)
    ball = Column(Integer, nullable=False)
    
    # Player IDs from source data
    p_bat = Column(Integer)  # Batter ID
    p_bowl = Column(Integer)  # Bowler ID
    
    # Player names
    batter = Column(String(100))
    bowler = Column(String(100))
    non_striker = Column(String(100))
    
    # Team info
    batting_team = Column(String(100))
    bowling_team = Column(String(100))
    
    # Player attributes per delivery
    bat_hand = Column(String(10))  # RHB/LHB
    bowl_style = Column(String(20))  # RF, LM, SLO, etc.
    bowl_kind = Column(String(30))  # pace bowler, spin bowler, etc.
    
    # Match context
    date = Column(Date)
    year = Column(Integer)
    ground = Column(String(200))
    country = Column(String(100))
    competition = Column(String(100))
    winner = Column(String(100))
    toss = Column(String(100))
    
    # Ball outcome
    score = Column(Integer)
    outcome = Column(String(50))
    out = Column(Boolean)
    dismissal = Column(String(50))
    noball = Column(Integer)
    wide = Column(Integer)
    byes = Column(Integer)
    legbyes = Column(Integer)
    
    # Batter running totals
    batruns = Column(Integer)
    ballfaced = Column(Integer)
    cur_bat_runs = Column(Integer)
    cur_bat_bf = Column(Integer)
    
    # Bowler running totals
    bowlruns = Column(Integer)
    cur_bowl_ovr = Column(Float)
    cur_bowl_wkts = Column(Integer)
    cur_bowl_runs = Column(Integer)
    
    # Innings state
    inns_runs = Column(Integer)
    inns_wkts = Column(Integer)
    inns_balls = Column(Integer)
    inns_runs_rem = Column(Integer)
    inns_balls_rem = Column(Integer)
    inns_rr = Column(Float)
    inns_rrr = Column(Float)
    target = Column(Integer)
    max_balls = Column(Integer)
    
    # Wagon wheel coordinates
    wagon_x = Column(Integer)
    wagon_y = Column(Integer)
    wagon_zone = Column(Integer)  # 0-8
    
    # Delivery details
    line = Column(String(30))  # ON_THE_STUMPS, OUTSIDE_OFFSTUMP, etc.
    length = Column(String(30))  # GOOD_LENGTH, YORKER, FULL, etc.
    shot = Column(String(30))  # COVER_DRIVE, FLICK, DEFENDED, etc.
    control = Column(Integer)  # 0 or 1
    
    # Predictive metrics
    pred_score = Column(Float)  # Expected score (-1 = no data)
    win_prob = Column(Float)  # Win probability (-1 = no data)
    
    # Left-right batter analysis
    striker_batter_type = Column(String(10))  # RHB/LHB
    non_striker_batter_type = Column(String(10))  # RHB/LHB
    crease_combo = Column(String(20))  # e.g., RHB_LHB, LHB_LHB
