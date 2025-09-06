from sqlalchemy import text
from database import get_session
from tabulate import tabulate

def verify_team_level_data():
    # Create a database session
    session_gen = get_session()
    session = next(session_gen)

    try:
        # Query to find the first 100 records where batting_team is the same as striker
        query = text("""
            SELECT *
            FROM batting_stats
            WHERE batting_team = striker
            LIMIT 100
        """)
        
        result = session.execute(query).fetchall()
        
        # Prepare data for tabulation
        if result:
            headers = result[0].keys()  # Get column names from the first row
            table_data = [row for row in result]
            
            # Display the data in a table format
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
        else:
            print("No records found where batting_team is the same as striker.")
    
    finally:
        session.close()

if __name__ == "__main__":
    verify_team_level_data()