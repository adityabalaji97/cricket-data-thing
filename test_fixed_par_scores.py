"""
Test the fixed par score distribution
"""

from database import get_session
from context_model import VenueResourceTableBuilder
from datetime import date

def test_fixed_par_scores():
    print("🔧 Testing Fixed Par Score Distribution")
    print("=" * 50)
    
    session_gen = get_session()
    session = next(session_gen)
    
    builder = VenueResourceTableBuilder()
    
    venue = "Shere Bangla National Stadium, Mirpur"
    league = "Bangladesh Premier League"
    before_date = date(2022, 1, 1)
    
    print(f"Testing venue: {venue}")
    print(f"League: {league}")
    print(f"Before date: {before_date}")
    
    # Build par score distribution with fixed query
    par_distribution = builder.build_par_score_distribution(session, venue, before_date, league)
    
    print("\n📊 Fixed Par Score Results:")
    
    if par_distribution['innings']:
        for innings in [1, 2]:
            if innings in par_distribution['innings']:
                print(f"\n  Innings {innings}:")
                innings_data = par_distribution['innings'][innings]
                
                for over in [5, 10, 15, 19]:
                    if over in innings_data:
                        data = innings_data[over]
                        print(f"    Over {over}: avg={data['avg_score']:.1f}, median={data['median']:.1f}, samples={data['sample_size']}")
                        
                        # Validate the scores are reasonable
                        expected_min = over * 4  # Very conservative (4 runs per over)
                        expected_max = over * 12  # Aggressive (12 runs per over)
                        
                        if expected_min <= data['avg_score'] <= expected_max:
                            print(f"      ✅ Score looks reasonable ({expected_min}-{expected_max} expected)")
                        else:
                            print(f"      ⚠️  Score seems unusual ({expected_min}-{expected_max} expected)")
    
    # Compare with manual calculation for validation
    print("\n🔍 Manual Validation:")
    from sqlalchemy import text
    
    manual_query = text("""
        WITH match_scores AS (
            SELECT 
                d.match_id,
                d.innings,
                SUM(CASE WHEN d.over <= 4 THEN d.runs_off_bat + d.extras ELSE 0 END) as runs_after_5_overs,
                SUM(CASE WHEN d.over <= 9 THEN d.runs_off_bat + d.extras ELSE 0 END) as runs_after_10_overs,
                SUM(d.runs_off_bat + d.extras) as final_score
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE m.venue = :venue
            AND m.competition = :league
            AND m.date < :before_date
            AND d.innings = 1
            GROUP BY d.match_id, d.innings
        )
        SELECT 
            AVG(runs_after_5_overs) as avg_5_overs,
            AVG(runs_after_10_overs) as avg_10_overs,
            AVG(final_score) as avg_final,
            COUNT(*) as total_matches
        FROM match_scores
    """)
    
    manual_result = session.execute(manual_query, {
        "venue": venue,
        "league": league,
        "before_date": before_date
    }).fetchone()
    
    print(f"  Manual calculation:")
    print(f"    After 5 overs: {manual_result.avg_5_overs:.1f} runs")
    print(f"    After 10 overs: {manual_result.avg_10_overs:.1f} runs")
    print(f"    Final score: {manual_result.avg_final:.1f} runs")
    print(f"    Total matches: {manual_result.total_matches}")
    
    session.close()
    
    print("\n🎉 Par score distribution test complete!")

if __name__ == "__main__":
    test_fixed_par_scores()
