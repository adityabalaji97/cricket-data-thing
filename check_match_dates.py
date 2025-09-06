"""
Quick script to check the date range of matches in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_session
from sqlalchemy import text
from datetime import date

def check_match_dates():
    """Check the date range of matches in our database."""
    print("📅 Checking Match Date Range in Database")
    print("=" * 50)
    
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # Get match date range
        date_query = text("""
            SELECT 
                MIN(date) as earliest_match,
                MAX(date) as latest_match,
                COUNT(*) as total_matches,
                COUNT(DISTINCT EXTRACT(YEAR FROM date)) as total_years
            FROM matches
        """)
        
        result = session.execute(date_query).fetchone()
        
        print(f"📊 Match Database Summary:")
        print(f"  Earliest Match: {result.earliest_match}")
        print(f"  Latest Match:   {result.latest_match}")
        print(f"  Total Matches:  {result.total_matches:,}")
        print(f"  Years Covered:  {result.total_years}")
        
        # Get matches per year
        yearly_query = text("""
            SELECT 
                EXTRACT(YEAR FROM date) as year,
                COUNT(*) as matches
            FROM matches
            GROUP BY EXTRACT(YEAR FROM date)
            ORDER BY year DESC
            LIMIT 10
        """)
        
        yearly_results = session.execute(yearly_query).fetchall()
        
        print(f"\n📈 Recent Years Match Count:")
        print(f"{'Year':<6} {'Matches':<8}")
        print("-" * 16)
        for row in yearly_results:
            print(f"{int(row.year):<6} {row.matches:<8}")
        
        # Check what our batch processor date covers
        batch_date = date(2025, 12, 31)
        print(f"\n🔧 Batch Processor Analysis:")
        print(f"  Cutoff Date Used: {batch_date}")
        print(f"  Latest Match:     {result.latest_match}")
        
        if result.latest_match <= batch_date:
            print(f"  ✅ Batch processor covers ALL {result.total_matches:,} matches")
        else:
            excluded_query = text("""
                SELECT COUNT(*) as excluded_matches
                FROM matches
                WHERE date > :cutoff_date
            """)
            excluded = session.execute(excluded_query, {"cutoff_date": batch_date}).fetchone()
            print(f"  ⚠️  Batch processor excludes {excluded.excluded_matches} recent matches")
        
    except Exception as e:
        print(f"❌ Error checking dates: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

if __name__ == "__main__":
    check_match_dates()
