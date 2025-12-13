"""
Debug script to test player summary generation
"""

import sys
sys.path.append('/Users/adityabalaji/cdt/cricket-data-thing')

from services.player_patterns import detect_batter_patterns
import json

# Test with mock data first
test_player = "V Kohli"

print(f"Testing pattern detection for: {test_player}")
print("=" * 60)

# Fetch stats using the API
import requests

# Test 1: Check if player exists
response = requests.get(f"http://localhost:8000/player/{test_player}/stats")
print(f"\nAPI Response Status: {response.status_code}")

if response.status_code == 200:
    stats = response.json()
    print("\n📊 RAW STATS:")
    print(f"Matches: {stats.get('overall', {}).get('matches', 0)}")
    print(f"Runs: {stats.get('overall', {}).get('runs', 0)}")
    print(f"Average: {stats.get('overall', {}).get('average', 0)}")
    print(f"Strike Rate: {stats.get('overall', {}).get('strike_rate', 0)}")
    
    print("\n🔍 PHASE STATS:")
    phase_stats = stats.get('phase_stats', {})
    for phase_name, phase_data in phase_stats.items():
        if isinstance(phase_data, dict) and phase_name in ['overall', 'pace', 'spin']:
            print(f"\n{phase_name.upper()}:")
            if 'powerplay' in phase_data:
                pp = phase_data['powerplay']
                print(f"  Powerplay: {pp.get('runs', 0)} runs @ SR {pp.get('strike_rate', 0):.1f}")
            if 'middle' in phase_data:
                mid = phase_data['middle']
                print(f"  Middle: {mid.get('runs', 0)} runs @ SR {mid.get('strike_rate', 0):.1f}")
            if 'death' in phase_data:
                death = phase_data['death']
                print(f"  Death: {death.get('runs', 0)} runs @ SR {death.get('strike_rate', 0):.1f}")
    
    # Add player name
    stats['player_name'] = test_player
    
    # Test pattern detection
    print("\n🎯 DETECTED PATTERNS:")
    patterns = detect_batter_patterns(stats)
    print(json.dumps(patterns, indent=2))
    
    print("\n✅ PATTERN SUMMARY:")
    print(f"Style: {patterns.get('style_classification', 'unknown')}")
    print(f"Primary Phase: {patterns.get('primary_phase', 'unknown')}")
    print(f"Strengths found: {len(patterns.get('strengths', []))}")
    print(f"Weaknesses found: {len(patterns.get('weaknesses', []))}")
    print(f"Entry pattern: {patterns.get('entry_pattern', 'unknown')}")
    
    if patterns.get('strengths'):
        print("\n💪 STRENGTHS:")
        for i, s in enumerate(patterns['strengths'][:2], 1):
            print(f"  {i}. {s['context']}: SR {s['strike_rate']:.0f}, Avg {s.get('average', 0):.1f}")
    
    if patterns.get('weaknesses'):
        print("\n⚠️ WEAKNESSES:")
        for i, w in enumerate(patterns['weaknesses'][:1], 1):
            print(f"  {i}. {w['context']}: SR {w['strike_rate']:.0f}, Avg {w.get('average', 0):.1f}")

else:
    print(f"\n❌ Error: Could not fetch stats")
    print(f"Response: {response.text[:500]}")
    
    # Try to list available players
    print("\n\n📋 Available players (searching for 'Kohli'):")
    players_response = requests.get("http://localhost:8000/players")
    if players_response.status_code == 200:
        players = players_response.json()
        kohli_players = [p for p in players if 'Kohli' in p or 'kohli' in p]
        for p in kohli_players[:10]:
            print(f"  - {p}")
