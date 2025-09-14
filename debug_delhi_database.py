#!/usr/bin/env python3
"""
Debug what's actually in the database for Delhi teams
"""

import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/cricket_stats')

def check_delhi_in_database():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("=== Checking Delhi teams directly in database ===\n")
        
        # Check what team names exist for Delhi
        print("1. Delhi team names in matches table:")
        cur.execute("""
            SELECT DISTINCT team_name, COUNT(*) as matches
            FROM (
                SELECT team1 as team_name FROM matches WHERE team1 LIKE '%Delhi%'
                UNION ALL
                SELECT team2 as team_name FROM matches WHERE team2 LIKE '%Delhi%'
            ) t
            GROUP BY team_name
            ORDER BY team_name;
        """)
        
        delhi_teams = cur.fetchall()
        print(f"Found {len(delhi_teams)} Delhi team name variations:")
        for team_name, count in delhi_teams:
            print(f"  - '{team_name}': {count} matches")
        
        # Check ELO data availability by team name and year
        print("\n2. ELO data by team name and year:")
        for team_name, _ in delhi_teams:
            cur.execute("""
                SELECT 
                    EXTRACT(YEAR FROM date) as year,
                    COUNT(*) as matches,
                    MIN(date) as first_match,
                    MAX(date) as last_match,
                    AVG(CASE WHEN team1 = %s THEN team1_elo WHEN team2 = %s THEN team2_elo END) as avg_elo
                FROM matches 
                WHERE (team1 = %s OR team2 = %s)
                AND (team1_elo IS NOT NULL OR team2_elo IS NOT NULL)
                GROUP BY EXTRACT(YEAR FROM date)
                ORDER BY year;
            """, (team_name, team_name, team_name, team_name))
            
            yearly_data = cur.fetchall()
            print(f"\n  {team_name}:")
            if yearly_data:
                for year, matches, first, last, avg_elo in yearly_data:
                    print(f"    {int(year)}: {matches} matches, {first} to {last}, avg ELO: {avg_elo:.0f}")
            else:
                print("    No ELO data found")
        
        # Check for the problematic 1444 ELO specifically
        print("\n3. Records with ELO 1444:")
        cur.execute("""
            SELECT date, team1, team2, team1_elo, team2_elo, winner
            FROM matches 
            WHERE (team1 LIKE '%Delhi%' OR team2 LIKE '%Delhi%')
            AND (team1_elo = 1444 OR team2_elo = 1444)
            ORDER BY date;
        """)
        
        elo_1444_records = cur.fetchall()
        print(f"Found {len(elo_1444_records)} matches with ELO 1444:")
        for date, team1, team2, elo1, elo2, winner in elo_1444_records:
            delhi_team = team1 if 'Delhi' in team1 else team2
            delhi_elo = elo1 if 'Delhi' in team1 else elo2
            print(f"  {date}: {delhi_team} (ELO: {delhi_elo}) vs opponent")
        
        # Check the transition period specifically (2018-2019)
        print("\n4. Transition period analysis (2018-2020):")
        cur.execute("""
            SELECT date, team1, team2, team1_elo, team2_elo, winner
            FROM matches 
            WHERE (team1 LIKE '%Delhi%' OR team2 LIKE '%Delhi%')
            AND date BETWEEN '2018-01-01' AND '2020-12-31'
            AND (team1_elo IS NOT NULL AND team2_elo IS NOT NULL)
            ORDER BY date;
        """)
        
        transition_records = cur.fetchall()
        print(f"Found {len(transition_records)} matches in transition period:")
        for date, team1, team2, elo1, elo2, winner in transition_records[:10]:  # Show first 10
            delhi_team = team1 if 'Delhi' in team1 else team2
            delhi_elo = elo1 if 'Delhi' in team1 else elo2
            print(f"  {date}: {delhi_team} (ELO: {delhi_elo})")
        
        if len(transition_records) > 10:
            print(f"  ... and {len(transition_records) - 10} more")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    check_delhi_in_database()
