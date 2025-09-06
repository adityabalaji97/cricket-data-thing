#!/usr/bin/env python3
"""
Production-Safe Delivery Updater - OPTIMIZED

This version uses bulk SQL operations instead of individual updates
to avoid the 1.6M individual UPDATE statements disaster.
"""

import sys
import os
from sqlalchemy import create_engine, text
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

def run_phase_1_bulk():
    """Run Phase 1 using efficient bulk SQL operations."""
    print("🔄 Running Phase 1 with BULK SQL operations...")
    
    db_url = get_production_db_url()
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as connection:
            print("📊 Checking current state...")
            
            # Check how many deliveries need updating
            count_result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM deliveries 
                WHERE striker_batter_type IS NULL
            """))
            total_to_update = count_result.scalar()
            print(f"Found {total_to_update:,} deliveries to update")
            
            if total_to_update == 0:
                print("✅ No deliveries need updating")
                return True
            
            print("🚀 Running BULK updates...")
            start_time = datetime.now()
            
            # BULK UPDATE 1: striker_batter_type
            print("   Updating striker_batter_type...")
            striker_result = connection.execute(text("""
                UPDATE deliveries 
                SET striker_batter_type = p.batter_type
                FROM players p 
                WHERE deliveries.batter = p.name 
                AND deliveries.striker_batter_type IS NULL
                AND p.batter_type IS NOT NULL
            """))
            striker_updated = striker_result.rowcount
            print(f"   ✅ Updated {striker_updated:,} striker types")
            
            # BULK UPDATE 2: non_striker_batter_type  
            print("   Updating non_striker_batter_type...")
            non_striker_result = connection.execute(text("""
                UPDATE deliveries 
                SET non_striker_batter_type = p.batter_type
                FROM players p 
                WHERE deliveries.non_striker = p.name 
                AND deliveries.non_striker_batter_type IS NULL
                AND p.batter_type IS NOT NULL
            """))
            non_striker_updated = non_striker_result.rowcount
            print(f"   ✅ Updated {non_striker_updated:,} non-striker types")
            
            # BULK UPDATE 3: bowler_type
            print("   Updating bowler_type...")
            bowler_result = connection.execute(text("""
                UPDATE deliveries 
                SET bowler_type = p.bowler_type
                FROM players p 
                WHERE deliveries.bowler = p.name 
                AND deliveries.bowler_type IS NULL
                AND p.bowler_type IS NOT NULL
            """))
            bowler_updated = bowler_result.rowcount
            print(f"   ✅ Updated {bowler_updated:,} bowler types")
            
            connection.commit()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ Phase 1 completed in {duration:.1f} seconds!")
            print(f"   Striker types: {striker_updated:,}")
            print(f"   Non-striker types: {non_striker_updated:,}")
            print(f"   Bowler types: {bowler_updated:,}")
            
            return True
            
    except Exception as e:
        print(f"❌ Phase 1 failed: {e}")
        return False

def run_phase_2_bulk():
    """Run Phase 2 using efficient bulk SQL operations."""
    print("🔄 Running Phase 2 with BULK SQL operations...")
    
    db_url = get_production_db_url()
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as connection:
            print("📊 Checking current state...")
            
            # Check how many deliveries need derived column updates
            count_result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM deliveries 
                WHERE crease_combo IS NULL 
                AND striker_batter_type IS NOT NULL 
                AND non_striker_batter_type IS NOT NULL
            """))
            total_to_update = count_result.scalar()
            print(f"Found {total_to_update:,} deliveries needing derived updates")
            
            if total_to_update == 0:
                print("✅ No deliveries need derived updates")
                return True
            
            print("🚀 Running BULK derived column updates...")
            start_time = datetime.now()
            
            # BULK UPDATE 1: rhb_rhb combinations
            print("   Creating rhb_rhb combinations...")
            rhb_rhb_result = connection.execute(text("""
                UPDATE deliveries 
                SET crease_combo = 'rhb_rhb'
                WHERE crease_combo IS NULL
                AND striker_batter_type = 'RHB' 
                AND non_striker_batter_type = 'RHB'
            """))
            rhb_rhb_count = rhb_rhb_result.rowcount
            print(f"   ✅ Created {rhb_rhb_count:,} rhb_rhb combinations")
            
            # BULK UPDATE 2: lhb_lhb combinations
            print("   Creating lhb_lhb combinations...")
            lhb_lhb_result = connection.execute(text("""
                UPDATE deliveries 
                SET crease_combo = 'lhb_lhb'
                WHERE crease_combo IS NULL
                AND striker_batter_type = 'LHB' 
                AND non_striker_batter_type = 'LHB'
            """))
            lhb_lhb_count = lhb_lhb_result.rowcount
            print(f"   ✅ Created {lhb_lhb_count:,} lhb_lhb combinations")
            
            # BULK UPDATE 3: lhb_rhb combinations
            print("   Creating lhb_rhb combinations...")
            lhb_rhb_result = connection.execute(text("""
                UPDATE deliveries 
                SET crease_combo = 'lhb_rhb'
                WHERE crease_combo IS NULL
                AND (
                    (striker_batter_type = 'LHB' AND non_striker_batter_type = 'RHB') OR
                    (striker_batter_type = 'RHB' AND non_striker_batter_type = 'LHB')
                )
            """))
            lhb_rhb_count = lhb_rhb_result.rowcount
            print(f"   ✅ Created {lhb_rhb_count:,} lhb_rhb combinations")
            
            # BULK UPDATE 4: unknown crease combos
            print("   Setting unknown crease combos...")
            unknown_crease_result = connection.execute(text("""
                UPDATE deliveries 
                SET crease_combo = 'unknown'
                WHERE crease_combo IS NULL
            """))
            unknown_crease_count = unknown_crease_result.rowcount
            print(f"   ✅ Set {unknown_crease_count:,} unknown crease combos")
            
            # BULK UPDATE 5: intoBatter ball direction
            print("   Setting intoBatter ball directions...")
            into_batter_result = connection.execute(text("""
                UPDATE deliveries 
                SET ball_direction = 'intoBatter'
                WHERE ball_direction IS NULL
                AND (
                    (striker_batter_type = 'RHB' AND bowler_type IN ('RO', 'LC')) OR
                    (striker_batter_type = 'LHB' AND bowler_type IN ('RL', 'LO'))
                )
            """))
            into_batter_count = into_batter_result.rowcount
            print(f"   ✅ Set {into_batter_count:,} intoBatter directions")
            
            # BULK UPDATE 6: awayFromBatter ball direction
            print("   Setting awayFromBatter ball directions...")
            away_batter_result = connection.execute(text("""
                UPDATE deliveries 
                SET ball_direction = 'awayFromBatter'
                WHERE ball_direction IS NULL
                AND (
                    (striker_batter_type = 'LHB' AND bowler_type IN ('RO', 'LC')) OR
                    (striker_batter_type = 'RHB' AND bowler_type IN ('RL', 'LO'))
                )
            """))
            away_batter_count = away_batter_result.rowcount
            print(f"   ✅ Set {away_batter_count:,} awayFromBatter directions")
            
            # BULK UPDATE 7: unknown ball directions
            print("   Setting unknown ball directions...")
            unknown_direction_result = connection.execute(text("""
                UPDATE deliveries 
                SET ball_direction = 'unknown'
                WHERE ball_direction IS NULL
            """))
            unknown_direction_count = unknown_direction_result.rowcount
            print(f"   ✅ Set {unknown_direction_count:,} unknown ball directions")
            
            connection.commit()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ Phase 2 completed in {duration:.1f} seconds!")
            print(f"   rhb_rhb: {rhb_rhb_count:,}")
            print(f"   lhb_lhb: {lhb_lhb_count:,}")
            print(f"   lhb_rhb: {lhb_rhb_count:,}")
            print(f"   unknown crease: {unknown_crease_count:,}")
            print(f"   intoBatter: {into_batter_count:,}")
            print(f"   awayFromBatter: {away_batter_count:,}")
            print(f"   unknown direction: {unknown_direction_count:,}")
            
            return True
            
    except Exception as e:
        print(f"❌ Phase 2 failed: {e}")
        return False

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='BULK production phase runner')
    parser.add_argument('--phase', choices=['1', '2', 'all'], required=True)
    parser.add_argument('--confirm', action='store_true')
    
    args = parser.parse_args()
    
    print("BULK PRODUCTION PHASE RUNNER")
    print("=" * 50)
    
    if os.getenv("ENVIRONMENT", "").lower() != "production":
        print("❌ ENVIRONMENT must be set to 'production'")
        return 1
    
    try:
        db_url = get_production_db_url()
        print(f"🔗 Production DB: {db_url.split('@')[1] if '@' in db_url else 'Unknown'}")
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    if not args.confirm:
        print(f"\n⚠️  Running BULK Phase {args.phase} on PRODUCTION")
        print("This will use efficient SQL JOINs instead of 1.6M individual updates!")
        response = input("Type 'CONFIRM' to proceed: ").strip()
        if response != "CONFIRM":
            print("❌ Cancelled")
            return 1
    
    success = True
    total_start = datetime.now()
    
    if args.phase == 'all':
        print("\n" + "="*20 + " PHASE 1 " + "="*20)
        success = run_phase_1_bulk()
        if success:
            print("\n" + "="*20 + " PHASE 2 " + "="*20)
            success = run_phase_2_bulk()
    elif args.phase == '1':
        success = run_phase_1_bulk()
    elif args.phase == '2':
        success = run_phase_2_bulk()
    
    total_end = datetime.now()
    total_duration = (total_end - total_start).total_seconds()
    
    print(f"\n{'='*50}")
    print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"Total time: {total_duration:.1f} seconds")
    print("🚀 BULK operations completed!")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
