#!/usr/bin/env python3
"""
Test the fixed phase stats endpoint
"""

import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000"

def test_fixed_phase_stats():
    """Test the fixed phase stats endpoint"""
    
    test_teams = ["RCB", "CSK", "MI", "KKR"]
    
    print("🏏 Testing Fixed Phase Stats Endpoint")
    print("="*50)
    
    for team_name in test_teams:
        print(f"\n🔍 Testing team: {team_name}")
        
        url = f"{BASE_URL}/teams/{team_name}/phase-stats"
        params = {
            "start_date": "2023-01-01",
            "end_date": "2025-09-06"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS! Status: {response.status_code}")
                
                phase_stats = data.get('phase_stats', {})
                print(f"📊 Results:")
                print(f"   - Total matches: {phase_stats.get('total_matches', 0)}")
                print(f"   - Context: {phase_stats.get('context', 'N/A')}")
                print(f"   - Benchmark teams: {phase_stats.get('benchmark_teams', 0)}")
                
                # Show phase breakdown
                for phase in ['powerplay', 'middle_overs', 'death_overs']:
                    phase_data = phase_stats.get(phase, {})
                    runs = phase_data.get('runs', 0)
                    balls = phase_data.get('balls', 0)
                    sr = phase_data.get('strike_rate', 0)
                    norm_sr = phase_data.get('normalized_strike_rate', 0)
                    print(f"   - {phase}: {runs}/{balls} (SR: {sr:.1f}, Norm: {norm_sr})")
                
            else:
                print(f"❌ FAILED! Status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"Raw error: {response.text[:200]}")
                    
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Is it running?")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print(f"\n{'='*50}")
    print("🎯 Test completed!")

if __name__ == "__main__":
    test_fixed_phase_stats()
