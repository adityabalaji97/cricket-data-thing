#!/usr/bin/env python3
"""
Check DC's ELO data directly in the database
"""

import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/cricket_stats')

def check_dc_database():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("=== Checking DC's ELO data in database ===\n")
        
        # Check if DC exists in matches table with their various names
        print("1. Checking DC team names in matches...")
        cur.execute("""
            SELECT DISTINCT team1 as team_name
            FROM matches 
            WHERE team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD')
            UNION
            SELECT DISTINCT team2 as team_name
            FROM matches 
            WHERE team2 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD')
            ORDER BY team_name;
        """)
        team_names = cur.fetchall()
        print("DC team name variations found:", [t[0] for t in team_names])
        
        # Check ELO values for DC matches from 2019 onwards
        print("\n2. Checking DC matches with ELO values from 2019...")
        cur.execute("""
            SELECT 
                id,
                start_date,
                CASE 
                    WHEN team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') THEN team1
                    ELSE team2
                END as dc_name,
                CASE 
                    WHEN team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') THEN team1_elo_before
                    ELSE team2_elo_before
                END as elo_before,
                CASE 
                    WHEN team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') THEN team1_elo_after
                    ELSE team2_elo_after
                END as elo_after,
                CASE 
                    WHEN team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') THEN 
                        CASE WHEN winner = team1 THEN 'W' ELSE 'L' END
                    ELSE 
                        CASE WHEN winner = team2 THEN 'W' ELSE 'L' END
                END as result
            FROM matches
            WHERE 
                (team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') OR 
                 team2 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD'))
                AND start_date >= '2019-01-01'
                AND league = 'Indian Premier League'
            ORDER BY start_date
            LIMIT 20;
        """)
        
        results = cur.fetchall()
        print(f"Found {len(results)} DC matches from 2019 onwards (showing first 20):\n")
        print(f"{'Match ID':<10} {'Date':<12} {'Team Name':<20} {'ELO Before':<12} {'ELO After':<12} {'Result':<8}")
        print("-" * 85)
        
        for row in results:
            id, date, team_name, elo_before, elo_after, result = row
            print(f"{id:<10} {date.strftime('%Y-%m-%d'):<12} {team_name:<20} {elo_before:<12.0f} {elo_after:<12.0f} {result:<8}")
        
        # Check for stuck ELO values
        print("\n3. Checking for consecutive matches with same ELO (potential stuck values)...")
        cur.execute("""
            WITH dc_matches AS (
                SELECT 
                    id,
                    start_date,
                    CASE 
                        WHEN team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') THEN team1_elo_after
                        ELSE team2_elo_after
                    END as elo_after
                FROM matches
                WHERE 
                    (team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') OR 
                     team2 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD'))
                    AND start_date >= '2019-01-01'
                    AND league = 'Indian Premier League'
                ORDER BY start_date
            ),
            elo_runs AS (
                SELECT 
                    elo_after,
                    COUNT(*) as consecutive_count,
                    MIN(start_date) as first_date,
                    MAX(start_date) as last_date
                FROM (
                    SELECT 
                        *,
                        ROW_NUMBER() OVER (ORDER BY start_date) - 
                        ROW_NUMBER() OVER (PARTITION BY elo_after ORDER BY start_date) as grp
                    FROM dc_matches
                ) t
                GROUP BY elo_after, grp
                HAVING COUNT(*) > 3
            )
            SELECT * FROM elo_runs ORDER BY first_date;
        """)
        
        stuck_periods = cur.fetchall()
        if stuck_periods:
            print("\nFound periods where ELO stayed the same for multiple matches:")
            print(f"{'ELO Value':<12} {'Count':<8} {'First Date':<12} {'Last Date':<12}")
            print("-" * 50)
            for elo, count, first_date, last_date in stuck_periods:
                print(f"{elo:<12.0f} {count:<8} {first_date.strftime('%Y-%m-%d'):<12} {last_date.strftime('%Y-%m-%d'):<12}")
        else:
            print("No long periods of stuck ELO values found")
        
        # Check if there's a pattern around 1444
        print("\n4. Checking matches around ELO 1444...")
        cur.execute("""
            SELECT 
                id,
                start_date,
                CASE 
                    WHEN team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') THEN team1_elo_before
                    ELSE team2_elo_before
                END as elo_before,
                CASE 
                    WHEN team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') THEN team1_elo_after
                    ELSE team2_elo_after  
                END as elo_after
            FROM matches
            WHERE 
                (team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') OR 
                 team2 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD'))
                AND league = 'Indian Premier League'
                AND (
                    (team1 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') AND 
                     (team1_elo_before = 1444 OR team1_elo_after = 1444))
                    OR
                    (team2 IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD') AND 
                     (team2_elo_before = 1444 OR team2_elo_after = 1444))
                )
            ORDER BY start_date;
        """)
        
        matches_1444 = cur.fetchall()
        if matches_1444:
            print(f"\nFound {len(matches_1444)} matches where DC had ELO of 1444:")
            print(f"{'Match ID':<10} {'Date':<12} {'ELO Before':<12} {'ELO After':<12}")
            print("-" * 50)
            for id, date, elo_before, elo_after in matches_1444:
                print(f"{id:<10} {date.strftime('%Y-%m-%d'):<12} {elo_before:<12.0f} {elo_after:<12.0f}")
        
        # Check precomputed ELO data if it exists
        print("\n5. Checking precomputed ELO data for DC...")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'precomputed_elo_ratings';
        """)
        
        if cur.fetchone():
            cur.execute("""
                SELECT 
                    team,
                    date,
                    elo_rating,
                    matches_played
                FROM precomputed_elo_ratings
                WHERE team IN ('Delhi Capitals', 'DC', 'Delhi Daredevils', 'DD')
                    AND date >= '2019-01-01'
                ORDER BY date
                LIMIT 20;
            """)
            
            precomputed = cur.fetchall()
            if precomputed:
                print(f"\nFound {len(precomputed)} precomputed DC ELO entries (showing first 20):")
                print(f"{'Team':<20} {'Date':<12} {'ELO':<10} {'Matches':<10}")
                print("-" * 55)
                for team, date, elo, matches in precomputed:
                    print(f"{team:<20} {date.strftime('%Y-%m-%d'):<12} {elo:<10.0f} {matches:<10}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_dc_database()
