#!/usr/bin/env python3
"""
Test script for the new team phase stats endpoint
"""

import requests
import json
from datetime import date, timedelta

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_phase_stats_endpoint():
    """Test the new phase stats endpoint"""
    
    # Test with CSK (a common team)
    team_name = "CSK"
    
    # Test with date range (last 6 months for example)
    end_date = date.today()
    start_date = end_date - timedelta(days=180)
    
    url = f"{BASE_URL}/teams/{team_name}/phase-stats"
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
            print(f"Success! Team: {data['team']}")
            print(f"Date range: {data['date_range']['start']} to {data['date_range']['end']}")
            
            phase_stats = data['phase_stats']
            print(f"\nPhase Statistics:")
            print(f"Total Matches: {phase_stats['total_matches']}")
            
            # Display phase-wise stats
            phases = ['powerplay', 'middle_overs', 'death_overs']
            for phase in phases:
                if phase in phase_stats:
                    stats = phase_stats[phase]
                    print(f"\n{phase.replace('_', ' ').title()}:")
                    print(f"  Runs: {stats['runs']}")
                    print(f"  Balls: {stats['balls']}")
                    print(f"  Wickets: {stats['wickets']}")
                    print(f"  Average: {stats['average']:.2f}")
                    print(f"  Strike Rate: {stats['strike_rate']:.2f}")
            
            # Show formatted radar data
            print(f"\nRadar Chart Data (Real Benchmarking):")
            print(f"Context: {phase_stats.get('context', 'Unknown')}")
            print(f"Benchmark Teams: {phase_stats.get('benchmark_teams', 0)}")
            print(f"PP Avg: {phase_stats['powerplay']['normalized_average']:.1f}%ile (actual: {phase_stats['powerplay']['average']:.2f})")
            print(f"PP SR: {phase_stats['powerplay']['normalized_strike_rate']:.1f}%ile (actual: {phase_stats['powerplay']['strike_rate']:.2f})")
            print(f"Mid Avg: {phase_stats['middle_overs']['normalized_average']:.1f}%ile (actual: {phase_stats['middle_overs']['average']:.2f})")
            print(f"Mid SR: {phase_stats['middle_overs']['normalized_strike_rate']:.1f}%ile (actual: {phase_stats['middle_overs']['strike_rate']:.2f})")
            print(f"Death Avg: {phase_stats['death_overs']['normalized_average']:.1f}%ile (actual: {phase_stats['death_overs']['average']:.2f})")
            print(f"Death SR: {phase_stats['death_overs']['normalized_strike_rate']:.1f}%ile (actual: {phase_stats['death_overs']['strike_rate']:.2f})")
            
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

def test_endpoint_multiple_teams():
    """Test endpoint with different teams"""
    teams = ["MI", "RCB", "KKR"]
    
    print(f"\nTesting multiple teams: {teams}")
    print("-" * 50)
    
    for team in teams:
        url = f"{BASE_URL}/teams/{team}/phase-stats"
        
        try:
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                phase_stats = data['phase_stats']
                total_matches = phase_stats['total_matches']
                context = phase_stats.get('context', 'Unknown')
                benchmark_teams = phase_stats.get('benchmark_teams', 0)
                pp_avg_norm = phase_stats['powerplay']['normalized_average']
                pp_sr_norm = phase_stats['powerplay']['normalized_strike_rate']
                print(f"{team}: {total_matches} matches, PP Avg: {pp_avg_norm:.1f}%ile, PP SR: {pp_sr_norm:.1f}%ile ({context}, {benchmark_teams} benchmark teams)")
            else:
                print(f"{team}: Error {response.status_code}")
                
        except Exception as e:
            print(f"{team}: ERROR - {str(e)}")
    
    return True

if __name__ == "__main__":
    print("🏏 Testing Team Phase Stats Endpoint")
    print("=" * 50)
    
    # Test with date range
    success1 = test_phase_stats_endpoint()
    
    # Test multiple teams
    success2 = test_endpoint_multiple_teams()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ All tests passed! The phase stats endpoint is working correctly.")
        print("\n📊 The radar chart will show 6 vertices:")
        print("   • Powerplay Average")
        print("   • Powerplay Strike Rate")
        print("   • Middle Overs Average")
        print("   • Middle Overs Strike Rate")
        print("   • Death Overs Average")
        print("   • Death Overs Strike Rate")
    else:
        print("❌ Some tests failed. Check the output above for details.")
