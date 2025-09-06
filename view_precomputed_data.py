import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_session
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)

def view_precomputed_data():
    """View the data we've inserted into precomputed tables."""
    print("📊 Viewing Precomputed Data")
    print("=" * 50)
    
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # 1. Team Phase Stats
        print("\n🏏 TEAM PHASE STATS")
        print("-" * 30)
        team_query = text("""
            SELECT *
            FROM team_phase_stats
            ORDER BY avg_runs DESC
            LIMIT 10
        """)
        
        teams = session.execute(team_query).fetchall()
        print(f"Top 10 Teams by Average Runs:")
        print(f"{'Team':<25} {'Venue':<20} {'Phase':<10} {'Innings':<8} {'Avg Runs':<10} {'Avg Wickets':<12} {'Run Rate':<10} {'Balls Faced':<12} {'Boundary %':<12} {'Dot %':<8} {'Matches':<8}")
        print("-" * 130)
        for team in teams:
            print(f"{team.team:<25} {team.venue_identifier:<20} {team.phase:<10} {team.innings:<8} {team.avg_runs:<10.1f} {team.avg_wickets:<12.1f} {team.avg_run_rate:<10.2f} {team.avg_balls_faced:<12} {team.boundary_rate:<12.1f} {team.dot_rate:<8.1f} {team.matches_played:<8}")

        # 2. Venue Resources
        print("\n🏟️ VENUE RESOURCES")
        print("-" * 30)
        venue_query = text("""
            SELECT *
            FROM venue_resources
            ORDER BY sample_size DESC
            LIMIT 15
        """)
        
        venues = session.execute(venue_query).fetchall()
        print(f"Sample Venue Resource States:")
        print(f"{'Venue':<25} {'Inn':<3} {'Over':<4} {'Wkts':<4} {'Resource %':<10} {'Avg Score':<10} {'Sample':<6}")
        print("-" * 80)
        for venue in venues:
            venue_name = venue.venue[:24] if venue.venue else "Unknown"
            print(f"{venue_name:<25} {venue.innings:<3} {venue.over_num:<4} {venue.wickets_lost:<4} {venue.resource_percentage:<10.1f} {venue.avg_final_score:<10.1f} {venue.sample_size:<6}")

        # 3. WPA Outcomes
        print("\n🏆 WPA OUTCOMES")
        print("-" * 30)
        wpa_query = text("""
            SELECT *
            FROM wpa_outcomes
            ORDER BY sample_size DESC
            LIMIT 15
        """)
        
        wpa_outcomes = session.execute(wpa_query).fetchall()
        print(f"Sample WPA Outcome States:")
        print(f"{'Venue':<25} {'Target':<6} {'Over':<4} {'Wkts':<4} {'Score Range':<12} {'Win %':<8} {'Sample':<6}")
        print("-" * 85)
        for wpa in wpa_outcomes:
            venue_name = wpa.venue[:24] if wpa.venue else "Unknown"
            score_range = f"{wpa.runs_range_min}-{wpa.runs_range_max}"
            win_pct = f"{wpa.win_probability*100:.1f}%"
            print(f"{venue_name:<25} {wpa.target_bucket:<6} {wpa.over_bucket:<4} {wpa.wickets_lost:<4} {score_range:<12} {win_pct:<8} {wpa.sample_size:<6}")

        # 4. Top Batters
        print("\n🏏 TOP BATTING BASELINES")
        print("-" * 30)
        batting_query = text("""
            SELECT *
            FROM player_baselines
            WHERE role = 'batting'
            ORDER BY avg_runs DESC
            LIMIT 10
        """)
        
        batters = session.execute(batting_query).fetchall()
        print(f"Top 10 Batters by Average Runs:")
        print(f"{'Player':<25} {'Venue Type':<15} {'Venue':<20} {'Phase':<10} {'Avg Runs':<10} {'Strike Rate':<12} {'Boundary %':<12} {'Dot %':<8} {'Matches':<8}")
        print("-" * 130)
        for batter in batters:
            print(f"{batter.player_name:<25} {batter.venue_type:<15} {batter.venue_identifier or 'N/A':<20} {batter.phase:<10} {batter.avg_runs:<10.1f} {batter.avg_strike_rate:<12.1f} {batter.boundary_percentage:<12.1f} {batter.dot_percentage:<8.1f} {batter.matches_played:<8}")
        
        # 5. Top Bowlers
        print("\n🏏 TOP BOWLING BASELINES")
        print("-" * 30)
        bowling_query = text("""
            SELECT *
            FROM player_baselines
            WHERE role = 'bowling'
            ORDER BY avg_wickets DESC
            LIMIT 10
        """)
        
        bowlers = session.execute(bowling_query).fetchall()
        print(f"Top 10 Bowlers by Average Wickets:")
        print(f"{'Player':<25} {'Venue Type':<15} {'Venue':<20} {'Phase':<10} {'Avg Wkts':<10} {'Economy':<10} {'Dot %':<10} {'Matches':<8}")
        print("-" * 130)
        for bowler in bowlers:
            print(f"{bowler.player_name:<25} {bowler.venue_type:<15} {bowler.venue_identifier or 'N/A':<20} {bowler.phase:<10} {bowler.avg_wickets:<10.2f} {bowler.avg_economy:<10.2f} {bowler.dot_ball_percentage:<10.1f} {bowler.matches_played:<8}")
        
        # 6. Summary Stats
        print("\n📈 SUMMARY STATISTICS")
        print("-" * 30)
        
        summary_query = text("""
            SELECT 
                'Teams' as category,
                COUNT(*) as total_records
            FROM team_phase_stats
            UNION ALL
            SELECT 
                'Venue Resources' as category,
                COUNT(*) as total_records
            FROM venue_resources
            UNION ALL
            SELECT 
                'WPA Outcomes' as category,
                COUNT(*) as total_records
            FROM wpa_outcomes
            UNION ALL
            SELECT 
                'Batting Players' as category,
                COUNT(*) as total_records
            FROM player_baselines WHERE role = 'batting'
            UNION ALL
            SELECT 
                'Bowling Players' as category,
                COUNT(*) as total_records
            FROM player_baselines WHERE role = 'bowling'
            UNION ALL
            SELECT 
                'Total Player Records' as category,
                COUNT(*) as total_records
            FROM player_baselines
        """)
        
        summary = session.execute(summary_query).fetchall()
        for row in summary:
            print(f"{row.category:<20}: {row.total_records:>6} records")
        
        # 7. Check computation runs
        print("\n🔄 COMPUTATION RUNS")
        print("-" * 30)
        
        runs_query = text("""
            SELECT 
                table_name,
                status,
                records_inserted,
                start_time,
                end_time,
                CASE 
                    WHEN end_time IS NOT NULL AND start_time IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (end_time - start_time))
                    ELSE NULL 
                END as duration_seconds
            FROM computation_runs
            ORDER BY start_time DESC
            LIMIT 5
        """)
        
        runs = session.execute(runs_query).fetchall()
        print(f"{'Table':<20} {'Status':<10} {'Records':<10} {'Duration':<10}")
        print("-" * 52)
        for run in runs:
            duration = f"{run.duration_seconds:.1f}s" if run.duration_seconds else "N/A"
            print(f"{run.table_name:<20} {run.status:<10} {run.records_inserted or 0:<10} {duration:<10}")
        
        print(f"\n✅ Precomputed data viewing completed!")
        
    except Exception as e:
        print(f"❌ Error viewing data: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

if __name__ == "__main__":
    view_precomputed_data()