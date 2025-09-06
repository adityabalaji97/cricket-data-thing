#!/usr/bin/env python3
"""
Find players who actually played in Major League Cricket
"""

from database import get_session
from sqlalchemy.sql import text
import logging

def find_mlc_players():
    """Find players who played in Major League Cricket"""
    db = next(get_session())
    
    try:
        # Get players from Major League Cricket
        query = text("""
            SELECT DISTINCT bs.striker as player, COUNT(*) as matches
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE m.competition = 'Major League Cricket'
            GROUP BY bs.striker
            ORDER BY matches DESC
            LIMIT 10
        """)
        
        results = db.execute(query).fetchall()
        
        print("=== PLAYERS IN MAJOR LEAGUE CRICKET ===")
        if results:
            print(f"{'Player':<25} {'Matches':<10}")
            print("-" * 40)
            for row in results:
                print(f"{row.player:<25} {row.matches:<10}")
        else:
            print("No players found in Major League Cricket")
            
        return results
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return []
    finally:
        db.close()

def test_with_mlc_player(player_name):
    """Test the API with a player who actually played in MLC"""
    import requests
    from urllib.parse import quote
    
    base_url = "https://hindsight2020.vercel.app/api"
    
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
    
    print(f"\n=== TESTING API WITH {player_name} ===")
    print(f"URL: {url}")
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
                print("✅ SUCCESS: API is working correctly!")
                print(f"Player has {matches} matches with {runs} runs in Major League Cricket")
                return True
            else:
                print("❌ ISSUE: Still getting empty overall stats")
                return False
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("FINDING PLAYERS IN MAJOR LEAGUE CRICKET")
    print("=" * 50)
    
    # Find players who actually played in MLC
    mlc_players = find_mlc_players()
    
    if mlc_players:
        # Test with the first player who has the most matches
        top_player = mlc_players[0].player
        print(f"\nTesting API with {top_player} (who actually played in MLC)...")
        success = test_with_mlc_player(top_player)
        
        if success:
            print(f"\n🎉 CONCLUSION: The API fix is working! The issue was that R Ravindra never played in Major League Cricket.")
        else:
            print(f"\n🔍 The API still has issues even with a player who did play in MLC.")
    else:
        print("\n❌ No players found in Major League Cricket database")
