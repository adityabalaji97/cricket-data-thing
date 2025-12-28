#!/usr/bin/env python3
"""Explore delivery_details table with correct column names."""

from database import get_database_connection
from sqlalchemy import text

def explore():
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        print("=" * 70)
        print("DELIVERY_DETAILS TABLE EXPLORATION")
        print("=" * 70)
        
        total = session.execute(text("SELECT COUNT(*) FROM delivery_details")).scalar()
        print(f"\n📊 Total records: {total:,}")
        
        matches = session.execute(text(
            "SELECT COUNT(DISTINCT p_match) FROM delivery_details WHERE p_match IS NOT NULL"
        )).scalar()
        print(f"📊 Distinct matches (p_match): {matches:,}")
        
        missing = session.execute(text("""
            SELECT COUNT(DISTINCT dd.p_match)
            FROM delivery_details dd
            LEFT JOIN matches m ON dd.p_match = m.id
            WHERE m.id IS NULL AND dd.p_match IS NOT NULL
        """)).scalar()
        print(f"📊 Missing from matches table: {missing:,}")
        
        print("\n" + "-" * 70)
        print("SAMPLE MISSING MATCHES")
        print("-" * 70)
        
        sample = session.execute(text("""
            SELECT DISTINCT dd.p_match, dd.match_date, dd.ground, dd.competition, dd.winner
            FROM delivery_details dd
            LEFT JOIN matches m ON dd.p_match = m.id
            WHERE m.id IS NULL AND dd.p_match IS NOT NULL
            LIMIT 5
        """)).fetchall()
        
        for row in sample:
            print(f"  {row[0]} | {row[1]} | {row[3]} | {row[2][:40] if row[2] else ''}")
        
        print("\n" + "-" * 70)
        print("COMPETITIONS (top 15)")
        print("-" * 70)
        
        comps = session.execute(text("""
            SELECT competition, COUNT(DISTINCT p_match) as cnt
            FROM delivery_details WHERE p_match IS NOT NULL
            GROUP BY competition ORDER BY cnt DESC LIMIT 15
        """)).fetchall()
        
        for row in comps:
            print(f"  {row[0]}: {row[1]} matches")
        
    finally:
        session.close()

if __name__ == "__main__":
    explore()
