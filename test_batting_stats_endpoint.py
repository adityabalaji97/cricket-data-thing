#!/usr/bin/env python3
"""
Quick test script for the new team batting stats endpoint
"""

import requests
import json
from datetime import date, timedelta

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_batting_stats_endpoint():
    """Test the new batting stats endpoint"""
    
    # Test with CSK (a common team)
    team_name = "CSK"
    
    # Test with date range (last 6 months for example)
    end_date = date.today()
    start_date = end_date - timedelta(days=180)
    
    url = f"{BASE_URL}/teams/{team_name}/batting-stats"
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
    
    print(f"Testing endpoint: {url}")
    print(f"Parameters: {params}")
    print("-" * 50)
    
    try:
        response = requests.get(url, params=params)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Found {data['total_records']} batting records for {data['team']}")
            print(f"Date range: {data['date_range']['start']} to {data['date_range']['end']}")
            
            if data['batting_stats']:
                # Show first record as example
                first_stat = data['batting_stats'][0]
                print(f"\nExample record:")
                print(f"Player: {first_stat['striker']}")
                print(f"Runs: {first_stat['runs']}")
                print(f"Balls: {first_stat['balls_faced']}")
                print(f"Strike Rate: {first_stat['strike_rate']}")
                print(f"Match: {first_stat['match_info']['date']} at {first_stat['match_info']['venue']}")
            
            return True
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API server.")
        print("Make sure the server is running with: python main.py")
        return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

def test_endpoint_without_dates():
    """Test endpoint without date filters"""
    team_name = "MI"
    url = f"{BASE_URL}/teams/{team_name}/batting-stats"
    
    print(f"\nTesting without date filters: {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Found {data['total_records']} total batting records for {data['team']}")
            return True
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("🏏 Testing Team Batting Stats Endpoint")
    print("=" * 50)
    
    # Test with date range
    success1 = test_batting_stats_endpoint()
    
    # Test without date filters
    success2 = test_endpoint_without_dates()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ All tests passed! The endpoint is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above for details.")
