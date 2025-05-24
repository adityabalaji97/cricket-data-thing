#!/usr/bin/env python3
"""
Cricket Database Export/Import Script

This script helps collaborators set up a local copy of the production database
for development and testing purposes.

Usage:
    # Export from Heroku (run by project maintainer)
    python db_sync.py export

    # Import to local database (run by collaborators)  
    python db_sync.py import

    # Update local database with latest data
    python db_sync.py update
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base
import argparse

def get_heroku_database_url():
    """Get the Heroku database URL"""
    try:
        result = subprocess.run(
            ['heroku', 'config:get', 'DATABASE_URL', '-a', 'cricket-data-thing'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("❌ Error: Could not get Heroku DATABASE_URL")
        print("Make sure you have Heroku CLI installed and are logged in")
        sys.exit(1)

def get_local_database_url():
    """Get local database URL from environment or default"""
    from dotenv import load_dotenv
    load_dotenv()
    
    local_url = os.getenv("LOCAL_DATABASE_URL", "postgresql://postgres:password@localhost:5432/cricket_db_local")
    return local_url

def export_data():
    """Export data from Heroku database to JSON files"""
    print("🔄 Exporting data from Heroku database...")
    
    heroku_url = get_heroku_database_url()
    engine = create_engine(heroku_url)
    
    # Create exports directory
    export_dir = Path("data_exports")
    export_dir.mkdir(exist_ok=True)
    
    # Get all table names
    with engine.connect() as conn:
        tables_result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """))
        tables = [row[0] for row in tables_result]
    
    exported_tables = {}
    
    for table in tables:
        print(f"📦 Exporting table: {table}")
        
        with engine.connect() as conn:
            # Get table data
            result = conn.execute(text(f"SELECT * FROM {table}"))
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to list of dictionaries
            table_data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Handle datetime serialization
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[col] = value
                table_data.append(row_dict)
            
            exported_tables[table] = {
                'columns': list(columns),
                'data': table_data,
                'row_count': len(table_data)
            }
    
    # Save to JSON file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = export_dir / f"cricket_db_export_{timestamp}.json"
    
    export_data = {
        'export_timestamp': datetime.now().isoformat(),
        'source_database': 'heroku',
        'tables': exported_tables
    }
    
    with open(export_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    # Create latest symlink
    latest_file = export_dir / "latest_export.json"
    if latest_file.exists():
        latest_file.unlink()
    latest_file.symlink_to(export_file.name)
    
    print(f"✅ Export complete: {export_file}")
    print(f"📊 Exported {len(exported_tables)} tables")
    
    # Create summary
    print("\n📋 Export Summary:")
    for table, info in exported_tables.items():
        print(f"   {table}: {info['row_count']} rows")
    
    return export_file

def import_data(export_file=None):
    """Import data from JSON file to local database"""
    if export_file is None:
        export_file = Path("data_exports/latest_export.json")
    
    if not export_file.exists():
        print(f"❌ Export file not found: {export_file}")
        print("Run 'python db_sync.py export' first, or specify a file")
        sys.exit(1)
    
    print(f"🔄 Importing data from: {export_file}")
    
    # Load export data
    with open(export_file, 'r') as f:
        export_data = json.load(f)
    
    local_url = get_local_database_url()
    print(f"📍 Target database: {local_url.split('@')[1] if '@' in local_url else 'localhost'}")
    
    # Create local database engine
    engine = create_engine(local_url)
    
    # Create all tables
    print("🏗️  Creating database schema...")
    Base.metadata.create_all(bind=engine)
    
    # Import data
    tables_data = export_data['tables']
    
    with engine.connect() as conn:
        for table_name, table_info in tables_data.items():
            print(f"📥 Importing table: {table_name} ({table_info['row_count']} rows)")
            
            # Clear existing data
            conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            
            # Import new data
            if table_info['data']:
                columns = table_info['columns']
                placeholders = ', '.join([f':{col}' for col in columns])
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                
                conn.execute(text(insert_sql), table_info['data'])
        
        conn.commit()
    
    print("✅ Import complete!")
    print(f"📅 Data from: {export_data['export_timestamp']}")

def setup_local_env():
    """Help collaborators set up their local environment"""
    print("🔧 Setting up local environment for collaboration...")
    
    # Check if .env exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
    else:
        print("📝 Creating .env file from template...")
        
        env_content = f"""# Local Development Database
LOCAL_DATABASE_URL=postgresql://postgres:password@localhost:5432/cricket_db_local
DATABASE_URL=postgresql://postgres:password@localhost:5432/cricket_db_local

# Read-only mode (can be set to false for local development)
READ_ONLY_MODE=false

# Export timestamp (automatically updated)
LAST_DATA_SYNC={datetime.now().isoformat()}
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print("✅ Created .env file")
    
    print("""
🎯 Next steps for collaborators:

1. **Install PostgreSQL locally:**
   - macOS: brew install postgresql
   - Windows: Download from postgresql.org
   - Linux: sudo apt-get install postgresql

2. **Create local database:**
   createdb cricket_db_local

3. **Get latest data export:**
   Ask the project maintainer for the latest data export file

4. **Import the data:**
   python db_sync.py import path/to/export_file.json

5. **Start developing:**
   uvicorn main:app --reload

""")

def main():
    parser = argparse.ArgumentParser(description='Cricket Database Sync Tool')
    parser.add_argument('action', choices=['export', 'import', 'setup'], 
                       help='Action to perform')
    parser.add_argument('--file', '-f', type=Path,
                       help='Export file to import (for import action)')
    
    args = parser.parse_args()
    
    if args.action == 'export':
        export_data()
    elif args.action == 'import':
        import_data(args.file)
    elif args.action == 'setup':
        setup_local_env()

if __name__ == "__main__":
    main()
