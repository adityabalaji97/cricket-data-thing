#!/usr/bin/env python3
"""
Production-Safe Master Execution Script for Left-Right Analysis

This script runs the left-right analysis implementation on production databases
using environment variables for database connection and includes safety checks.

Environment Variables Required:
    DATABASE_URL - Production database connection string
    ENVIRONMENT - Set to 'production' for production runs

Usage:
    export DATABASE_URL="postgresql://user:pass@host:port/dbname"
    export ENVIRONMENT="production"
    python run_production_phases.py --phase=all --confirm
"""

import sys
import os
import argparse
import time
from datetime import datetime
from typing import Optional

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Import our updater classes but we'll modify them to use env variables
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def get_production_db_url() -> str:
    """Get production database URL from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required for production runs")
    
    # Handle Heroku postgres:// URLs
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return db_url


def verify_production_environment() -> bool:
    """Verify this is intended for production use."""
    environment = os.getenv("ENVIRONMENT", "").lower()
    
    if environment != "production":
        print("❌ ENVIRONMENT variable must be set to 'production' for this script")
        print("   This is a safety check to prevent accidental production runs")
        return False
    
    return True


def check_production_database_connection(db_url: str) -> bool:
    """Test connection to production database."""
    try:
        print("🔗 Testing production database connection...")
        engine = create_engine(db_url)
        
        with engine.connect() as connection:
            # Test basic connectivity
            result = connection.execute(text("SELECT 1"))
            result.scalar()
            
            # Check if this looks like a production database
            tables_result = connection.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name IN ('deliveries', 'matches', 'players')
            """))
            table_count = tables_result.scalar()
            
            if table_count < 3:
                print("❌ Database doesn't appear to have required tables")
                return False
            
            # Check data volume (production should have significant data)
            deliveries_count = connection.execute(text("SELECT COUNT(*) FROM deliveries")).scalar()
            matches_count = connection.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            
            print(f"📊 Production database stats:")
            print(f"   • Deliveries: {deliveries_count:,}")
            print(f"   • Matches: {matches_count:,}")
            
            if deliveries_count < 10000:  # Production should have more than 10k deliveries
                print("⚠️  Warning: Low delivery count for production database")
                return False
            
            print("✅ Production database connection verified")
            return True
            
    except Exception as e:
        print(f"❌ Production database connection failed: {e}")
        return False


def get_user_confirmation(operation: str) -> bool:
    """Get explicit user confirmation for production operations."""
    print(f"\n⚠️  PRODUCTION SAFETY CHECK ⚠️")
    print(f"You are about to run: {operation}")
    print(f"This will modify data in the PRODUCTION database")
    print(f"Database: {get_production_db_url().split('@')[1] if '@' in get_production_db_url() else 'Unknown'}")
    
    response = input("\nType 'CONFIRM PRODUCTION' to proceed: ").strip()
    
    if response == "CONFIRM PRODUCTION":
        print("✅ Production operation confirmed")
        return True
    else:
        print("❌ Production operation cancelled")
        return False


def run_production_player_update(db_url: str) -> bool:
    """Run Phase 3: Update player data from Excel on production."""
    print("\n" + "="*60)
    print("PRODUCTION PHASE 3: Update Player Data from Excel")
    print("="*60)
    
    try:
        # Import here to avoid early DB connection
        from player_data_updater import PlayerDataUpdater
        
        # Use production Excel file path (you may need to adjust this)
        excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
        
        if not os.path.exists(excel_path):
            print(f"❌ Excel file not found: {excel_path}")
            return False
        
        # Create updater with production DB URL
        class ProductionPlayerUpdater(PlayerDataUpdater):
            def __init__(self, excel_path):
                from sqlalchemy.orm import sessionmaker
                import logging
                self.db_url = db_url
                self.excel_path = excel_path
                self.engine = create_engine(db_url)
                Session = sessionmaker(bind=self.engine)
                self.session = Session()
                
                # Set up logging
                logging.basicConfig(level=logging.INFO)
                self.logger = logging.getLogger(__name__)
                
                # Initialize player cache
                self.player_cache = {}
                self.load_player_cache()
        
        updater = ProductionPlayerUpdater(excel_path)
        results = updater.update_players()
        
        print(f"✅ Production Phase 3 completed successfully!")
        print(f"   Total processed: {results['total_processed']}")
        print(f"   Updated existing: {results['updated']}")
        print(f"   New players added: {results['new']}")
        print(f"   Errors: {results['errors']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Production Phase 3 failed: {e}")
        return False


def run_production_delivery_update(db_url: str) -> bool:
    """Run Phase 1: Add base columns to deliveries table on production."""
    print("\n" + "="*60)
    print("PRODUCTION PHASE 1: Add Base Columns to Deliveries Table")
    print("="*60)
    
    try:
        # Import and modify the delivery updater
        from delivery_updater import DeliveryUpdater
        
        class ProductionDeliveryUpdater(DeliveryUpdater):
            def __init__(self):
                from sqlalchemy.orm import sessionmaker
                import logging
                self.db_url = db_url
                self.engine = create_engine(db_url)
                Session = sessionmaker(bind=self.engine)
                self.session = Session()
                
                logging.basicConfig(level=logging.INFO)
                self.logger = logging.getLogger(__name__)
                
                self.player_cache = {}
                self.load_player_cache()
        
        updater = ProductionDeliveryUpdater()
        results = updater.run_update(batch_size=1000)
        
        print(f"✅ Production Phase 1 completed successfully!")
        print(f"   Total updated: {results['total_updated']}")
        print(f"   Total errors: {results['total_errors']}")
        print(f"   Batches processed: {results['batch_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Production Phase 1 failed: {e}")
        return False


