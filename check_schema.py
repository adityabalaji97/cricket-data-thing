#!/usr/bin/env python3
"""
Check deliveries table schema to understand what columns exist
"""

from sqlalchemy import text, inspect
from sqlalchemy.orm import sessionmaker
from database import get_database_connection

def check_deliveries_schema():
    """Check the current schema of the deliveries table"""
    
    try:
        # Get database connection
        engine, SessionLocal = get_database_connection()
        session = SessionLocal()
        
        print("✓ Database connection successful")
        
        # Get table info using SQLAlchemy inspector
        inspector = inspect(engine)
        
        # Check if deliveries table exists
        tables = inspector.get_table_names()
        if 'deliveries' not in tables:
            print("✗ deliveries table does not exist!")
            return False
        
        print("✓ deliveries table found")
        
        # Get column information
        columns = inspector.get_columns('deliveries')
        
        print(f"\n📋 Deliveries table has {len(columns)} columns:")
        print("="*70)
        
        # Sort columns by name for easier reading
        columns.sort(key=lambda x: x['name'])
        
        column_names = []
        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            
            print(f"  {col_name:<30} {col_type:<20} {nullable}")
            column_names.append(col_name)
        
        # Check for the enhancement columns we're looking for
        print(f"\n🔍 Checking for enhancement columns:")
        print("="*50)
        
        # Columns that enhanced loader expects (snake_case)
        expected_cols = [
            'striker_batter_type',
            'non_striker_batter_type', 
            'bowler_type',
            'crease_combo',
            'ball_direction'
        ]
        
        # Columns from SQL schema (camelCase variations)
        sql_schema_cols = [
            'striker_battertype',
            'non_striker_battertype',
            'creasecombo', 
            'balldirection'
        ]
        
        print("Expected columns (snake_case):")
        for col in expected_cols:
            exists = col in column_names
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"  {col:<30} {status}")
        
        print("\nSQL schema columns (camelCase):")
        for col in sql_schema_cols:
            exists = col in column_names
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"  {col:<30} {status}")
        
        # Look for any similar columns
        print(f"\n🔍 Related columns found:")
        related_cols = [name for name in column_names if any(keyword in name.lower() for keyword in 
                       ['batter', 'bowler', 'crease', 'ball', 'direction', 'combo', 'type'])]
        
        if related_cols:
            for col in sorted(related_cols):
                print(f"  {col}")
        else:
            print("  No related columns found")
        
        # Count total deliveries
        count_result = session.execute(text("SELECT COUNT(*) FROM deliveries"))
        total_count = count_result.scalar()
        
        print(f"\n📈 Total deliveries in database: {total_count:,}")
        
        session.close()
        return {
            'column_names': column_names,
            'total_deliveries': total_count,
            'has_enhancement_cols': any(col in column_names for col in expected_cols),
            'has_sql_schema_cols': any(col in column_names for col in sql_schema_cols)
        }
        
    except Exception as e:
        print(f"✗ Error checking schema: {e}")
        return False

def main():
    """Main function"""
    print("🏏 Checking deliveries table schema...")
    print("="*60)
    
    result = check_deliveries_schema()
    
    if result:
        print(f"\n✅ Schema check completed!")
        if result['has_enhancement_cols']:
            print("✓ Enhancement columns found (snake_case)")
        elif result['has_sql_schema_cols']:
            print("⚠️  SQL schema columns found (camelCase) - may need model update")
        else:
            print("❌ No enhancement columns found - need to add them")
    else:
        print(f"\n❌ Schema check failed!")
    
    return result

if __name__ == "__main__":
    main()
