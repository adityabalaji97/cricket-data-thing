#!/usr/bin/env python3
"""
Debug script for team phase stats endpoint issues
"""

import requests
import json
from datetime import date, timedelta

# Base URL for the API
BASE_URL = "http://localhost:8000"

def debug_phase_stats():
    """Debug the phase stats endpoint with detailed error info"""
    
    # Test with CSK first
    team_name = "CSK"
    url = f"{BASE_URL}/teams/{team_name}/phase-stats"
    
    print(f"🔍 Debugging endpoint: {url}")
    print("=" * 50)
    
    try:
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success!")
            print(json.dumps(data, indent=2))
        else:
            print("❌ Error Response:")
            print(f"Status: {response.status_code}")
            print(f"Response Text: {response.text}")
            
            # Try to parse as JSON for better error info
            try:
                error_data = response.json()
                print(f"Error Details: {json.dumps(error_data, indent=2)}")
            except:
                print("Raw response (not JSON):", response.text)
                
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Is it running?")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_matches_endpoint():
    """Test if the matches endpoint works (to isolate the issue)"""
    team_name = "CSK"
    url = f"{BASE_URL}/teams/{team_name}/matches"
    
    print(f"\n🔍 Testing matches endpoint: {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url)
        print(f"Matches endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Matches endpoint works! Found {data['total_matches']} matches")
        else:
            print(f"❌ Matches endpoint also failing: {response.text}")
            
    except Exception as e:
        print(f"❌ Matches endpoint error: {str(e)}")

if __name__ == "__main__":
    print("🏏 Debugging Team Phase Stats Issues")
    print("=" * 50)
    
    debug_phase_stats()
    test_matches_endpoint()
    
    print("\n" + "=" * 50)
    print("💡 If you see 500 errors, check the server logs for the exact SQL error.")
    print("💡 The issue is likely in the phase stats SQL query or data processing.")
