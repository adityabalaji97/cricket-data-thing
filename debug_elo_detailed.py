#!/usr/bin/env python3
"""
Debug exactly what the ELO history service returns when we request Delhi Capitals
"""

import asyncio
import aiohttp
import json

API_URL = "http://localhost:8000"

async def debug_elo_history_detailed():
    async with aiohttp.ClientSession() as session:
        print("=== Detailed ELO History Debug ===\n")
        
        # Test what happens when we request "Delhi Capitals" (what the frontend sends)
        print("1. Testing ELO history for 'Delhi Capitals' (what frontend sends)...")
        params = {'teams': 'Delhi Capitals'}
        
        async with session.get(f"{API_URL}/teams/elo-history", params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Teams requested: {data['teams_requested']}")
                print(f"Teams found: {data['teams_found']}")
                
                for team_key, history in data['elo_histories'].items():
                    print(f"\n{team_key}: {len(history)} records")
                    
                    if history:
                        # Sort by date to see chronological order
                        sorted_history = sorted(history, key=lambda x: x['date'])
                        
                        print(f"  Date range: {sorted_history[0]['date']} to {sorted_history[-1]['date']}")
                        print(f"  ELO range: {min(r['elo'] for r in history)} to {max(r['elo'] for r in history)}")
                        
                        # Show first few and last few records
                        print("  First 5 records:")
                        for i, record in enumerate(sorted_history[:5]):
                            print(f"    {record['date']}: ELO {record['elo']}")
                        
                        print("  Last 5 records:")
                        for i, record in enumerate(sorted_history[-5:]):
                            print(f"    {record['date']}: ELO {record['elo']}")
                        
                        # Check what years we have data for
                        years = {}
                        for record in history:
                            year = record['date'][:4]
                            if year not in years:
                                years[year] = []
                            years[year].append(record['elo'])
                        
                        print("  Data by year:")
                        for year in sorted(years.keys()):
                            elos = years[year]
                            print(f"    {year}: {len(elos)} matches, ELO range {min(elos)}-{max(elos)}")
                        
                        # Check for the 1444 issue specifically
                        elo_1444 = [r for r in history if r['elo'] == 1444]
                        if elo_1444:
                            print(f"  Found {len(elo_1444)} records with ELO 1444:")
                            for record in elo_1444[:3]:  # Show first 3
                                print(f"    {record['date']}: vs {record['opponent']}")
            else:
                print(f"Error: {response.status}")
        
        # Compare with what we get when requesting both names explicitly
        print("\n2. Testing with explicit Delhi team names...")
        params = {'teams': ['Delhi Capitals', 'Delhi Daredevils']}
        
        async with session.get(f"{API_URL}/teams/elo-history", params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Teams requested: {data['teams_requested']}")
                print(f"Teams found: {data['teams_found']}")
                
                total_records = 0
                for team_key, history in data['elo_histories'].items():
                    total_records += len(history)
                    print(f"\n{team_key}: {len(history)} records")
                
                print(f"\nTotal records when requesting both: {total_records}")
        
        # Test if the issue is in our get_all_team_name_variations function
        print("\n3. Let's test what variations our function returns...")
        # This would require importing our function, but let's check the raw data instead
        
        print("\n4. Testing direct team name queries...")
        for team_name in ['Delhi Capitals', 'Delhi Daredevils']:
            params = {'teams': team_name}
            async with session.get(f"{API_URL}/teams/elo-history", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_records = sum(len(history) for history in data['elo_histories'].values())
                    print(f"'{team_name}' -> {total_records} total records")

if __name__ == "__main__":
    asyncio.run(debug_elo_history_detailed())
