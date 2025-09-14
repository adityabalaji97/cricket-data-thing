#!/usr/bin/env python3
"""
Test the API endpoints directly to see what's happening with DC's data
"""

import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"  # Adjust if needed

def test_dc_api():
    print("=== Testing DC ELO API Responses ===\n")
    
    # Test 1: Get DC's complete ELO history
    print("1. Fetching DC's complete ELO history...")
    response = requests.get(f"{API_URL}/teams/elo-history", params={"teams": "DC"})
    
    if response.status_code == 200:
        data = response.json()
        dc_history = data.get('elo_histories', {}).get('DC', [])
        
        print(f"   Total records: {len(dc_history)}")
        
        if dc_history:
            # Sort by date
            dc_history.sort(key=lambda x: x['date'])
            
            # Find 1444 values
            elo_1444_matches = [m for m in dc_history if m['elo'] == 1444]
            print(f"   Matches with ELO 1444: {len(elo_1444_matches)}")
            
            if elo_1444_matches:
                print(f"   First 1444: {elo_1444_matches[0]['date']}")
                print(f"   Last 1444: {elo_1444_matches[-1]['date']}")
            
            # Check 2019-2020 period
            matches_2019_2020 = [m for m in dc_history if '2019' <= m['date'] <= '2020-12-31']
            print(f"\n   Matches from 2019-2020: {len(matches_2019_2020)}")
            
            if matches_2019_2020:
                print("\n   First 5 matches in 2019-2020:")
                for m in matches_2019_2020[:5]:
                    print(f"      {m['date']}: ELO={m['elo']}, vs {m.get('opponent', 'N/A')}, Result={m.get('result', 'N/A')}")
                
                print("\n   Last 5 matches in 2019-2020:")
                for m in matches_2019_2020[-5:]:
                    print(f"      {m['date']}: ELO={m['elo']}, vs {m.get('opponent', 'N/A')}, Result={m.get('result', 'N/A')}")
            
            # Check for the specific date around Nov 2020
            print("\n   Checking around November 2020...")
            nov_2020_matches = [m for m in dc_history if '2020-10-01' <= m['date'] <= '2020-11-30']
            for m in nov_2020_matches:
                print(f"      {m['date']}: ELO={m['elo']}, vs {m.get('opponent', 'N/A')}, Result={m.get('result', 'N/A')}")
    else:
        print(f"   Error: {response.status_code}")
    
    # Test 2: Check with date-filtered queries (like the frontend does)
    print("\n2. Testing date-filtered queries...")
    
    test_ranges = [
        ("2020-01-01", "2021-12-31", "2020-2021"),
        ("2008-01-01", "2025-12-31", "2008-2025"),
        ("2019-01-01", "2020-12-31", "2019-2020"),
    ]
    
    for start_date, end_date, label in test_ranges:
        print(f"\n   Range: {label}")
        
        # First get teams
        params = {
            'league': 'Indian Premier League',
            'start_date': start_date,
            'end_date': end_date,
            'include_international': 'false'
        }
        
        response = requests.get(f"{API_URL}/teams/elo-rankings", params=params)
        if response.status_code == 200:
            data = response.json()
            rankings = data.get('rankings', [])
            
            # Find DC
            dc_ranking = next((t for t in rankings if t['team_abbreviation'] == 'DC'), None)
            if dc_ranking:
                print(f"      DC in rankings: ELO={dc_ranking.get('current_elo')}, Matches={dc_ranking.get('matches_played')}")
            else:
                print(f"      DC not found in rankings!")
                # Check if it's under a different name
                delhi_teams = [t for t in rankings if 'Delhi' in t.get('team_name', '') or 'DC' in t.get('team_abbreviation', '')]
                if delhi_teams:
                    print(f"      Found Delhi teams: {delhi_teams}")
        
        # Now get history with date filter (old way - problematic)
        params = {
            'teams': 'DC',
            'start_date': start_date,
            'end_date': end_date
        }
        
        response = requests.get(f"{API_URL}/teams/elo-history", params=params)
        if response.status_code == 200:
            data = response.json()
            dc_history = data.get('elo_histories', {}).get('DC', [])
            
            if dc_history:
                dc_history.sort(key=lambda x: x['date'])
                print(f"      History records: {len(dc_history)}")
                
                # Find what would be shown on Nov 10, 2020
                matches_before_nov10 = [m for m in dc_history if m['date'] <= '2020-11-10']
                if matches_before_nov10:
                    last_match = matches_before_nov10[-1]
                    print(f"      Last match before Nov 10, 2020: {last_match['date']}, ELO={last_match['elo']}")
            else:
                print(f"      No history returned for DC")
    
    # Test 3: Check team name variations
    print("\n3. Checking team name variations...")
    for team_name in ['DC', 'Delhi Capitals', 'DD', 'Delhi Daredevils']:
        response = requests.get(f"{API_URL}/teams/elo-history", params={"teams": team_name})
        if response.status_code == 200:
            data = response.json()
            history = data.get('elo_histories', {}).get(team_name, [])
            print(f"   '{team_name}': {len(history)} records")

if __name__ == "__main__":
    test_dc_api()