def run_production_derived_update(db_url: str) -> bool:
    """Run Phase 2: Add derived columns to deliveries table on production."""
    print("\n" + "="*60)
    print("PRODUCTION PHASE 2: Add Derived Columns to Deliveries Table")
    print("="*60)
    
    try:
        from derived_columns_updater import DerivedColumnsUpdater
        
        class ProductionDerivedUpdater(DerivedColumnsUpdater):
            def __init__(self):
                from sqlalchemy.orm import sessionmaker
                import logging
                self.db_url = db_url
                self.engine = create_engine(db_url)
                Session = sessionmaker(bind=self.engine)
                self.session = Session()
                
                logging.basicConfig(level=logging.INFO)
                self.logger = logging.getLogger(__name__)
                
                # Define bowler type mappings for ball direction logic
                self.into_batter_bowler_types = {
                    'RHB': ['RO', 'LC'],
                    'LHB': ['RL', 'LO']
                }
                
                self.away_from_batter_bowler_types = {
                    'LHB': ['RO', 'LC'],
                    'RHB': ['RL', 'LO']
                }
        
        updater = ProductionDerivedUpdater()
        results = updater.run_update(batch_size=1000)
        
        print(f"✅ Production Phase 2 completed successfully!")
        print(f"   Total updated: {results['total_updated']}")
        print(f"   Total errors: {results['total_errors']}")
        print(f"   Batches processed: {results['batch_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Production Phase 2 failed: {e}")
        return False


def run_production_granular_update(db_url: str) -> bool:
    """Run granular crease combo update on production."""
    print("\n" + "="*60)
    print("PRODUCTION: Granular Crease Combo Update")
    print("="*60)
    
    try:
        from update_crease_combo_granular import CreaseComboGranularUpdater
        
        class ProductionGranularUpdater(CreaseComboGranularUpdater):
            def __init__(self):
                from sqlalchemy.orm import sessionmaker
                import logging
                self.db_url = db_url
                self.engine = create_engine(db_url)
                Session = sessionmaker(bind=self.engine)
                self.session = Session()
                
                logging.basicConfig(level=logging.INFO)
                self.logger = logging.getLogger(__name__)
        
        updater = ProductionGranularUpdater()
        results = updater.run_granular_update()
        
        print(f"✅ Production granular update completed successfully!")
        print(f"   RHB-RHB created: {results['rhb_rhb_created']:,}")
        print(f"   LHB-LHB created: {results['lhb_lhb_created']:,}")
        print(f"   LHB-RHB created: {results['lhb_rhb_created']:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Production granular update failed: {e}")
        return False


def main():
    """Main execution function for production runs."""
    parser = argparse.ArgumentParser(description='Run left-right analysis on production database')
    parser.add_argument('--phase', choices=['all', '3', '1', '2', 'granular'], required=True,
                       help='Which phase to run')
    parser.add_argument('--confirm', action='store_true', 
                       help='Skip manual confirmation (use with caution)')
    
    args = parser.parse_args()
    
    print("PRODUCTION LEFT-RIGHT ANALYSIS IMPLEMENTATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Running phase(s): {args.phase}")
    
    # Safety checks
    if not verify_production_environment():
        return 1
    
    try:
        db_url = get_production_db_url()
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    if not check_production_database_connection(db_url):
        return 1
    
    # Get user confirmation unless --confirm flag is used
    if not args.confirm:
        operation_desc = f"Phase {args.phase} left-right analysis update"
        if not get_user_confirmation(operation_desc):
            return 1
    
    start_time = time.time()
    success = True
    
    # Run phases based on argument
    if args.phase == 'all':
        phases = [
            ("Phase 3", lambda: run_production_player_update(db_url)),
            ("Phase 1", lambda: run_production_delivery_update(db_url)),
            ("Phase 2", lambda: run_production_derived_update(db_url)),
            ("Granular Update", lambda: run_production_granular_update(db_url))
        ]
        
        for phase_name, phase_func in phases:
            if not phase_func():
                print(f"\n💥 {phase_name} failed. Stopping execution.")
                success = False
                break
                
    elif args.phase == '3':
        success = run_production_player_update(db_url)
    elif args.phase == '1':
        success = run_production_delivery_update(db_url)
    elif args.phase == '2':
        success = run_production_derived_update(db_url)
    elif args.phase == 'granular':
        success = run_production_granular_update(db_url)
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "="*80)
    print("PRODUCTION EXECUTION SUMMARY")
    print("="*80)
    print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Completed at: {datetime.now().isoformat()}")
    
    if success:
        print("\n🎉 Production update completed successfully!")
        print("Your production deliveries table now includes granular left-right analysis!")
    else:
        print("\n💥 Production update failed. Check error messages above.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
