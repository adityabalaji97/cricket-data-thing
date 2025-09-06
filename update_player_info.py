#!/usr/bin/env python3
"""
Player Info Update Script - Extended Version

This script extends update_bowler_info.py to also handle batters who do not have
an entry in the players table. It can process missing players from deliveries
table and update their information.

Usage:
    python update_player_info.py --find-missing-players
    python update_player_info.py --find-missing-batters
    python update_player_info.py --csv missing_players_20241207_123456.csv
    python update_player_info.py --single-update "Player Name"
"""

import argparse
import csv
import sys
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from database import get_database_connection
from models import Player, Delivery


class PlayerInfoUpdater:
    """Updates player information in the players table, including missing batters."""
    
    def __init__(self):
        """Initialize database connection."""
        self.engine, SessionLocal = get_database_connection()
        self.session = SessionLocal()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up database connection."""
        self.session.close()
    
    def find_missing_players(self) -> Dict[str, Set[str]]:
        """Find all players (batters and bowlers) missing from players table."""
        print("🔍 Comprehensive search for missing players...")
        
        # Get all unique player names from deliveries
        all_players_query = text("""
            SELECT DISTINCT batter AS player_name FROM deliveries 
            WHERE batter IS NOT NULL AND batter != ''
            UNION
            SELECT DISTINCT non_striker AS player_name FROM deliveries 
            WHERE non_striker IS NOT NULL AND non_striker != ''
            UNION
            SELECT DISTINCT bowler AS player_name FROM deliveries 
            WHERE bowler IS NOT NULL AND bowler != ''
        """)
        
        delivery_players = set()
        result = self.session.execute(all_players_query)
        for row in result:
            delivery_players.add(row[0])
        
        # Get batters only
        batter_query = text("""
            SELECT DISTINCT batter AS player_name FROM deliveries 
            WHERE batter IS NOT NULL AND batter != ''
            UNION
            SELECT DISTINCT non_striker AS player_name FROM deliveries 
            WHERE non_striker IS NOT NULL AND non_striker != ''
        """)
        
        delivery_batters = set()
        result = self.session.execute(batter_query)
        for row in result:
            delivery_batters.add(row[0])
        
        # Get bowlers only
        bowler_query = text("""
            SELECT DISTINCT bowler AS player_name FROM deliveries 
            WHERE bowler IS NOT NULL AND bowler != ''
        """)
        
        delivery_bowlers = set()
        result = self.session.execute(bowler_query)
        for row in result:
            delivery_bowlers.add(row[0])
        
        # Get all existing player names
        existing_players = set()
        players = self.session.query(Player.name).all()
        for player in players:
            existing_players.add(player[0])
        
        # Find missing players by category
        missing_all = delivery_players - existing_players
        missing_batters = delivery_batters - existing_players
        missing_bowlers = delivery_bowlers - existing_players
        
        print(f"📊 Comprehensive Player Analysis:")
        print(f"   • Total unique players in deliveries: {len(delivery_players):,}")
        print(f"   • Existing players in database: {len(existing_players):,}")
        print(f"   • Total missing players: {len(missing_all):,}")
        print(f"   • Missing batters only: {len(missing_batters - missing_bowlers):,}")
        print(f"   • Missing bowlers only: {len(missing_bowlers - missing_batters):,}")
        print(f"   • Missing both (all-rounders): {len(missing_batters & missing_bowlers):,}")
        
        return {
            'all': missing_all,
            'batters': missing_batters,
            'bowlers': missing_bowlers,
            'batters_only': missing_batters - missing_bowlers,
            'bowlers_only': missing_bowlers - missing_batters,
            'both': missing_batters & missing_bowlers
        }
    
    def export_missing_players_csv(self, missing_players: Dict[str, Set[str]], output_file: Optional[str] = None) -> str:
        """Export missing players to CSV for manual data entry."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"missing_players_{timestamp}.csv"
        
        print(f"📄 Exporting missing players to: {output_file}")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'player_name', 'appears_as', 'batter_type', 'bowler_type', 
                'bowl_hand', 'bowl_type', 'nationality', 'notes'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write batters only
            for player in sorted(missing_players['batters_only']):
                writer.writerow({
                    'player_name': player,
                    'appears_as': 'batter_only',
                    'batter_type': '',  # To be filled manually
                    'bowler_type': '',
                    'bowl_hand': '',
                    'bowl_type': '',
                    'nationality': '',
                    'notes': 'Found as batter/non-striker only'
                })
            
            # Write bowlers only
            for player in sorted(missing_players['bowlers_only']):
                writer.writerow({
                    'player_name': player,
                    'appears_as': 'bowler_only',
                    'batter_type': '',
                    'bowler_type': '',  # To be filled manually
                    'bowl_hand': '',  # To be filled manually
                    'bowl_type': '',  # To be filled manually
                    'nationality': '',
                    'notes': 'Found as bowler only'
                })
            
            # Write all-rounders (appear as both)
            for player in sorted(missing_players['both']):
                writer.writerow({
                    'player_name': player,
                    'appears_as': 'both',
                    'batter_type': '',  # To be filled manually
                    'bowler_type': '',  # To be filled manually
                    'bowl_hand': '',  # To be filled manually
                    'bowl_type': '',  # To be filled manually
                    'nationality': '',
                    'notes': 'Found as both batter and bowler'
                })
        
        print(f"✅ Exported {len(missing_players['all'])} missing players")
        return output_file
    
    def add_new_player(self, player_name: str, player_data: Dict) -> bool:
        """Add a new player to the players table."""
        try:
            # Check if player already exists
            existing_player = self.session.query(Player).filter(
                Player.name == player_name
            ).first()
            
            if existing_player:
                print(f"⚠️  Player {player_name} already exists, skipping add...")
                return False
            
            # Create new player
            new_player = Player(
                name=player_name,
                batter_type=player_data.get('batter_type') or None,
                bowler_type=player_data.get('bowler_type') or None,
                bowl_hand=player_data.get('bowl_hand') or None,
                bowl_type=player_data.get('bowl_type') or None,
                nationality=player_data.get('nationality') or None
            )
            
            self.session.add(new_player)
            self.session.commit()
            
            print(f"✅ Added new player: {player_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding player {player_name}: {str(e)}")
            self.session.rollback()
            return False
    
    def process_missing_players_csv(self, csv_file: str) -> Dict[str, int]:
        """Process CSV file for missing players (new additions)."""
        print(f"📄 Processing missing players CSV: {csv_file}")
        
        results = {'added': 0, 'skipped': 0, 'errors': 0}
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    player_name = row['player_name'].strip()
                    
                    # Skip if no player name
                    if not player_name:
                        continue
                    
                    # Skip if no info provided (all fields empty)
                    info_fields = ['batter_type', 'bowler_type', 'bowl_hand', 'bowl_type', 'nationality']
                    if not any(row.get(field, '').strip() for field in info_fields):
                        print(f"⏭️  Skipping {player_name} - no info provided")
                        results['skipped'] += 1
                        continue
                    
                    # Prepare data
                    player_data = {
                        'batter_type': row.get('batter_type', '').strip() or None,
                        'bowler_type': row.get('bowler_type', '').strip() or None,
                        'bowl_hand': row.get('bowl_hand', '').strip() or None,
                        'bowl_type': row.get('bowl_type', '').strip() or None,
                        'nationality': row.get('nationality', '').strip() or None
                    }
                    
                    # Add new player
                    if self.add_new_player(player_name, player_data):
                        results['added'] += 1
                    else:
                        results['errors'] += 1
        
        except FileNotFoundError:
            print(f"❌ CSV file not found: {csv_file}")
            return results
        except Exception as e:
            print(f"❌ Error processing CSV: {str(e)}")
            return results
        
        return results
    
    def interactive_single_update(self, player_name: str):
        """Interactive update for a single player."""
        print(f"🔧 Interactive update for: {player_name}")
        
        # Check if player exists
        player = self.session.query(Player).filter(Player.name == player_name).first()
        
        if not player:
            print(f"❌ Player {player_name} not found. Would you like to add them? (y/n)")
            if input().lower().strip() == 'y':
                return self._interactive_add_player(player_name)
            return
        
        # Show current info
        print(f"\nCurrent player info:")
        print(f"  • batter_type: {player.batter_type or 'None'}")
        print(f"  • bowler_type: {player.bowler_type or 'None'}")
        print(f"  • bowl_hand: {player.bowl_hand or 'None'}")
        print(f"  • bowl_type: {player.bowl_type or 'None'}")
        print(f"  • nationality: {player.nationality or 'None'}")
        
        # Get updates
        updates = {}
        
        print(f"\nEnter new values (press Enter to keep current):")
        
        new_batter_type = input(f"batter_type [{player.batter_type or ''}]: ").strip()
        if new_batter_type:
            player.batter_type = new_batter_type
            updates['batter_type'] = new_batter_type
        
        new_bowler_type = input(f"bowler_type [{player.bowler_type or ''}]: ").strip()
        if new_bowler_type:
            player.bowler_type = new_bowler_type
            updates['bowler_type'] = new_bowler_type
            
        new_bowl_hand = input(f"bowl_hand [{player.bowl_hand or ''}]: ").strip()
        if new_bowl_hand:
            player.bowl_hand = new_bowl_hand
            updates['bowl_hand'] = new_bowl_hand
            
        new_bowl_type = input(f"bowl_type [{player.bowl_type or ''}]: ").strip()
        if new_bowl_type:
            player.bowl_type = new_bowl_type
            updates['bowl_type'] = new_bowl_type
        
        new_nationality = input(f"nationality [{player.nationality or ''}]: ").strip()
        if new_nationality:
            player.nationality = new_nationality
            updates['nationality'] = new_nationality
        
        if updates:
            self.session.commit()
            print(f"✅ Updated {player_name}: {', '.join(f'{k}: {v}' for k, v in updates.items())}")
        else:
            print("⚠️  No changes made")
    
    def _interactive_add_player(self, player_name: str):
        """Interactive addition of new player."""
        print(f"➕ Adding new player: {player_name}")
        
        player_data = {}
        
        player_data['batter_type'] = input("batter_type (LHB/RHB): ").strip() or None
        player_data['bowler_type'] = input("bowler_type (LO/LM/RL/RM/RO/etc): ").strip() or None
        player_data['bowl_hand'] = input("bowl_hand (Left/Right): ").strip() or None  
        player_data['bowl_type'] = input("bowl_type (Pace/Spin/etc): ").strip() or None
        player_data['nationality'] = input("nationality (optional): ").strip() or None
        
        self.add_new_player(player_name, player_data)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Update player information in players table')
    parser.add_argument('--csv', help='CSV file to process (missing players)')
    parser.add_argument('--find-missing-batters', action='store_true', help='Find batters missing from players table')
    parser.add_argument('--find-missing-players', action='store_true', help='Find all missing players and export to CSV')
    parser.add_argument('--single-update', help='Single player name to update interactively')
    parser.add_argument('--export-csv', help='Export missing players to specified CSV file')
    
    args = parser.parse_args()
    
    if not any([args.csv, args.find_missing_batters, args.find_missing_players, args.single_update]):
        print("❌ Please provide one of the available options")
        parser.print_help()
        sys.exit(1)
    
    print("🏏 Starting Player Info Update...")
    print("="*50)
    
    with PlayerInfoUpdater() as updater:
        if args.find_missing_batters:
            missing_players = updater.find_missing_players()
            missing_batters = missing_players['batters']
            if missing_batters:
                print(f"\n📋 First 10 missing batters:")
                for i, batter in enumerate(sorted(missing_batters)[:10]):
                    print(f"   {i+1}. {batter}")
                if len(missing_batters) > 10:
                    print(f"   ... and {len(missing_batters) - 10} more")
        
        elif args.find_missing_players:
            missing_players = updater.find_missing_players()
            
            # Export to CSV
            csv_file = args.export_csv or None
            exported_file = updater.export_missing_players_csv(missing_players, csv_file)
            
            print(f"\n📄 Next steps:")
            print(f"   1. Open {exported_file}")
            print(f"   2. Fill in the batter_type, bowler_type, bowl_hand, bowl_type columns")
            print(f"   3. Run: python update_player_info.py --csv {exported_file}")
        
        elif args.single_update:
            updater.interactive_single_update(args.single_update)
            
        elif args.csv:
            results = updater.process_missing_players_csv(args.csv)
            print(f"\n📊 Missing Players Import Results:")
            print(f"   • Added: {results['added']}")
            print(f"   • Skipped: {results['skipped']}")
            print(f"   • Errors: {results['errors']}")
    
    print("\n✅ Player info update process completed!")


if __name__ == "__main__":
    main()
