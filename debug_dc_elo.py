#!/usr/bin/env python3
"""
Debug DC's ELO history to see why it's stuck at 1444
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import pandas as pd

API_URL = "http://localhost:8000"  # Adjust if different

async def debug_dc_elo():
    async with aiohttp.ClientSession() as session:
        # First, let's get DC's ELO history
        print("Fetching DC's ELO history...")
        
        # Get ELO history for DC
        async with session.get(f"{API_URL}/teams/elo-history?teams=DC") as response:
            if response.status == 200:
                data = await response.json()
                dc_history = data.get('elo_histories', {}).get('DC', [])
                
                print(f"\nTotal DC history records: {len(dc_history)}")
                
                if dc_history:
                    # Convert to DataFrame for easier analysis
                    df = pd.DataFrame(dc_history)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                    
                    print("\n=== DC ELO History Analysis ===")
                    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
                    print(f"ELO range: {df['elo'].min()} to {df['elo'].max()}")
                    
                    # Find where ELO is 1444
                    elo_1444 = df[df['elo'] == 1444]
                    if not elo_1444.empty:
                        print(f"\n=== Matches where DC had ELO 1444 ===")
                        print(elo_1444[['date', 'elo', 'opponent', 'result', 'match_id']].to_string())
                    
                    # Check for gaps in dates (periods with no matches)
                    print("\n=== Checking for gaps in match history ===")
                    df['days_since_last'] = df['date'].diff().dt.days
                    large_gaps = df[df['days_since_last'] > 180]  # Gaps > 6 months
                    
                    if not large_gaps.empty:
                        print("Large gaps (>180 days) between matches:")
                        for idx, row in large_gaps.iterrows():
                            prev_idx = df.index.get_loc(idx) - 1
                            if prev_idx >= 0:
                                prev_row = df.iloc[prev_idx]
                                print(f"  Gap: {prev_row['date'].date()} (ELO: {prev_row['elo']}) -> {row['date'].date()} (ELO: {row['elo']}) = {row['days_since_last']:.0f} days")
                    
                    # Look at 2019-2020 transition specifically
                    print("\n=== DC matches from 2019 onwards ===")
                    recent_matches = df[df['date'] >= '2019-01-01'].copy()
                    print(f"Total matches from 2019: {len(recent_matches)}")
                    
                    if not recent_matches.empty:
                        print("\nFirst 10 matches from 2019:")
                        print(recent_matches.head(10)[['date', 'elo', 'opponent', 'result', 'match_id']].to_string())
                        
                        print("\nLast 10 matches in dataset:")
                        print(recent_matches.tail(10)[['date', 'elo', 'opponent', 'result', 'match_id']].to_string())
                    
                    # Check if ELO ever changes from 1444 after it first appears
                    if not elo_1444.empty:
                        first_1444_date = elo_1444.iloc[0]['date']
                        after_1444 = df[df['date'] > first_1444_date]
                        unique_elos_after = after_1444['elo'].unique()
                        
                        print(f"\n=== ELO values after first occurrence of 1444 (on {first_1444_date.date()}) ===")
                        print(f"Unique ELO values: {sorted(unique_elos_after)}")
                        
                        if len(unique_elos_after) == 1 and unique_elos_after[0] == 1444:
                            print("WARNING: ELO is stuck at 1444 after this date!")
                            print("This suggests a data issue - DC's matches might not be updating ELO properly")
                        
                    # Group by year to see match counts
                    print("\n=== DC matches by year ===")
                    df['year'] = df['date'].dt.year
                    yearly_stats = df.groupby('year').agg({
                        'elo': ['min', 'max', 'first', 'last'],
                        'match_id': 'count'
                    }).round(0)
                    yearly_stats.columns = ['ELO Min', 'ELO Max', 'ELO Start', 'ELO End', 'Matches']
                    print(yearly_stats.to_string())
                    
                else:
                    print("No history found for DC!")
            else:
                print(f"Error fetching data: {response.status}")
                text = await response.text()
                print(f"Response: {text}")

        # Also check what the ELO rankings endpoint returns for DC
        print("\n\n=== Checking DC in ELO rankings ===")
        
        # Check with different date ranges
        test_dates = [
            ("2019-01-01", "2019-12-31", "2019"),
            ("2020-01-01", "2020-12-31", "2020"),
            ("2021-01-01", "2021-12-31", "2021"),
        ]
        
        for start, end, label in test_dates:
            params = {
                'league': 'Indian Premier League',
                'start_date': start,
                'end_date': end,
                'include_international': 'false'
            }
            
            async with session.get(f"{API_URL}/teams/elo-rankings", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    rankings = data.get('rankings', [])
                    
                    # Find DC in rankings
                    dc_ranking = next((team for team in rankings if team['team_abbreviation'] == 'DC'), None)
                    
                    if dc_ranking:
                        print(f"{label}: DC ELO = {dc_ranking.get('current_elo', 'N/A')}, Matches = {dc_ranking.get('matches_played', 'N/A')}")
                    else:
                        print(f"{label}: DC not found in rankings")

if __name__ == "__main__":
    asyncio.run(debug_dc_elo())
