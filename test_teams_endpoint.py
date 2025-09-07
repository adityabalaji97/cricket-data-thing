#!/usr/bin/env python3
"""
Test the /teams endpoint to see if it's working
"""

import requests
import json

def test_teams_endpoint():
    """Test if the teams endpoint is working"""
    try:
        api_url = "http://localhost:8000"  # Adjust if your API runs on different port
        
        print("Testing /teams endpoint...")
        response = requests.get(f"{api_url}/teams")
        
        if response.status_code == 200:
            teams = response.json()
            print(f"✓ Teams endpoint working: {len(teams)} teams found")
            print("Sample teams:")
            for team in teams[:5]:
                print(f"  - {team['full_name']} ({team['abbreviated_name']})")
            return True
        else:
            print(f"✗ Teams endpoint failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection Error - Is the API server running on {api_url}?")
        return False
    except Exception as e:
        print(f"✗ Error testing teams endpoint: {e}")
        return False

def test_frontend_call():
    """Test the exact call the frontend would make"""
    try:
        # This simulates what the frontend does
        response = requests.get("http://localhost:8000/teams")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Frontend simulation successful")
            print(f"Response type: {type(data)}")
            print(f"Number of teams: {len(data)}")
            
            if len(data) > 0:
                print(f"First team structure: {data[0]}")
            
            return True
        else:
            print(f"\n✗ Frontend simulation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n✗ Frontend simulation error: {e}")
        return False

if __name__ == "__main__":
    print("=== TESTING TEAMS ENDPOINT ===")
    
    # Test basic endpoint
    if test_teams_endpoint():
        # Test frontend simulation
        test_frontend_call()
    
    print("\nIf both tests pass, the issue might be:")
    print("1. CORS (Cross-Origin Resource Sharing) issue")
    print("2. Frontend API URL configuration")
    print("3. Network connectivity between frontend and backend")
    print("\nCheck your browser's developer console (F12) for error messages.")
