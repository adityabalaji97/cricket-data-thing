#!/usr/bin/env python3
"""
Debug the Delhi Daredevils → Delhi Capitals transition issue in ELO racer chart
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_URL = "http://localhost:8000"  # Adjust if different

async def debug_delhi_transition():
    async with aiohttp.ClientSession() as session:
        print("=== Debugging Delhi Daredevils → Delhi Capitals Transition ===\n")
        
        # Test 1: Check what the rankings API returns for Delhi
        print("1. Checking ELO rankings API for Delhi...")
        params = {
            'league': 'Indian Premier League',
            'include_international': 'false',
            'start_date': '2008-01-01',
            'end_date': '2025-09-14'
        }
        
        async with session.get(f"{API_URL}/teams/elo-rankings", params=params) as response:
            if response.status == 200:
                data = await response.json()
                delhi_teams = [team for team in data['rankings'] if 'Delhi' in team['team_name']]
                print(f"Delhi teams found in rankings: {len(delhi_teams)}")
                for team in delhi_teams:
                    print(f"  - {team['team_name']} (abbrev: {team['team_abbreviation']}) - ELO: {team['current_elo']}")
            else:
                print(f"Error: {response.status}")
        
        # Test 2: Test ELO history for "Delhi Capitals" specifically
        print("\n2. Testing ELO history for 'Delhi Capitals'...")
        history_params = {'teams': 'Delhi Capitals'}
        
        async with session.get(f"{API_URL}/teams/elo-history", params=history_params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Teams requested: {data['teams_requested']}")
                print(f"Teams found: {data['teams_found']}")
                
                for team_name, history in data['elo_histories'].items():
                    print(f"\n{team_name}: {len(history)} records")
                    if history:
                        print(f"  First record: {history[0]['date']} - ELO: {history[0]['elo']}")
                        print(f"  Last record: {history[-1]['date']} - ELO: {history[-1]['elo']}")
                        
                        # Check for the problematic 1444 ELO
                        elo_1444_records = [r for r in history if r['elo'] == 1444]
                        if elo_1444_records:
                            print(f"  Records with ELO 1444: {len(elo_1444_records)}")
                            print(f"  First 1444: {elo_1444_records[0]['date']}")
                            print(f"  Last 1444: {elo_1444_records[-1]['date']}")
                        
                        # Check records around 2019 (transition year)
                        records_2019 = [r for r in history if r['date'].startswith('2019')]
                        if records_2019:
                            print(f"  2019 records: {len(records_2019)}")
                            print(f"  First 2019: {records_2019[0]['date']} - ELO: {records_2019[0]['elo']}")
                            print(f"  Last 2019: {records_2019[-1]['date']} - ELO: {records_2019[-1]['elo']}")
            else:
                print(f"Error: {response.status}")
        
        # Test 3: Test ELO history for "Delhi Daredevils" specifically
        print("\n3. Testing ELO history for 'Delhi Daredevils'...")
        history_params = {'teams': 'Delhi Daredevils'}
        
        async with session.get(f"{API_URL}/teams/elo-history", params=history_params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Teams requested: {data['teams_requested']}")
                print(f"Teams found: {data['teams_found']}")
                
                for team_name, history in data['elo_histories'].items():
                    print(f"\n{team_name}: {len(history)} records")
                    if history:
                        print(f"  First record: {history[0]['date']} - ELO: {history[0]['elo']}")
                        print(f"  Last record: {history[-1]['date']} - ELO: {history[-1]['elo']}")
                        
                        # Check when records stop
                        last_year = history[-1]['date'][:4]
                        print(f"  Last year with data: {last_year}")
            else:
                print(f"Error: {response.status}")
        
        # Test 4: Test what happens when we request both names
        print("\n4. Testing ELO history for both 'Delhi Capitals' and 'Delhi Daredevils'...")
        history_params = {'teams': ['Delhi Capitals', 'Delhi Daredevils']}
        
        async with session.get(f"{API_URL}/teams/elo-history", params=history_params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Teams requested: {data['teams_requested']}")
                print(f"Teams found: {data['teams_found']}")
                
                total_records = 0
                for team_name, history in data['elo_histories'].items():
                    print(f"\n{team_name}: {len(history)} records")
                    total_records += len(history)
                    if history:
                        print(f"  Date range: {history[0]['date']} to {history[-1]['date']}")
                        print(f"  ELO range: {min(r['elo'] for r in history)} to {max(r['elo'] for r in history)}")
                
                print(f"\nTotal records across all Delhi teams: {total_records}")
            else:
                print(f"Error: {response.status}")
        
        # Test 5: Check the database directly for team name variations
        print("\n5. Checking what team names exist in the database...")
        # This would require a database query - you might want to run this separately
        
        print("\n=== Summary ===")
        print("Check the above output to identify:")
        print("1. Are both 'Delhi Capitals' and 'Delhi Daredevils' in rankings?")
        print("2. Does 'Delhi Capitals' return any ELO history?")
        print("3. Where does 'Delhi Daredevils' ELO history end?")
        print("4. Is there a gap in the data around 2019?")
        print("5. Do we get complete history when requesting both names?")

if __name__ == "__main__":
    asyncio.run(debug_delhi_transition())
