#!/usr/bin/env python3
"""
Check match_type and competition values in the database for IPL matches
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/cricket_stats')

def check_ipl_matches():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("=== Checking IPL match data ===\n")
        
        # Check match_type and competition values for IPL matches
        print("1. Checking match_type and competition values for 2020-2021...")
        cur.execute("""
            SELECT 
                EXTRACT(YEAR FROM date) as year,
                match_type,
                competition,
                COUNT(*) as match_count
            FROM matches
            WHERE date >= '2020-01-01' AND date <= '2021-12-31'
                AND (
                    competition LIKE '%Premier League%' 
                    OR event_name LIKE '%Premier League%'
                    OR team1 IN ('Mumbai Indians', 'MI', 'Chennai Super Kings', 'CSK', 'Delhi Capitals', 'DC')
                    OR team2 IN ('Mumbai Indians', 'MI', 'Chennai Super Kings', 'CSK', 'Delhi Capitals', 'DC')
                )
            GROUP BY EXTRACT(YEAR FROM date), match_type, competition
            ORDER BY year, match_count DESC;
        """)
        
        results = cur.fetchall()
        print(f"{'Year':<6} {'Match Type':<15} {'Competition':<30} {'Count':<10}")
        print("-" * 65)
        for row in results:
            year, match_type, competition, count = row
            print(f"{int(year) if year else 'NULL':<6} {match_type or 'NULL':<15} {(competition or 'NULL')[:28]:<30} {count:<10}")
        
        # Check what values exist for league matches
        print("\n2. Checking all league-type competitions...")
        cur.execute("""
            SELECT DISTINCT 
                match_type,
                competition
            FROM matches
            WHERE match_type = 'league'
                OR competition LIKE '%League%'
            ORDER BY match_type, competition;
        """)
        
        results = cur.fetchall()
        print(f"\n{'Match Type':<15} {'Competition':<40}")
        print("-" * 55)
        for match_type, competition in results:
            print(f"{match_type or 'NULL':<15} {competition or 'NULL':<40}")
        
        # Check specific DC matches in 2020
        print("\n3. Checking DC matches in Nov 2020...")
        cur.execute("""
            SELECT 
                id,
                date,
                team1,
                team2,
                match_type,
                competition,
                event_name,
                team1_elo,
                team2_elo
            FROM matches
            WHERE date >= '2020-11-01' AND date <= '2020-11-15'
                AND (team1 IN ('Delhi Capitals', 'DC') OR team2 IN ('Delhi Capitals', 'DC'))
            ORDER BY date;
        """)
        
        results = cur.fetchall()
        print(f"\n{'ID':<10} {'Date':<12} {'Team1':<20} {'Team2':<20} {'Type':<10} {'Competition':<25}")
        print("-" * 100)
        for row in results:
            match_id, date, team1, team2, match_type, competition, event_name, t1_elo, t2_elo = row
            print(f"{match_id:<10} {date.strftime('%Y-%m-%d'):<12} {team1:<20} {team2:<20} {match_type or 'NULL':<10} {(competition or 'NULL')[:23]:<25}")
            print(f"{'':>10} Event: {event_name or 'NULL'}, T1 ELO: {t1_elo or 'NULL'}, T2 ELO: {t2_elo or 'NULL'}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_ipl_matches()
