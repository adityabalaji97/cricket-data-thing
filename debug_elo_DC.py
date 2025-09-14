#!/usr/bin/env python3
"""
Debug the exact API calls from the frontend to identify the ELO inconsistency
"""

import requests
import json
from datetime import datetime

def debug_api_call(url, label):
    """Debug a specific API call and analyze the response"""
    print(f"\n{'='*60}")
    print(f"DEBUGGING: {label}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"Response Status: {response.status_code}")
        print(f"Teams in response: {len(data.get('elo_histories', {}))}")
        
        # Focus on DC's data
        elo_histories = data.get('elo_histories', {})
        
        if 'DC' in elo_histories:
            dc_history = elo_histories['DC']
            print(f"\nDC History: {len(dc_history)} matches")
            
            # Find matches around November 8, 2020
            target_date = "2020-11-08"
            relevant_matches = []
            
            for match in dc_history:
                match_date = match['date']
                if match_date >= "2020-11-01" and match_date <= "2020-11-30":
                    relevant_matches.append(match)
            
            print(f"\nDC matches in November 2020:")
            for match in relevant_matches:
                print(f"  {match['date']}: ELO = {match['elo']}, vs {match.get('opponent', 'Unknown')}, Result = {match.get('result', 'Unknown')}")
            
            # Find the exact match on Nov 8, 2020
            nov_8_matches = [m for m in dc_history if m['date'] == target_date]
            if nov_8_matches:
                print(f"\n🎯 DC ELO on {target_date}:")
                for match in nov_8_matches:
                    print(f"  ELO = {match['elo']}")
                    print(f"  Opponent = {match.get('opponent', 'Unknown')}")
                    print(f"  Result = {match.get('result', 'Unknown')}")
                    print(f"  Match ID = {match.get('match_id', 'Unknown')}")
            else:
                print(f"\n❌ No DC matches found on {target_date}")
                
                # Find the closest match before that date
                matches_before = [m for m in dc_history if m['date'] <= target_date]
                if matches_before:
                    # Sort by date and get the most recent
                    matches_before.sort(key=lambda x: x['date'])
                    latest_before = matches_before[-1]
                    print(f"\n📅 Most recent DC match before {target_date}:")
                    print(f"  Date: {latest_before['date']}")
                    print(f"  ELO = {latest_before['elo']}")
                    print(f"  This ELO would be used for {target_date} in the racer chart")
        else:
            print(f"\n❌ DC not found in response")
            print(f"Available teams: {list(elo_histories.keys())}")
            
        # Check for duplicate team entries
        print(f"\nAll teams in response:")
        for team_name, history in elo_histories.items():
            print(f"  {team_name}: {len(history)} matches")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Debug both API calls to identify the ELO inconsistency"""
    
    # The exact URLs from the browser network tab
    url_2020_2021 = "https://hindsight2020.vercel.app/api/teams/elo-history?teams=CSK&teams=MI&teams=DC&teams=KKR&teams=RCB&teams=PBKS&teams=RR&teams=SRH&teams=PBKS&start_date=2020-01-01&end_date=2021-12-31"
    
    url_2008_2025 = "https://hindsight2020.vercel.app/api/teams/elo-history?teams=RCB&teams=RPSG&teams=GT&teams=PBKS&teams=KKR&teams=MI&teams=LSG&teams=SRH&teams=PBKS&teams=KTK&teams=DC&teams=GL&teams=RR&teams=RPSG&teams=CSK&teams=DC&teams=DCh&teams=Pune+Warriors&start_date=2008-01-01&end_date=2025-09-14"
    
    print("🔍 DEBUGGING ELO RACER CHART API CALLS")
    print("Comparing DC's ELO values on November 8, 2020")
    
    # Debug both calls
    debug_api_call(url_2020_2021, "2020-2021 Date Range")
    debug_api_call(url_2008_2025, "2008-2025 Date Range") 
    
    print(f"\n{'='*60}")
    print("🎯 ANALYSIS COMPLETE")
    print("Check the ELO values above to identify the inconsistency")
    print("If they're different, we've found the backend bug!")
    print("If they're the same, the issue is in frontend processing")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()