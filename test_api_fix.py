#!/usr/bin/env python3
"""
Quick test script to verify the enhanced league matching works for player stats
"""

import requests
import json
from urllib.parse import quote

def test_player_stats_api():
    """Test the player stats API with Major League Cricket"""
    
    base_url = "https://hindsight2020.vercel.app/api"
    player_name = "R Ravindra"
    
    # Test parameters
    params = {
        "start_date": "2020-01-01",
        "end_date": "2025-06-21", 
        "leagues": ["Major League Cricket"],
        "include_international": False
    }
    
    # URL encode the player name
    encoded_player = quote(player_name)
    
    # Build URL
    url = f"{base_url}/player/{encoded_player}/stats"
    
    print(f"Testing: {url}")
    print(f"Parameters: {params}")
    
    try:
        # Make the API call
        response = requests.get(url, params=params)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we got valid data
            overall = data.get('overall', {})
            matches = overall.get('matches', 0)
            runs = overall.get('runs', 0)
            
            print(f"Matches found: {matches}")
            print(f"Total runs: {runs}")
            
            if matches > 0 and runs > 0:
                print("✅ SUCCESS: Enhanced league matching is working!")
                print(f"Player has {matches} matches with {runs} runs in Major League Cricket")
            else:
                print("❌ ISSUE: Still getting empty overall stats")
                print("Response data:")
                print(json.dumps(data, indent=2))
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def test_vitality_blast():
    """Test with Vitality Blast to see if it handles variations"""
    
    base_url = "https://hindsight2020.vercel.app/api"
    
    # Test parameters for Vitality Blast
    params = {
        "start_date": "2020-01-01",
        "end_date": "2025-06-21", 
        "leagues": ["Vitality Blast"],
        "include_international": False
    }
    
    url = f"{base_url}/venue_notes/All Venues"
    
    print(f"\nTesting Vitality Blast: {url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, params=params)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total_matches = data.get('total_matches', 0)
            
            print(f"Total matches found: {total_matches}")
            
            if total_matches > 0:
                print("✅ SUCCESS: Vitality Blast variations working!")
            else:
                print("❌ ISSUE: No matches found for Vitality Blast")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

if __name__ == "__main__":
    print("=== Testing Enhanced League Matching ===\n")
    
    # Test Major League Cricket
    test_player_stats_api()
    
    # Test Vitality Blast variations
    test_vitality_blast()
    
    print("\n=== Test Complete ===")
