"""
Quick script to check current deliveries table structure
"""
from sqlalchemy import inspect
from database import get_database_connection
from models import Delivery

def check_deliveries_schema():
    """Check current deliveries table structure"""
    try:
        engine, _ = get_database_connection()
        inspector = inspect(engine)
        
        # Get deliveries table columns
        columns = inspector.get_columns('deliveries')
        
        print("Current deliveries table structure:")
        print("=" * 50)
        for col in columns:
            print(f"  {col['name']}: {col['type']} (nullable: {col['nullable']})")
        
        # Check if WPA columns already exist
        column_names = [col['name'] for col in columns]
        wpa_columns = ['wpa_batter', 'wpa_bowler', 'wpa_computed_date']
        
        print("\nWPA Column Status:")
        print("=" * 30)
        for wpa_col in wpa_columns:
            exists = wpa_col in column_names
            print(f"  {wpa_col}: {'EXISTS' if exists else 'MISSING'}")
            
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_deliveries_schema()
