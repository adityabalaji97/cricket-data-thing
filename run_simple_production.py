#!/usr/bin/env python3
"""
Simple Production Phase Runner

This script runs each phase directly without complex inheritance to avoid
the method resolution issues we're seeing.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import argparse
from datetime import datetime

load_dotenv()

def get_production_db_url():
    """Get production database URL from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url

def verify_production_environment():
    """Verify this is intended for production use."""
    environment = os.getenv("ENVIRONMENT", "").lower()
    return environment == "production"

def run_phase_3_simple():
    """Run Phase 3 using environment variable for database."""
    print("🔄 Running Phase 3 with production database...")
    
    # Temporarily set the database URL for the existing script
    db_url = get_production_db_url()
    
    # Create a temporary modified database.py content
    temp_db_content = f'''
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "{db_url}"

engine = create_engine(DATABASE_URL)

def get_database_connection():
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal
'''
    
    # Write temporary database config
    with open('temp_database.py', 'w') as f:
        f.write(temp_db_content)
    
    try:
        # Import with the temporary database config
        sys.path.insert(0, '.')
        
        # Now import the player updater
        import temp_database
        from player_data_updater import PlayerDataUpdater
        
        # Override the database module
        import player_data_updater
        player_data_updater.get_database_connection = temp_database.get_database_connection
        
        # Create and run the updater
        excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
        updater = PlayerDataUpdater(temp_database.DATABASE_URL, excel_path)
        results = updater.update_players()
        
        print(f"✅ Phase 3 completed successfully!")
        print(f"   Total processed: {results['total_processed']}")
        print(f"   Updated existing: {results['updated']}")
        print(f"   New players added: {results['new']}")
        print(f"   Errors: {results['errors']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 3 failed: {e}")
        return False
    finally:
        # Clean up temporary file
        if os.path.exists('temp_database.py'):
            os.remove('temp_database.py')

def run_phase_1_simple():
    """Run Phase 1 using environment variable for database."""
    print("🔄 Running Phase 1 with production database...")
    
    db_url = get_production_db_url()
    
    try:
        from delivery_updater import DeliveryUpdater
        
        # Create updater with production URL
        updater = DeliveryUpdater(db_url)
        results = updater.run_update(batch_size=1000)
        
        print(f"✅ Phase 1 completed successfully!")
        print(f"   Total updated: {results['total_updated']}")
        print(f"   Total errors: {results['total_errors']}")
        print(f"   Batches processed: {results['batch_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 1 failed: {e}")
        return False

def run_phase_2_simple():
    """Run Phase 2 using environment variable for database."""
    print("🔄 Running Phase 2 with production database...")
    
    db_url = get_production_db_url()
    
    try:
        from derived_columns_updater import DerivedColumnsUpdater
        
        # Create updater with production URL
        updater = DerivedColumnsUpdater(db_url)
        results = updater.run_update(batch_size=1000)
        
        print(f"✅ Phase 2 completed successfully!")
        print(f"   Total updated: {results['total_updated']}")
        print(f"   Total errors: {results['total_errors']}")
        print(f"   Batches processed: {results['batch_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 2 failed: {e}")
        return False

def run_granular_simple():
    """Run granular update using environment variable for database."""
    print("🔄 Running granular update with production database...")
    
    db_url = get_production_db_url()
    
    try:
        from update_crease_combo_granular import CreaseComboGranularUpdater
        
        # Create updater with production URL
        updater = CreaseComboGranularUpdater(db_url)
        results = updater.run_granular_update()
        
        print(f"✅ Granular update completed successfully!")
        print(f"   RHB-RHB created: {results['rhb_rhb_created']:,}")
        print(f"   LHB-LHB created: {results['lhb_lhb_created']:,}")
        print(f"   LHB-RHB created: {results['lhb_rhb_created']:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Granular update failed: {e}")
        return False

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Simple production phase runner')
    parser.add_argument('--phase', choices=['3', '1', '2', 'granular', 'all'], required=True)
    parser.add_argument('--confirm', action='store_true')
    
    args = parser.parse_args()
    
    print("SIMPLE PRODUCTION RUNNER")
    print("=" * 50)
    print(f"Started at: {datetime.now().isoformat()}")
    
    if not verify_production_environment():
        print("❌ ENVIRONMENT must be set to 'production'")
        return 1
    
    try:
        db_url = get_production_db_url()
        print(f"🔗 Production DB: {db_url.split('@')[1] if '@' in db_url else 'Unknown'}")
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    # Get confirmation
    if not args.confirm:
        print(f"\n⚠️  Running Phase {args.phase} on PRODUCTION")
        response = input("Type 'CONFIRM' to proceed: ").strip()
        if response != "CONFIRM":
            print("❌ Cancelled")
            return 1
    
    success = True
    
    if args.phase == 'all':
        phases = [
            ("3", run_phase_3_simple),
            ("1", run_phase_1_simple),
            ("2", run_phase_2_simple),
            ("granular", run_granular_simple)
        ]
        
        for phase_name, phase_func in phases:
            print(f"\n{'='*20} PHASE {phase_name} {'='*20}")
            if not phase_func():
                success = False
                break
                
    elif args.phase == '3':
        success = run_phase_3_simple()
    elif args.phase == '1':
        success = run_phase_1_simple()
    elif args.phase == '2':
        success = run_phase_2_simple()
    elif args.phase == 'granular':
        success = run_granular_simple()
    
    print(f"\n{'='*50}")
    print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"Completed at: {datetime.now().isoformat()}")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
