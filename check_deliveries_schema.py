#!/usr/bin/env python3
"""
Check Deliveries Table Schema

This script inspects the current schema of the deliveries table to see
what columns exist and their data types.
"""

from sqlalchemy import create_engine, text, inspect
from database import get_database_connection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_deliveries_schema():
    """Check the current schema of the deliveries table"""
    
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        # Get table info using SQLAlchemy inspector
        inspector = inspect(engine)
        
        # Check if deliveries table exists
        tables = inspector.get_table_names()
        if 'deliveries' not in tables:
            logger.error("❌ deliveries table does not exist!")
            return
        
        logger.info("✅ deliveries table found")
        
        # Get column information
        columns = inspector.get_columns('deliveries')
        
        logger.info(f"\n📋 Deliveries table has {len(columns)} columns:")
        logger.info("="*80)
        
        # Sort columns by name for easier reading
        columns.sort(key=lambda x: x['name'])
        
        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f"DEFAULT: {col['default']}" if col['default'] else ""
            
            logger.info(f"  {col_name:<25} {col_type:<20} {nullable:<10} {default}")
        
        # Check for the specific columns we're looking for
        column_names = {col['name'] for col in columns}
        
        logger.info(f"\n🔍 Checking for enhancement columns:")
        logger.info("="*50)
        
        # Snake_case versions (what enhanced loader expects)
        snake_case_cols = {
            'striker_batter_type': 'striker_batter_type' in column_names,
            'non_striker_batter_type': 'non_striker_batter_type' in column_names,
            'bowler_type': 'bowler_type' in column_names,
            'crease_combo': 'crease_combo' in column_names,
            'ball_direction': 'ball_direction' in column_names
        }
        
        # CamelCase versions (from SQL schema)
        camel_case_cols = {
            'striker_batterType': 'striker_battertype' in column_names,
            'non_striker_batterType': 'non_striker_battertype' in column_names,
            'bowler_type': 'bowler_type' in column_names,  # This one is consistent
            'creaseCombo': 'creasecombo' in column_names,
            'ballDirection': 'balldirection' in column_names
        }
        
        logger.info("Snake_case columns (enhanced loader expects):")
        for col, exists in snake_case_cols.items():
            status = "✅ EXISTS" if exists else "❌ MISSING"
            logger.info(f"  {col:<25} {status}")
        
        logger.info("\nCamelCase columns (from SQL schema):")
        for col, exists in camel_case_cols.items():
            status = "✅ EXISTS" if exists else "❌ MISSING"
            logger.info(f"  {col:<25} {status}")
        
        # Check for any variations or similar columns
        logger.info(f"\n🔍 Looking for similar column names:")
        
        potential_cols = [name for name in column_names if any(keyword in name.lower() for keyword in 
                         ['batter', 'bowler', 'crease', 'ball', 'direction', 'combo', 'type'])]
        
        if potential_cols:
            logger.info("Found these related columns:")
            for col in sorted(potential_cols):
                logger.info(f"  {col}")
        else:
            logger.info("No related columns found")
        
        # Get a sample of data to see what's populated
        logger.info(f"\n📊 Sample data from deliveries table:")
        logger.info("="*50)
        
        sample_query = text("""
            SELECT 
                match_id, innings, over, ball, batter, bowler,
                CASE WHEN EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'deliveries' AND column_name = 'striker_batter_type'
                ) THEN striker_batter_type ELSE 'COLUMN_NOT_EXISTS' END as striker_batter_type_check
            FROM deliveries 
            LIMIT 3
        """)
        
        try:
            result = session.execute(sample_query)
            rows = result.fetchall()
            
            if rows:
                logger.info("Sample rows:")
                for i, row in enumerate(rows, 1):
                    logger.info(f"  Row {i}: match_id={row[0]}, innings={row[1]}, over={row[2]}, "
                              f"ball={row[3]}, batter={row[4][:20]}...")
            else:
                logger.info("No data found in deliveries table")
                
        except Exception as e:
            logger.warning(f"Could not fetch sample data: {e}")
        
        # Count total deliveries
        count_query = text("SELECT COUNT(*) FROM deliveries")
        result = session.execute(count_query)
        total_count = result.scalar()
        
        logger.info(f"\n📈 Total deliveries in database: {total_count:,}")
        
        return {
            'columns': columns,
            'column_names': column_names,
            'snake_case_exists': snake_case_cols,
            'camel_case_exists': camel_case_cols,
            'total_deliveries': total_count
        }
        
    except Exception as e:
        logger.error(f"Error checking schema: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("🏏 Checking deliveries table schema...")
    print("="*60)
    
    try:
        schema_info = check_deliveries_schema()
        print(f"\n✅ Schema check completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
