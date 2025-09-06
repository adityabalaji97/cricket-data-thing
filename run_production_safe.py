#!/usr/bin/env python3
"""
Production-Safe Delivery Updater

This version only uses columns that exist in production and avoids
the ORM model to prevent schema conflicts.
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

def run_phase_1_safe():
    """Run Phase 1 using only production-safe queries."""
    print("🔄 Running Phase 1 with production-safe queries...")
    
    db_url = get_production_db_url()
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as connection:
            # First, load all players into memory
            print("📋 Loading player data...")
            player_result = connection.execute(text("""
                SELECT name, batter_type, bowler_type 
                FROM players 
                WHERE batter_type IS NOT NULL OR bowler_type IS NOT NULL
            """))
            
            player_cache = {}
            for row in player_result:
                player_cache[row[0]] = {
                    'batter_type': row[1],
                    'bowler_type': row[2]
                }
            
            print(f"Loaded {len(player_cache)} players with type info")
            
            # Count deliveries that need updating
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
            
            # Process in batches
            batch_size = 1000
            total_updated = 0
            
            for offset in range(0, total_to_update, batch_size):
                # Get batch of deliveries
                batch_result = connection.execute(text("""
                    SELECT id, batter, non_striker, bowler
                    FROM deliveries 
                    WHERE striker_batter_type IS NULL
                    LIMIT :limit OFFSET :offset
                """), {"limit": batch_size, "offset": offset})
                
                batch_deliveries = batch_result.fetchall()
                
                if not batch_deliveries:
                    break
                
                # Update each delivery in the batch
                batch_updates = []
                for delivery in batch_deliveries:
                    delivery_id = delivery[0]
                    striker = delivery[1]
                    non_striker = delivery[2]
                    bowler = delivery[3]
                    
                    striker_type = player_cache.get(striker, {}).get('batter_type')
                    non_striker_type = player_cache.get(non_striker, {}).get('batter_type')
                    bowler_type = player_cache.get(bowler, {}).get('bowler_type')
                    
                    batch_updates.append({
                        'id': delivery_id,
                        'striker_batter_type': striker_type,
                        'non_striker_batter_type': non_striker_type,
                        'bowler_type': bowler_type
                    })
                
                # Execute batch update
                if batch_updates:
                    for update in batch_updates:
                        connection.execute(text("""
                            UPDATE deliveries 
                            SET striker_batter_type = :striker_type,
                                non_striker_batter_type = :non_striker_type,
                                bowler_type = :bowler_type
                            WHERE id = :delivery_id
                        """), {
                            'striker_type': update['striker_batter_type'],
                            'non_striker_type': update['non_striker_batter_type'],
                            'bowler_type': update['bowler_type'],
                            'delivery_id': update['id']
                        })
                    
                    connection.commit()
                    total_updated += len(batch_updates)
                
                # Progress update
                progress = (total_updated / total_to_update) * 100
                print(f"   Updated {total_updated:,}/{total_to_update:,} deliveries ({progress:.1f}%)")
            
            print(f"✅ Phase 1 completed successfully!")
            print(f"   Total updated: {total_updated:,}")
            
            return True
            
    except Exception as e:
        print(f"❌ Phase 1 failed: {e}")
        return False

def run_phase_2_safe():
    """Run Phase 2 using only production-safe queries."""
    print("🔄 Running Phase 2 with production-safe queries...")
    
    db_url = get_production_db_url()
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as connection:
            # Count deliveries that need derived column updates
            count_result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM deliveries 
                WHERE crease_combo IS NULL 
                AND striker_batter_type IS NOT NULL 
                AND non_striker_batter_type IS NOT NULL
            """))
            total_to_update = count_result.scalar()
            print(f"Found {total_to_update:,} deliveries needing derived column updates")
            
            if total_to_update == 0:
                print("✅ No deliveries need derived column updates")
                return True
            
            # Process in batches
            batch_size = 1000
            total_updated = 0
            
            for offset in range(0, total_to_update, batch_size):
                # Get batch of deliveries
                batch_result = connection.execute(text("""
                    SELECT id, striker_batter_type, non_striker_batter_type, bowler_type
                    FROM deliveries 
                    WHERE crease_combo IS NULL 
                    AND striker_batter_type IS NOT NULL 
                    AND non_striker_batter_type IS NOT NULL
                    LIMIT :limit OFFSET :offset
                """), {"limit": batch_size, "offset": offset})
                
                batch_deliveries = batch_result.fetchall()
                
                if not batch_deliveries:
                    break
                
                # Calculate derived values for each delivery
                for delivery in batch_deliveries:
                    delivery_id = delivery[0]
                    striker_type = delivery[1]
                    non_striker_type = delivery[2]
                    bowler_type = delivery[3]
                    
                    # Calculate crease combo
                    if not striker_type or not non_striker_type:
                        crease_combo = 'unknown'
                    elif striker_type == 'RHB' and non_striker_type == 'RHB':
                        crease_combo = 'rhb_rhb'
                    elif striker_type == 'LHB' and non_striker_type == 'LHB':
                        crease_combo = 'lhb_lhb'
                    elif (striker_type == 'LHB' and non_striker_type == 'RHB') or (striker_type == 'RHB' and non_striker_type == 'LHB'):
                        crease_combo = 'lhb_rhb'
                    else:
                        crease_combo = 'unknown'
                    
                    # Calculate ball direction
                    if not striker_type or not bowler_type:
                        ball_direction = 'unknown'
                    elif (striker_type == 'RHB' and bowler_type in ['RO', 'LC']) or (striker_type == 'LHB' and bowler_type in ['RL', 'LO']):
                        ball_direction = 'intoBatter'
                    elif (striker_type == 'LHB' and bowler_type in ['RO', 'LC']) or (striker_type == 'RHB' and bowler_type in ['RL', 'LO']):
                        ball_direction = 'awayFromBatter'
                    else:
                        ball_direction = 'unknown'
                    
                    # Update the delivery
                    connection.execute(text("""
                        UPDATE deliveries 
                        SET crease_combo = :crease_combo,
                            ball_direction = :ball_direction
                        WHERE id = :delivery_id
                    """), {
                        'crease_combo': crease_combo,
                        'ball_direction': ball_direction,
                        'delivery_id': delivery_id
                    })
                
                connection.commit()
                total_updated += len(batch_deliveries)
                
                # Progress update
                progress = (total_updated / total_to_update) * 100
                print(f"   Updated {total_updated:,}/{total_to_update:,} deliveries ({progress:.1f}%)")
            
            print(f"✅ Phase 2 completed successfully!")
            print(f"   Total updated: {total_updated:,}")
            
            return True
            
    except Exception as e:
        print(f"❌ Phase 2 failed: {e}")
        return False

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Production-safe phase runner')
    parser.add_argument('--phase', choices=['1', '2', 'all'], required=True)
    parser.add_argument('--confirm', action='store_true')
    
    args = parser.parse_args()
    
    print("PRODUCTION-SAFE PHASE RUNNER")
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
        print(f"\n⚠️  Running Phase {args.phase} on PRODUCTION")
        response = input("Type 'CONFIRM' to proceed: ").strip()
        if response != "CONFIRM":
            print("❌ Cancelled")
            return 1
    
    success = True
    
    if args.phase == 'all':
        print("\n" + "="*20 + " PHASE 1 " + "="*20)
        success = run_phase_1_safe()
        if success:
            print("\n" + "="*20 + " PHASE 2 " + "="*20)
            success = run_phase_2_safe()
    elif args.phase == '1':
        success = run_phase_1_safe()
    elif args.phase == '2':
        success = run_phase_2_safe()
    
    print(f"\nStatus: {'✅ SUCCESS' if success else '❌ FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
