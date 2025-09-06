#!/usr/bin/env python3
"""
Production-Optimized Phase Runner

This version uses smaller batches and more frequent commits to avoid
timeout issues on production databases.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import argparse
from datetime import datetime
import pandas as pd

load_dotenv()

def get_production_db_url():
    """Get production database URL from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url

def run_phase_3_optimized():
    """Run Phase 3 with optimized batching for production."""
    print("🔄 Running Phase 3 with optimized batching...")
    
    db_url = get_production_db_url()
    engine = create_engine(db_url, pool_timeout=30, pool_recycle=300)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    try:
        # Load Excel data
        excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
        df = pd.read_excel(excel_path)
        print(f"📄 Loaded {len(df)} players from Excel")
        
        # Get existing players
        session = SessionLocal()
        existing_players = {}
        
        # Get existing players in batches to avoid memory issues
        print("🔍 Loading existing players...")
        result = session.execute(text("SELECT name, batter_type, bowler_type, bowl_hand, bowl_type FROM players"))
        for row in result:
            existing_players[row[0]] = {
                'batter_type': row[1],
                'bowler_type': row[2], 
                'bowl_hand': row[3],
                'bowl_type': row[4]
            }
        
        print(f"Found {len(existing_players)} existing players")
        
        # Process in small batches
        batch_size = 50  # Much smaller batches for production
        total_updated = 0
        total_new = 0
        total_errors = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch_updated = 0
            batch_new = 0
            batch_errors = 0
            
            try:
                for _, row in batch.iterrows():
                    try:
                        player_name = str(row['Player']).strip()
                        if not player_name or player_name == 'nan':
                            continue
                        
                        # Get new values
                        new_batter_type = str(row.get('batterType', '')).strip() or None
                        new_bowler_type = str(row.get('bowlerType', '')).strip() or None
                        new_bowl_hand = str(row.get('bowlHand', '')).strip() or None
                        new_bowl_type = str(row.get('bowlType', '')).strip() or None
                        
                        if player_name in existing_players:
                            # Update existing player
                            updates = []
                            if new_batter_type and new_batter_type != 'nan':
                                updates.append(f"batter_type = '{new_batter_type}'")
                            if new_bowler_type and new_bowler_type != 'nan':
                                updates.append(f"bowler_type = '{new_bowler_type}'")
                            if new_bowl_hand and new_bowl_hand != 'nan':
                                updates.append(f"bowl_hand = '{new_bowl_hand}'")
                            if new_bowl_type and new_bowl_type != 'nan':
                                updates.append(f"bowl_type = '{new_bowl_type}'")
                            
                            if updates:
                                update_sql = f"UPDATE players SET {', '.join(updates)} WHERE name = :name"
                                session.execute(text(update_sql), {"name": player_name})
                                batch_updated += 1
                        else:
                            # Insert new player
                            insert_sql = """
                            INSERT INTO players (name, batter_type, bowler_type, bowl_hand, bowl_type) 
                            VALUES (:name, :batter_type, :bowler_type, :bowl_hand, :bowl_type)
                            """
                            session.execute(text(insert_sql), {
                                "name": player_name,
                                "batter_type": new_batter_type if new_batter_type != 'nan' else None,
                                "bowler_type": new_bowler_type if new_bowler_type != 'nan' else None,
                                "bowl_hand": new_bowl_hand if new_bowl_hand != 'nan' else None,
                                "bowl_type": new_bowl_type if new_bowl_type != 'nan' else None
                            })
                            batch_new += 1
                            
                    except Exception as e:
                        print(f"   Error with player {player_name}: {e}")
                        batch_errors += 1
                
                # Commit this batch
                session.commit()
                
                total_updated += batch_updated
                total_new += batch_new
                total_errors += batch_errors
                
                print(f"   Batch {i//batch_size + 1}: Updated {batch_updated}, New {batch_new}, Errors {batch_errors}")
                
            except Exception as e:
                print(f"   Batch {i//batch_size + 1} failed: {e}")
                session.rollback()
                total_errors += batch_size
        
        session.close()
        
        print(f"✅ Phase 3 completed!")
        print(f"   Total updated: {total_updated}")
        print(f"   Total new: {total_new}")
        print(f"   Total errors: {total_errors}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 3 failed: {e}")
        return False

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Production-optimized phase runner')
    parser.add_argument('--phase', choices=['3'], required=True)
    parser.add_argument('--confirm', action='store_true')
    
    args = parser.parse_args()
    
    print("PRODUCTION-OPTIMIZED RUNNER")
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
        print(f"\n⚠️  Running optimized Phase {args.phase} on PRODUCTION")
        response = input("Type 'CONFIRM' to proceed: ").strip()
        if response != "CONFIRM":
            print("❌ Cancelled")
            return 1
    
    if args.phase == '3':
        success = run_phase_3_optimized()
    
    print(f"\nStatus: {'✅ SUCCESS' if success else '❌ FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
