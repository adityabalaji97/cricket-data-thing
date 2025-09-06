"""
Debug script to investigate par score distribution calculations
"""

from database import get_session
from sqlalchemy import text
from datetime import date

def debug_par_scores():
    session_gen = get_session()
    session = next(session_gen)
    
    venue = "Shere Bangla National Stadium, Mirpur"
    league = "Bangladesh Premier League"
    before_date = date(2022, 1, 1)
    
    print("🔍 Debugging Par Score Distribution")
    print("=" * 50)
    
    # Check raw delivery data for a few matches
    print("1. Sample raw delivery data:")
    sample_query = text("""
        SELECT m.id, m.date, d.innings, d.over, d.ball, 
               d.runs_off_bat, d.extras, (d.runs_off_bat + d.extras) as total_runs
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        WHERE m.venue = :venue
        AND m.competition = :league
        AND m.date < :before_date
        AND d.innings = 1
        AND d.over <= 2
        ORDER BY m.date DESC, d.over, d.ball
        LIMIT 20
    """)
    
    sample_result = session.execute(sample_query, {
        "venue": venue,
        "league": league,
        "before_date": before_date
    }).fetchall()
    
    for row in sample_result:
        print(f"   Match {row.id[:8]}: Over {row.over}.{row.ball} = {row.total_runs} runs")
    
    # Check cumulative runs for a specific match
    print("\n2. Cumulative runs for one match:")
    if sample_result:
        test_match = sample_result[0].id
        cumulative_query = text("""
            SELECT d.over,
                   SUM(d.runs_off_bat + d.extras) OVER (ORDER BY d.over, d.ball) as cumulative_runs
            FROM deliveries d
            WHERE d.match_id = :match_id
            AND d.innings = 1
            AND d.over <= 19
            ORDER BY d.over, d.ball
        """)
        
        cumulative_result = session.execute(cumulative_query, {
            "match_id": test_match
        }).fetchall()
        
        # Show runs at end of each over
        current_over = -1
        for row in cumulative_result:
            if row.over != current_over:
                current_over = row.over
                print(f"   End of over {current_over}: {row.cumulative_runs} runs")
                if current_over >= 5:  # Stop after showing first few overs
                    break
    
    # Check our par score query step by step
    print("\n3. Par score query breakdown:")
    
    # First, check the over_scores CTE
    over_scores_query = text("""
        WITH over_scores AS (
            SELECT 
                d.match_id,
                d.innings,
                d.over,
                SUM(d2.runs_off_bat + d2.extras) as runs_at_over
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            JOIN deliveries d2 ON d.match_id = d2.match_id 
                AND d.innings = d2.innings 
                AND d2.over <= d.over
            WHERE m.venue = :venue
                AND m.date < :before_date
                AND m.competition = :league
                AND d.over < 20
            GROUP BY d.match_id, d.innings, d.over
        )
        SELECT match_id, over, runs_at_over
        FROM over_scores
        WHERE innings = 1 AND over IN (5, 10, 15)
        ORDER BY match_id, over
        LIMIT 15
    """)
    
    over_scores_result = session.execute(over_scores_query, {
        "venue": venue,
        "league": league, 
        "before_date": before_date
    }).fetchall()
    
    print("   Sample cumulative runs by over:")
    current_match = None
    for row in over_scores_result:
        if row.match_id != current_match:
            current_match = row.match_id
            print(f"   Match {row.match_id[:8]}:")
        print(f"     Over {row.over}: {row.runs_at_over} runs")
    
    # Check final scores distribution
    print("\n4. Final scores distribution:")
    final_scores_query = text("""
        SELECT 
            SUM(runs_off_bat + extras) as final_score,
            COUNT(*) as frequency
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        WHERE m.venue = :venue
        AND m.competition = :league
        AND m.date < :before_date
        AND d.innings = 1
        GROUP BY d.match_id
        ORDER BY final_score
    """)
    
    final_scores_result = session.execute(final_scores_query, {
        "venue": venue,
        "league": league,
        "before_date": before_date
    }).fetchall()
    
    if final_scores_result:
        scores = [row.final_score for row in final_scores_result]
        print(f"   Total matches: {len(scores)}")
        print(f"   Score range: {min(scores)} to {max(scores)}")
        print(f"   Average final score: {sum(scores)/len(scores):.1f}")
        print(f"   Sample scores: {scores[:10]}")
    
    # Check if there are any data quality issues
    print("\n5. Data quality checks:")
    
    # Check for unusually high individual ball runs
    high_runs_query = text("""
        SELECT d.runs_off_bat, d.extras, (d.runs_off_bat + d.extras) as total,
               COUNT(*) as frequency
        FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        WHERE m.venue = :venue
        AND m.competition = :league
        AND m.date < :before_date
        AND (d.runs_off_bat + d.extras) > 10
        GROUP BY d.runs_off_bat, d.extras
        ORDER BY total DESC
    """)
    
    high_runs_result = session.execute(high_runs_query, {
        "venue": venue,
        "league": league,
        "before_date": before_date
    }).fetchall()
    
    if high_runs_result:
        print("   Unusually high runs per ball:")
        for row in high_runs_result:
            print(f"     {row.total} runs ({row.runs_off_bat} + {row.extras} extras): {row.frequency} times")
    else:
        print("   ✅ No unusually high runs per ball found")
    
    session.close()

if __name__ == "__main__":
    debug_par_scores()
