#!/usr/bin/env python3
"""
Check what teams are returned by the rankings endpoint for different date ranges
"""

import requests
import json

API_URL = "https://cricket-data-thing-672dfbacf476.herokuapp.com"  # Adjust if needed

def test_rankings():
    print("=== Testing Rankings Endpoint for Different Date Ranges ===\n")
    
    test_ranges = [
        ("2020-01-01", "2021-12-31", "2020-2021"),
        ("2008-01-01", "2025-12-31", "2008-2025"),
    ]
    
    for start_date, end_date, label in test_ranges:
        print(f"\nRange: {label} ({start_date} to {end_date})")
        print("-" * 60)
        
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
            
            print(f"Total teams returned: {len(rankings)}")
            print("\nTeams and their abbreviations:")
            
            # Sort by ELO for consistent ordering
            rankings.sort(key=lambda x: x.get('current_elo', 0), reverse=True)
            
            for i, team in enumerate(rankings, 1):
                team_name = team.get('team_name', 'Unknown')
                team_abbr = team.get('team_abbreviation', 'N/A')
                elo = team.get('current_elo', 0)
                print(f"  {i:2}. {team_abbr:6} - {team_name:30} (ELO: {elo})")
            
            # Check for Delhi teams specifically
            delhi_teams = [t for t in rankings if 'Delhi' in t.get('team_name', '') or 
                          'DC' in t.get('team_abbreviation', '') or 
                          'DD' in t.get('team_abbreviation', '')]
            
            if delhi_teams:
                print(f"\nDelhi-related teams found: {len(delhi_teams)}")
                for team in delhi_teams:
                    print(f"  - {team.get('team_abbreviation')}: {team.get('team_name')} (ELO: {team.get('current_elo')})")
            else:
                print("\n⚠️  NO DELHI TEAMS FOUND IN RANKINGS!")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    test_rankings()
