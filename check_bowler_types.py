from sqlalchemy.sql import text
from database import get_session

# Quick script to check what bowler types exist in the database
def check_bowler_types():
    with get_session() as db:
        # Check deliveries table for bowler_type
        query = text("""
            SELECT DISTINCT bowler_type, COUNT(*) as count
            FROM deliveries 
            WHERE bowler_type IS NOT NULL 
            AND bowler_type != ''
            GROUP BY bowler_type
            ORDER BY count DESC
        """)
        
        print("Bowler types in deliveries table:")
        result = db.execute(query).fetchall()
        for row in result:
            print(f"  {row[0]}: {row[1]} deliveries")
        
        # Check players table for bowler_type
        query2 = text("""
            SELECT DISTINCT bowler_type, COUNT(*) as count
            FROM players 
            WHERE bowler_type IS NOT NULL 
            AND bowler_type != ''
            GROUP BY bowler_type
            ORDER BY count DESC
        """)
        
        print("\nBowler types in players table:")
        result2 = db.execute(query2).fetchall()
        for row in result2:
            print(f"  {row[0]}: {row[1]} players")

if __name__ == "__main__":
    check_bowler_types()
