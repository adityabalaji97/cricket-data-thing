#!/usr/bin/env python3
"""
Production Verification Script for Left-Right Analysis

This script verifies the left-right analysis implementation on production databases
using environment variables for database connection.

Environment Variables Required:
    DATABASE_URL - Production database connection string
    ENVIRONMENT - Set to 'production' for production runs

Usage:
    export DATABASE_URL="postgresql://user:pass@host:port/dbname"
    export ENVIRONMENT="production"
    python verify_production.py --ipl
"""

import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_production_db_url() -> str:
    """Get production database URL from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Handle Heroku postgres:// URLs
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return db_url


def verify_production_environment() -> bool:
    """Verify this is intended for production use."""
    environment = os.getenv("ENVIRONMENT", "").lower()
    
    if environment != "production":
        print("❌ ENVIRONMENT variable must be set to 'production'")
        print("   This is a safety check for production database access")
        return False
    
    return True


def get_production_delivery_statistics(filter_ipl=False):
    """Get comprehensive statistics from production database."""
    db_url = get_production_db_url()
    engine = create_engine(db_url)
    
    # Base WHERE clause for IPL filtering
    ipl_filter = ""
    if filter_ipl:
        ipl_filter = """
        WHERE d.match_id IN (
            SELECT id FROM matches 
            WHERE competition = 'Indian Premier League' 
            OR competition = 'IPL'
        )
        """
    
    with engine.connect() as connection:
        # Total deliveries
        total_query = f"SELECT COUNT(*) FROM deliveries d {ipl_filter}"
        total_deliveries = connection.execute(text(total_query)).scalar()
        
        # Phase 1 statistics
        if filter_ipl:
            striker_query = """
            SELECT COUNT(*) FROM deliveries d 
            WHERE d.match_id IN (
                SELECT id FROM matches 
                WHERE competition = 'Indian Premier League' 
                OR competition = 'IPL'
            ) AND d.striker_batter_type IS NOT NULL
            """
        else:
            striker_query = "SELECT COUNT(*) FROM deliveries WHERE striker_batter_type IS NOT NULL"
        striker_type_populated = connection.execute(text(striker_query)).scalar()
        
        if filter_ipl:
            non_striker_query = """
            SELECT COUNT(*) FROM deliveries d 
            WHERE d.match_id IN (
                SELECT id FROM matches 
                WHERE competition = 'Indian Premier League' 
                OR competition = 'IPL'
            ) AND d.non_striker_batter_type IS NOT NULL
            """
        else:
            non_striker_query = "SELECT COUNT(*) FROM deliveries WHERE non_striker_batter_type IS NOT NULL"
        non_striker_type_populated = connection.execute(text(non_striker_query)).scalar()
        
        if filter_ipl:
            bowler_query = """
            SELECT COUNT(*) FROM deliveries d 
            WHERE d.match_id IN (
                SELECT id FROM matches 
                WHERE competition = 'Indian Premier League' 
                OR competition = 'IPL'
            ) AND d.bowler_type IS NOT NULL
            """
        else:
            bowler_query = "SELECT COUNT(*) FROM deliveries WHERE bowler_type IS NOT NULL"
        bowler_type_populated = connection.execute(text(bowler_query)).scalar()
        
        # Phase 2 statistics
        if filter_ipl:
            crease_query = """
            SELECT COUNT(*) FROM deliveries d 
            WHERE d.match_id IN (
                SELECT id FROM matches 
                WHERE competition = 'Indian Premier League' 
                OR competition = 'IPL'
            ) AND d.crease_combo IS NOT NULL
            """
        else:
            crease_query = "SELECT COUNT(*) FROM deliveries WHERE crease_combo IS NOT NULL"
        crease_combo_populated = connection.execute(text(crease_query)).scalar()
        
        if filter_ipl:
            ball_direction_query = """
            SELECT COUNT(*) FROM deliveries d 
            WHERE d.match_id IN (
                SELECT id FROM matches 
                WHERE competition = 'Indian Premier League' 
                OR competition = 'IPL'
            ) AND d.ball_direction IS NOT NULL
            """
        else:
            ball_direction_query = "SELECT COUNT(*) FROM deliveries WHERE ball_direction IS NOT NULL"
        ball_direction_populated = connection.execute(text(ball_direction_query)).scalar()
        
        # Crease combo breakdown
        if filter_ipl:
            sample_query = """
            SELECT 
                d.crease_combo, 
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / :total, 2) as percentage
            FROM deliveries d
            WHERE d.match_id IN (
                SELECT id FROM matches 
                WHERE competition = 'Indian Premier League' 
                OR competition = 'IPL'
            ) AND d.crease_combo IS NOT NULL
            GROUP BY d.crease_combo
            ORDER BY count DESC
            """
        else:
            sample_query = """
            SELECT 
                crease_combo, 
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / :total, 2) as percentage
            FROM deliveries 
            WHERE crease_combo IS NOT NULL
            GROUP BY crease_combo
            ORDER BY count DESC
            """
        sample_data = connection.execute(text(sample_query), {"total": crease_combo_populated}).fetchall()
        
        # Ball direction breakdown
        if filter_ipl:
            direction_query = """
            SELECT 
                d.ball_direction, 
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / :total, 2) as percentage
            FROM deliveries d
            WHERE d.match_id IN (
                SELECT id FROM matches 
                WHERE competition = 'Indian Premier League' 
                OR competition = 'IPL'
            ) AND d.ball_direction IS NOT NULL
            GROUP BY d.ball_direction
            ORDER BY count DESC
            """
        else:
            direction_query = """
            SELECT 
                ball_direction, 
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / :total, 2) as percentage
            FROM deliveries 
            WHERE ball_direction IS NOT NULL
            GROUP BY ball_direction
            ORDER BY count DESC
            """
        ball_direction_data = connection.execute(text(direction_query), {"total": ball_direction_populated}).fetchall()
        
        return {
            'total_deliveries': total_deliveries,
            'striker_type_populated': striker_type_populated,
            'non_striker_type_populated': non_striker_type_populated,
            'bowler_type_populated': bowler_type_populated,
            'crease_combo_populated': crease_combo_populated,
            'ball_direction_populated': ball_direction_populated,
            'crease_combo_breakdown': sample_data,
            'ball_direction_breakdown': ball_direction_data
        }


def main():
    """Main verification function for production."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify left-right analysis on production database')
    parser.add_argument('--ipl', action='store_true', help='Filter results to IPL matches only')
    args = parser.parse_args()
    
    # Safety checks
    if not verify_production_environment():
        return 1
    
    try:
        db_url = get_production_db_url()
        # Mask the password in the display
        display_url = db_url.split('@')[1] if '@' in db_url else 'Unknown'
        print(f"🔗 Connected to production database: {display_url}")
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    title = "PRODUCTION Left-Right Analysis - Verification Report"
    if args.ipl:
        title += " (IPL Only)"
    
    print(title)
    print("=" * len(title))
    
    try:
        stats = get_production_delivery_statistics(filter_ipl=args.ipl)
        
        if args.ipl:
            print(f"\n🏏 PRODUCTION IPL DELIVERY STATISTICS:")
        else:
            print(f"\n📊 PRODUCTION DELIVERY STATISTICS:")
        print(f"Total deliveries: {stats['total_deliveries']:,}")
        print()
        
        print("📋 PHASE 1 RESULTS (Base Columns):")
        print(f"  striker_batter_type populated: {stats['striker_type_populated']:,} / {stats['total_deliveries']:,}")
        print(f"  non_striker_batter_type populated: {stats['non_striker_type_populated']:,} / {stats['total_deliveries']:,}")
        print(f"  bowler_type populated: {stats['bowler_type_populated']:,} / {stats['total_deliveries']:,}")
        
        phase1_completion = (stats['striker_type_populated'] / stats['total_deliveries']) * 100 if stats['total_deliveries'] > 0 else 0
        print(f"  Phase 1 completion: {phase1_completion:.1f}%")
        print()
        
        print("📋 PHASE 2 RESULTS (Derived Columns):")
        print(f"  crease_combo populated: {stats['crease_combo_populated']:,} / {stats['total_deliveries']:,}")
        print(f"  ball_direction populated: {stats['ball_direction_populated']:,} / {stats['total_deliveries']:,}")
        
        phase2_completion = (stats['crease_combo_populated'] / stats['total_deliveries']) * 100 if stats['total_deliveries'] > 0 else 0
        print(f"  Phase 2 completion: {phase2_completion:.1f}%")
        print()
        
        print("🎯 CREASE COMBO ANALYSIS (Granular):")
        for row in stats['crease_combo_breakdown']:
            combo_name = row[0]
            if combo_name == 'rhb_rhb':
                description = f"{combo_name} (both right-handed)"
            elif combo_name == 'lhb_lhb':
                description = f"{combo_name} (both left-handed)"
            elif combo_name == 'lhb_rhb':
                description = f"{combo_name} (left + right combo)"
            else:
                description = combo_name
            print(f"  {description}: {row[1]:,} deliveries ({row[2]}%)")
        print()
        
        # Check for old values that need granular update
        old_values = ['same', 'left_right']
        has_old_values = any(row[0] in old_values for row in stats['crease_combo_breakdown'])
        
        if has_old_values:
            print("🔧 PRODUCTION RECOMMENDATION:")
            print("   Old crease combo values detected. Run granular update:")
            print("   python run_production_phases.py --phase=granular --confirm")
            print()
        
        print("🎯 BALL DIRECTION ANALYSIS:")
        for row in stats['ball_direction_breakdown']:
            print(f"  {row[0]}: {row[1]:,} deliveries ({row[2]}%)")
        print()
        
        # Summary
        if phase1_completion > 99 and phase2_completion > 99:
            print("✅ SUCCESS: Production implementation is complete!")
            if args.ipl:
                print("🏏 Production IPL data is ready for advanced left-right analysis!")
            else:
                print("🚀 Production data is ready for advanced left-right analysis!")
        elif phase1_completion > 99:
            print("⚠️  Phase 1 complete, Phase 2 may need additional runs")
        else:
            print("⚠️  Some deliveries may need additional processing")
            
    except Exception as e:
        print(f"❌ Error generating production verification report: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
