#!/usr/bin/env python3
"""
Debug script to find the EXACT competition name for R Ravindra's MLC matches
"""

from database import get_session
from sqlalchemy.sql import text
import logging

def find_r_ravindra_exact_competitions():
    """Find the exact competition names for R Ravindra"""
    db = next(get_session())
    
    try:
        # Get ALL distinct competitions for R Ravindra
        query = text("""
            SELECT DISTINCT m.competition, COUNT(*) as matches
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = 'R Ravindra'
            GROUP BY m.competition
            ORDER BY matches DESC
        """)
        
        results = db.execute(query).fetchall()
        
        print("=== ALL COMPETITIONS FOR R RAVINDRA (EXACT NAMES) ===")
        if results:
            print(f"{'Competition':<40} {'Matches':<10}")
            print("-" * 55)
            for row in results:
                print(f"{row.competition:<40} {row.matches:<10}")
        else:
            print("No matches found for R Ravindra")
            
        # Now search for anything that might be MLC
        print("\n=== SEARCHING FOR MLC-LIKE COMPETITIONS ===")
        mlc_query = text("""
            SELECT DISTINCT m.competition, COUNT(*) as matches
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE bs.striker = 'R Ravindra'
            AND (m.competition ILIKE '%league%cricket%' 
                 OR m.competition ILIKE '%mlc%'
                 OR m.competition ILIKE '%major%'
                 OR m.competition ILIKE '%cricket%league%')
            GROUP BY m.competition
            ORDER BY matches DESC
        """)
        
        mlc_results = db.execute(mlc_query).fetchall()
        
        if mlc_results:
            for row in mlc_results:
                print(f"Found: {row.competition} ({row.matches} matches)")
        else:
            print("No MLC-like competitions found")
            
        return results
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return []
    finally:
        db.close()

def check_all_competitions_with_cricket_league():
    """Check all competitions that might be Major League Cricket"""
    db = next(get_session())
    
    try:
        query = text("""
            SELECT DISTINCT competition, COUNT(*) as matches
            FROM matches 
            WHERE competition ILIKE '%cricket%'
            AND competition ILIKE '%league%'
            GROUP BY competition
            ORDER BY matches DESC
        """)
        
        results = db.execute(query).fetchall()
        
        print("\n=== ALL COMPETITIONS WITH 'CRICKET' AND 'LEAGUE' ===")
        if results:
            for row in results:
                print(f"{row.competition}: {row.matches} matches")
        else:
            print("No cricket league competitions found")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("FINDING EXACT COMPETITION NAMES FOR R RAVINDRA")
    print("=" * 60)
    
    # Find exact competition names
    competitions = find_r_ravindra_exact_competitions()
    
    # Check all cricket league competitions
    check_all_competitions_with_cricket_league()
