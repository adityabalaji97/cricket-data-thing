#!/usr/bin/env python3
"""
Complete Production Setup Script

This script handles both schema migrations and data population for production.
It will create the required columns if they don't exist, then populate the data.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

def get_production_db_url():
    """Get production database URL from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url

def run_schema_migrations(db_url: str) -> bool:
    """Run all required schema migrations."""
    print("🔧 Running production schema migrations...")
    
    migrations = [
        # Phase 1 columns
        """
        ALTER TABLE deliveries 
        ADD COLUMN IF NOT EXISTS striker_batter_type VARCHAR(10),
        ADD COLUMN IF NOT EXISTS non_striker_batter_type VARCHAR(10),
        ADD COLUMN IF NOT EXISTS bowler_type VARCHAR(10);
        """,
        
        # Phase 2 columns  
        """
        ALTER TABLE deliveries 
        ADD COLUMN IF NOT EXISTS crease_combo VARCHAR(20),
        ADD COLUMN IF NOT EXISTS ball_direction VARCHAR(20);
        """,
        
        # Indexes for performance
        """
        CREATE INDEX IF NOT EXISTS idx_deliveries_striker_batter_type ON deliveries(striker_batter_type);
        CREATE INDEX IF NOT EXISTS idx_deliveries_bowler_type ON deliveries(bowler_type);
        CREATE INDEX IF NOT EXISTS idx_deliveries_crease_combo ON deliveries(crease_combo);
        CREATE INDEX IF NOT EXISTS idx_deliveries_ball_direction ON deliveries(ball_direction);
        CREATE INDEX IF NOT EXISTS idx_deliveries_batter_bowler_types ON deliveries(striker_batter_type, non_striker_batter_type, bowler_type);
        CREATE INDEX IF NOT EXISTS idx_deliveries_left_right_analysis ON deliveries(crease_combo, ball_direction, striker_batter_type, bowler_type);
        """,
        
        # Comments
        """
        COMMENT ON COLUMN deliveries.striker_batter_type IS 'Batter type (LHB/RHB) for striker from players table';
        COMMENT ON COLUMN deliveries.non_striker_batter_type IS 'Batter type (LHB/RHB) for non-striker from players table';
        COMMENT ON COLUMN deliveries.bowler_type IS 'Bowler type (LO/LM/RL/RM/RO/etc) from players table';
        COMMENT ON COLUMN deliveries.crease_combo IS 'Granular batter combination at crease: rhb_rhb, lhb_lhb, lhb_rhb, or unknown';
        COMMENT ON COLUMN deliveries.ball_direction IS 'Ball direction relative to striker: intoBatter, awayFromBatter, or unknown';
        """
    ]
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            for i, migration in enumerate(migrations, 1):
                print(f"   Running migration {i}/{len(migrations)}...")
                connection.execute(text(migration))
                connection.commit()
        
        print("✅ Schema migrations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Schema migration failed: {e}")
        return False

def main():
    """Main execution function."""
    print("PRODUCTION COMPLETE SETUP")
    print("=" * 50)
    
    # Verify environment
    environment = os.getenv("ENVIRONMENT", "").lower()
    if environment != "production":
        print("❌ ENVIRONMENT variable must be set to 'production'")
        return 1
    
    try:
        db_url = get_production_db_url()
        print(f"🔗 Connected to: {db_url.split('@')[1] if '@' in db_url else 'Unknown'}")
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    # Get confirmation
    print("\n⚠️  This will create columns and populate data in PRODUCTION")
    response = input("Type 'CONFIRM PRODUCTION SETUP' to proceed: ").strip()
    
    if response != "CONFIRM PRODUCTION SETUP":
        print("❌ Setup cancelled")
        return 1
    
    # Step 1: Run schema migrations
    if not run_schema_migrations(db_url):
        return 1
    
    # Step 2: Run all phases
    print("\n🚀 Running production phases...")
    
    # Import and run the production script
    os.system("python run_production_phases.py --phase=all --confirm")
    
    print("\n✅ Production setup completed!")
    print("Run 'python verify_production.py --ipl' to check results")
    
    return 0

if __name__ == "__main__":
    exit(main())
