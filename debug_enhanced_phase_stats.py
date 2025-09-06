#!/usr/bin/env python3
"""
Enhanced debug script for team phase stats endpoint with detailed logging
"""

import requests
import json
import logging
from datetime import date, timedelta

# Set up logging to see all details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Base URL for the API
BASE_URL = "http://localhost:8000"

def debug_phase_stats_enhanced():
    """Debug the phase stats endpoint with enhanced logging"""
    
    # Test with different teams to isolate the issue
    test_teams = ["RCB", "CSK", "MI", "KKR"]
    
    for team_name in test_teams:
        print(f"\n{'='*60}")
        print(f"🔍 Testing team: {team_name}")
        print(f"{'='*60}")
        
        url = f"{BASE_URL}/teams/{team_name}/phase-stats"
        
        # Add date parameters to make it more realistic
        params = {
            "start_date": "2023-01-01",
            "end_date": "2025-09-06"
        }
        
        print(f"📍 URL: {url}")
        print(f"📊 Parameters: {params}")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            print(f"📈 Status Code: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS!")
                print(f"📊 Team Data Summary:")
                print(f"   - Total matches: {data.get('phase_stats', {}).get('total_matches', 'N/A')}")
                print(f"   - Context: {data.get('phase_stats', {}).get('context', 'N/A')}")
                print(f"   - Benchmark teams: {data.get('phase_stats', {}).get('benchmark_teams', 'N/A')}")
                
                # Show a compact summary of phase stats
                for phase in ['powerplay', 'middle_overs', 'death_overs']:
                    phase_data = data.get('phase_stats', {}).get(phase, {})
                    print(f"   - {phase}: {phase_data.get('runs', 0)} runs, {phase_data.get('balls', 0)} balls")
                
                # Exit on first success to avoid flooding logs
                break
                
            else:
                print("❌ ERROR Response:")
                print(f"📄 Response Text: {response.text}")
                
                # Try to parse as JSON for better error info
                try:
                    error_data = response.json()
                    print(f"🔍 Error Details: {json.dumps(error_data, indent=2)}")
                except:
                    print("❗ Raw response (not JSON):", response.text[:500])
                    
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to API server. Is it running on port 8000?")
            break
        except requests.exceptions.Timeout:
            print("❌ Request timed out after 30 seconds")
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")

def test_simple_endpoints():
    """Test simpler endpoints to verify the server is working"""
    print(f"\n{'='*60}")
    print(f"🔧 Testing basic endpoints")
    print(f"{'='*60}")
    
    # Test root endpoint
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        print(f"Root endpoint (/): {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Server is responding")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Root endpoint error: {str(e)}")
    
    # Test teams endpoint
    try:
        response = requests.get(f"{BASE_URL}/teams", timeout=10)
        print(f"Teams endpoint (/teams): {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Teams endpoint working, found {len(data)} teams")
        else:
            print(f"❌ Teams endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Teams endpoint error: {str(e)}")
    
    # Test a simple team matches endpoint
    try:
        response = requests.get(f"{BASE_URL}/teams/RCB/matches", timeout=10)
        print(f"Team matches endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Team matches working, found {data.get('total_matches', 0)} matches")
        else:
            print(f"❌ Team matches failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Team matches error: {str(e)}")

def check_server_logs():
    """Instructions for checking server logs"""
    print(f"\n{'='*60}")
    print(f"📋 Server Log Instructions")
    print(f"{'='*60}")
    print("To see detailed server logs, check:")
    print("1. Terminal where you started the FastAPI server")
    print("2. Look for detailed logging from the enhanced phase stats service")
    print("3. The logs will show exactly which step failed")
    print("4. Look for messages starting with 'Step X:' to identify the failure point")
    print("")
    print("If the server isn't running, start it with:")
    print("   cd /Users/adityabalaji/cdt/cricket-data-thing")
    print("   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    print("🏏 Enhanced Team Phase Stats Debugging")
    print("="*60)
    
    # First test basic endpoints
    test_simple_endpoints()
    
    # Then test the problematic phase stats endpoint
    debug_phase_stats_enhanced()
    
    # Show log checking instructions
    check_server_logs()
    
    print("\n" + "="*60)
    print("💡 Next Steps:")
    print("1. Check the server terminal for detailed logs")
    print("2. Look for the specific step where the error occurs")
    print("3. The enhanced logging will show SQL queries and parameters")
    print("4. If you see the error, we can fix the specific issue")
