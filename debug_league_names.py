#!/usr/bin/env python3
"""
Debug script to check league names in the database and test matching logic
"""

from database import get_session
from sqlalchemy.sql import text
from models import leagues_mapping, league_aliases
from main import expand_league_abbreviations
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_league_names():
    """Check what league/competition names are actually stored in the database"""
    db = next(get_session())
    
    try:
        # Get all unique competition names from matches table
        query = text("""
            SELECT DISTINCT competition, match_type, COUNT(*) as match_count
            FROM matches 
            WHERE competition IS NOT NULL 
            GROUP BY competition, match_type
            ORDER BY match_type, match_count DESC
        """)
        
        results = db.execute(query).fetchall()
        
        print("=== LEAGUE NAMES IN DATABASE ===")
        print(f"{'Competition Name':<40} {'Type':<15} {'Matches':<10}")
        print("-" * 70)
        
        league_names = []
        international_names = []
        
        for row in results:
            print(f"{row.competition:<40} {row.match_type:<15} {row.match_count:<10}")
            if row.match_type == 'league':
                league_names.append(row.competition)
            else:
                international_names.append(row.competition)
        
        print(f"\nTotal league competitions: {len(league_names)}")
        print(f"Total international competitions: {len(international_names)}")
        
        return league_names, international_names
        
    except Exception as e:
        logger.error(f"Error checking league names: {str(e)}")
        return [], []
    finally:
        db.close()

def test_league_matching():
    """Test current league matching logic"""
    print("\n=== TESTING CURRENT LEAGUE MAPPING ===")
    
    test_searches = [
        "Major League Cricket",
        "MLC", 
        "Vitality Blast",
        "Vitality Blast Men",
        "IPL",
        "Indian Premier League"
    ]
    
    for search_term in test_searches:
        expanded = expand_league_abbreviations([search_term])
        print(f"Search: '{search_term}' -> Expanded: {expanded}")

def check_specific_player_matches():
    """Check what matches exist for R Ravindra in MLC"""
    db = next(get_session())
    
    try:
        # Check batting_stats for R Ravindra
        query = text("""
            SELECT DISTINCT 
                m.competition,
                m.match_type,
                m.date,
                m.venue,
                bs.runs,
                bs.balls_faced
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = 'R Ravindra'
            AND m.competition ILIKE '%mlc%'
            ORDER BY m.date DESC
        """)
        
        results = db.execute(query).fetchall()
        
        print(f"\n=== R RAVINDRA MATCHES IN MAJOR LEAGUE CRICKET ===")
        if results:
            print(f"{'Date':<12} {'Competition':<25} {'Venue':<20} {'Runs':<5} {'Balls':<5}")
            print("-" * 75)
            for row in results:
                print(f"{row.date:<12} {row.competition:<25} {row.venue:<20} {row.runs:<5} {row.balls_faced:<5}")
        else:
            print("No matches found for R Ravindra in competitions containing 'major'")
            
        # Check all competitions for R Ravindra
        query2 = text("""
            SELECT DISTINCT m.competition, COUNT(*) as matches
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = 'R Ravindra'
            GROUP BY m.competition
            ORDER BY matches DESC
        """)
        
        results2 = db.execute(query2).fetchall()
        print(f"\n=== ALL COMPETITIONS FOR R RAVINDRA ===")
        for row in results2:
            print(f"{row.competition}: {row.matches} matches")
            
    except Exception as e:
        logger.error(f"Error checking player matches: {str(e)}")
    finally:
        db.close()

def test_vitality_blast():
    """Check Vitality Blast name variations"""
    db = next(get_session())
    
    try:
        query = text("""
            SELECT DISTINCT competition, COUNT(*) as matches
            FROM matches 
            WHERE competition ILIKE '%vitality%' OR competition ILIKE '%blast%'
            GROUP BY competition
            ORDER BY matches DESC
        """)
        
        results = db.execute(query).fetchall()
        
        print(f"\n=== VITALITY BLAST VARIATIONS ===")
        for row in results:
            print(f"{row.competition}: {row.matches} matches")
            
    except Exception as e:
        logger.error(f"Error checking Vitality Blast: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("LEAGUE NAME DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # Check what's in the database
    league_names, international_names = check_league_names()
    
    # Test current matching logic
    test_league_matching()
    
    # Check specific player
    check_specific_player_matches()
    
    # Check Vitality Blast variations
    test_vitality_blast()
    
    print("\n=== CURRENT LEAGUES MAPPING ===")
    for full_name, abbrev in leagues_mapping.items():
        print(f"{full_name} -> {abbrev}")
    
    print("\n=== LEAGUE ALIASES ===")
    for alias, standard in league_aliases.items():
        print(f"{alias} -> {standard}")
