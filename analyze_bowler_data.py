#!/usr/bin/env python3
"""
Bowler Data Analysis Script

This script analyzes bowler data to identify:
1. Bowlers in deliveries table who don't exist in players table
2. Bowlers with missing bowling information (bowler_type, bowl_hand, bowl_type)
3. Generates CSV files for manual data updates

Usage:
    python analyze_bowler_data.py
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple

from sqlalchemy.orm import sessionmaker
from database import get_database_connection
from models import Delivery, Player


class BowlerDataAnalyzer:
    """Analyzes bowler data and generates reports for missing information."""
    
    def __init__(self):
        """Initialize database connection."""
        self.engine, SessionLocal = get_database_connection()
        self.session = SessionLocal()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up database connection."""
        self.session.close()
    
    def get_all_bowlers_from_deliveries(self) -> Set[str]:
        """Get all unique bowler names from deliveries table."""
        print("📊 Fetching all unique bowlers from deliveries table...")
        
        bowlers = self.session.query(Delivery.bowler).distinct().all()
        bowler_names = {bowler[0] for bowler in bowlers if bowler[0] is not None}
        
        print(f"✅ Found {len(bowler_names)} unique bowlers in deliveries table")
        return bowler_names
    
    def get_players_bowling_info(self) -> Dict[str, Dict]:
        """Get bowling information for all players."""
        print("📊 Fetching bowling information from players table...")
        
        players = self.session.query(
            Player.name,
            Player.bowler_type,
            Player.bowl_hand, 
            Player.bowl_type,
            Player.bowling_type
        ).all()
        
        players_info = {}
        for player in players:
            players_info[player.name] = {
                'bowler_type': player.bowler_type,
                'bowl_hand': player.bowl_hand,
                'bowl_type': player.bowl_type,
                'bowling_type': player.bowling_type  # Legacy field
            }
        
        print(f"✅ Found {len(players_info)} players with bowling info")
        return players_info
    
    def analyze_missing_bowlers(self, delivery_bowlers: Set[str], 
                              players_info: Dict[str, Dict]) -> Tuple[Set[str], Dict[str, Dict]]:
        """Analyze which bowlers are missing or have incomplete data."""
        print("🔍 Analyzing missing and incomplete bowler data...")
        
        # Bowlers not in players table at all
        missing_bowlers = delivery_bowlers - set(players_info.keys())
        
        # Bowlers with incomplete bowling information
        incomplete_bowlers = {}
        for bowler in delivery_bowlers:
            if bowler in players_info:
                info = players_info[bowler]
                missing_fields = []
                
                # Check each bowling field
                if not info.get('bowler_type'):
                    missing_fields.append('bowler_type')
                if not info.get('bowl_hand'):
                    missing_fields.append('bowl_hand')
                if not info.get('bowl_type'):
                    missing_fields.append('bowl_type')
                
                if missing_fields:
                    incomplete_bowlers[bowler] = {
                        'current_info': info,
                        'missing_fields': missing_fields
                    }
        
        print(f"❌ {len(missing_bowlers)} bowlers not in players table")
        print(f"⚠️  {len(incomplete_bowlers)} bowlers with incomplete bowling info")
        
        return missing_bowlers, incomplete_bowlers
    
    def get_bowler_match_count(self, bowlers: Set[str]) -> Dict[str, int]:
        """Get match count for each bowler to prioritize by frequency."""
        print("📈 Getting delivery counts for bowlers...")
        
        bowler_counts = defaultdict(int)
        
        # Get delivery count for each bowler
        for bowler in bowlers:
            count = self.session.query(Delivery).filter(Delivery.bowler == bowler).count()
            bowler_counts[bowler] = count
        
        return dict(bowler_counts)
    
    def generate_missing_bowlers_csv(self, missing_bowlers: Set[str], 
                                   bowler_counts: Dict[str, int], 
                                   filename: str = None) -> str:
        """Generate CSV for bowlers not in players table."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"missing_bowlers_{timestamp}.csv"
        
        # Sort by delivery count (most frequent first)
        sorted_bowlers = sorted(missing_bowlers, 
                              key=lambda x: bowler_counts.get(x, 0), 
                              reverse=True)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow([
                'bowler_name',
                'delivery_count',
                'bowler_type',  # To be filled manually
                'bowl_hand',    # To be filled manually  
                'bowl_type',    # To be filled manually
                'bowling_type', # Legacy field
                'nationality',  # Optional
                'notes'         # For any additional info
            ])
            
            # Data rows
            for bowler in sorted_bowlers:
                writer.writerow([
                    bowler,
                    bowler_counts.get(bowler, 0),
                    '',  # bowler_type - to be filled
                    '',  # bowl_hand - to be filled
                    '',  # bowl_type - to be filled
                    '',  # bowling_type - to be filled
                    '',  # nationality - to be filled
                    ''   # notes - to be filled
                ])
        
        print(f"📄 Generated missing bowlers CSV: {filename}")
        return filename
    
    def generate_incomplete_bowlers_csv(self, incomplete_bowlers: Dict[str, Dict],
                                      bowler_counts: Dict[str, int],
                                      filename: str = None) -> str:
        """Generate CSV for bowlers with incomplete bowling information."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"incomplete_bowlers_{timestamp}.csv"
        
        # Sort by delivery count (most frequent first)
        sorted_bowlers = sorted(incomplete_bowlers.keys(),
                              key=lambda x: bowler_counts.get(x, 0),
                              reverse=True)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow([
                'bowler_name',
                'delivery_count',
                'current_bowler_type',
                'current_bowl_hand', 
                'current_bowl_type',
                'current_bowling_type',
                'missing_fields',
                'new_bowler_type',  # To be filled
                'new_bowl_hand',    # To be filled
                'new_bowl_type',    # To be filled
                'notes'
            ])
            
            # Data rows
            for bowler in sorted_bowlers:
                info = incomplete_bowlers[bowler]
                current = info['current_info']
                missing = ', '.join(info['missing_fields'])
                
                writer.writerow([
                    bowler,
                    bowler_counts.get(bowler, 0),
                    current.get('bowler_type', ''),
                    current.get('bowl_hand', ''),
                    current.get('bowl_type', ''),
                    current.get('bowling_type', ''),
                    missing,
                    '',  # new_bowler_type - to be filled
                    '',  # new_bowl_hand - to be filled  
                    '',  # new_bowl_type - to be filled
                    ''   # notes
                ])
        
        print(f"📄 Generated incomplete bowlers CSV: {filename}")
        return filename
    
    def print_summary_report(self, delivery_bowlers: Set[str], 
                           missing_bowlers: Set[str],
                           incomplete_bowlers: Dict[str, Dict],
                           bowler_counts: Dict[str, int]):
        """Print a comprehensive summary report."""
        print("\n" + "="*80)
        print("🏏 BOWLER DATA ANALYSIS SUMMARY REPORT")
        print("="*80)
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   • Total unique bowlers in deliveries: {len(delivery_bowlers)}")
        print(f"   • Bowlers missing from players table: {len(missing_bowlers)}")
        print(f"   • Bowlers with incomplete info: {len(incomplete_bowlers)}")
        print(f"   • Bowlers with complete info: {len(delivery_bowlers) - len(missing_bowlers) - len(incomplete_bowlers)}")
        
        if missing_bowlers:
            print(f"\n❌ TOP 10 MISSING BOWLERS (by delivery count):")
            top_missing = sorted(missing_bowlers, 
                               key=lambda x: bowler_counts.get(x, 0), 
                               reverse=True)[:10]
            for i, bowler in enumerate(top_missing, 1):
                print(f"   {i:2d}. {bowler:<25} ({bowler_counts.get(bowler, 0):,} deliveries)")
        
        if incomplete_bowlers:
            print(f"\n⚠️  TOP 10 INCOMPLETE BOWLERS (by delivery count):")
            top_incomplete = sorted(incomplete_bowlers.keys(),
                                  key=lambda x: bowler_counts.get(x, 0),
                                  reverse=True)[:10]
            for i, bowler in enumerate(top_incomplete, 1):
                missing_fields = ', '.join(incomplete_bowlers[bowler]['missing_fields'])
                print(f"   {i:2d}. {bowler:<25} ({bowler_counts.get(bowler, 0):,} deliveries) - Missing: {missing_fields}")
        
        # Analysis by missing fields
        if incomplete_bowlers:
            field_counts = defaultdict(int)
            for bowler_data in incomplete_bowlers.values():
                for field in bowler_data['missing_fields']:
                    field_counts[field] += 1
            
            print(f"\n📈 MISSING FIELDS BREAKDOWN:")
            for field, count in sorted(field_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {field}: {count} bowlers")
        
        print(f"\n✅ NEXT STEPS:")
        print(f"   1. Review and fill the generated CSV files")
        print(f"   2. Use the update_bowler_info.py script to bulk update")
        print(f"   3. Re-run this analysis to verify updates")
        print("="*80)


def main():
    """Main execution function."""
    print("🏏 Starting Bowler Data Analysis...")
    print("="*50)
    
    with BowlerDataAnalyzer() as analyzer:
        # Get all data
        delivery_bowlers = analyzer.get_all_bowlers_from_deliveries()
        players_info = analyzer.get_players_bowling_info()
        
        # Analyze missing data
        missing_bowlers, incomplete_bowlers = analyzer.analyze_missing_bowlers(
            delivery_bowlers, players_info
        )
        
        # Get delivery counts for prioritization
        all_problem_bowlers = missing_bowlers.union(set(incomplete_bowlers.keys()))
        bowler_counts = analyzer.get_bowler_match_count(all_problem_bowlers)
        
        # Generate CSV files
        missing_csv = analyzer.generate_missing_bowlers_csv(missing_bowlers, bowler_counts)
        incomplete_csv = analyzer.generate_incomplete_bowlers_csv(incomplete_bowlers, bowler_counts)
        
        # Print summary report
        analyzer.print_summary_report(
            delivery_bowlers, missing_bowlers, incomplete_bowlers, bowler_counts
        )
        
        print(f"\n📁 Generated Files:")
        print(f"   • {missing_csv}")
        print(f"   • {incomplete_csv}")


if __name__ == "__main__":
    main()
