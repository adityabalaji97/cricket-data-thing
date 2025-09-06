"""
Test the enhanced league matching functionality
"""

def test_enhanced_matching():
    from models import expand_league_abbreviations
    
    test_cases = [
        "Major League Cricket",
        "MLC", 
        "Vitality Blast",
        "Vitality Blast Men",
        "IPL",
        "Indian Premier League"
    ]
    
    print("=== Testing Enhanced League Matching ===")
    for test in test_cases:
        try:
            result = expand_league_abbreviations([test])
            print(f"'{test}' -> {result}")
        except Exception as e:
            print(f"Error with '{test}': {e}")

if __name__ == "__main__":
    test_enhanced_matching()
