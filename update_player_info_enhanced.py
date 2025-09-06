#!/usr/bin/env python3
"""
Enhanced Player Info Update Script

This script extends the original to handle both missing batters and existing batters
with incomplete batter_type information.

Features:
- Find batters missing from players table
- Find existing batters with empty/null batter_type
- Single CSV export with flag column indicating the issue
- Process updates for both missing and incomplete batter info

Usage:
    python update_player_info_enhanced.py --find-missing-batters
    python update_player_info_enhanced.py --find-incomplete-batters
    python update_player_info_enhanced.py --find-all-batter-issues
    python update_player_info_enhanced.py --csv batters_to_update_20241207_123456.csv
    python update_player_info_enhanced.py --single-update "Player Name"
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


class EnhancedPlayerInfoUpdater:
    """Enhanced updater for player information with batter_type validation."""
    
    def __init__(self):
        """Initialize database connection."""
        self.engine, SessionLocal = get_database_connection()
        self.session = SessionLocal()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up database connection."""
        self.session.close()
    
    def find_missing_batters(self) -> Set[str]:
        """Find batters who appear in deliveries but don't exist in players table."""
        print("🔍 Finding batters missing from players table...")
        
        # Get all unique batter names from deliveries
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
        
        # Get all existing player names
        existing_players = set()
        players = self.session.query(Player.name).all()
        for player in players:
            existing_players.add(player[0])
        
        # Find missing batters
        missing_batters = delivery_batters - existing_players
        
        print(f"   • Total unique batters in deliveries: {len(delivery_batters):,}")
        print(f"   • Existing players in database: {len(existing_players):,}")
        print(f"   • Missing batters: {len(missing_batters):,}")
        
        return missing_batters
    
    def find_incomplete_batters(self) -> Set[str]:
        """Find existing players who have empty/null batter_type."""
        print("🔍 Finding existing batters with empty batter_type...")
        
        # Get players who exist but have empty batter_type
        incomplete_query = text("""
            SELECT name FROM players 
            WHERE (batter_type IS NULL OR batter_type = '' OR TRIM(batter_type) = '')
            AND name IN (
                SELECT DISTINCT batter FROM deliveries WHERE batter IS NOT NULL
                UNION 
                SELECT DISTINCT non_striker FROM deliveries WHERE non_striker IS NOT NULL
            )
        """)
        
        incomplete_batters = set()
        result = self.session.execute(incomplete_query)
        for row in result:
            incomplete_batters.add(row[0])
        
        print(f"   • Existing batters with empty batter_type: {len(incomplete_batters):,}")
        
        return incomplete_batters
    
    def find_all_batter_issues(self) -> Dict[str, Set[str]]:
        """Find both missing batters and batters with incomplete batter_type."""
        print("🔍 Comprehensive batter analysis...")
        
        missing_batters = self.find_missing_batters()
        incomplete_batters = self.find_incomplete_batters()
        
        # Summary
        print(f"\n📊 Batter Issues Summary:")
        print(f"   • Missing from players table: {len(missing_batters):,}")
        print(f"   • Existing but incomplete batter_type: {len(incomplete_batters):,}")
        print(f"   • Total batters needing attention: {len(missing_batters | incomplete_batters):,}")
        
        return {
            'missing': missing_batters,
            'incomplete': incomplete_batters,
            'all_issues': missing_batters | incomplete_batters
        }
    
    def get_batter_stats(self, batter_name: str) -> Dict[str, int]:
        """Get basic stats for a batter from deliveries table."""
        stats_query = text("""
            SELECT 
                COUNT(*) as total_balls,
                COUNT(CASE WHEN batter = :batter_name THEN 1 END) as striker_balls,
                COUNT(CASE WHEN non_striker = :batter_name THEN 1 END) as non_striker_balls,
                COUNT(DISTINCT match_id) as matches_played
            FROM deliveries 
            WHERE batter = :batter_name OR non_striker = :batter_name
        """)
        
        result = self.session.execute(stats_query, {"batter_name": batter_name})
        row = result.fetchone()
        
        return {
            'total_balls': row[0],
            'striker_balls': row[1], 
            'non_striker_balls': row[2],
            'matches_played': row[3]
        }
    
    def export_batter_issues_csv(self, batter_issues: Dict[str, Set[str]], output_file: Optional[str] = None) -> str:
        """Export batter issues to CSV with flag column indicating the problem."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"batters_to_update_{timestamp}.csv"
        
        print(f"📄 Exporting batter issues to: {output_file}")
        
        all_batters = batter_issues['missing'] | batter_issues['incomplete']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'batter_name', 'issue_type', 'current_batter_type', 'new_batter_type',
                'total_balls', 'striker_balls', 'non_striker_balls', 'matches_played', 
                'notes'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Process each batter
            for batter in sorted(all_batters):
                # Determine issue type
                if batter in batter_issues['missing']:
                    issue_type = "missing_from_players_table"
                    current_batter_type = "N/A"
                elif batter in batter_issues['incomplete']:
                    issue_type = "empty_batter_type"
                    # Get current batter_type
                    player = self.session.query(Player).filter(Player.name == batter).first()
                    current_batter_type = player.batter_type if player and player.batter_type else "NULL/Empty"
                else:
                    continue  # Shouldn't happen
                
                # Get batter stats
                stats = self.get_batter_stats(batter)
                
                # Generate notes
                notes = []
                if stats['striker_balls'] > stats['non_striker_balls']:
                    notes.append("Primarily striker")
                elif stats['non_striker_balls'] > stats['striker_balls']:
                    notes.append("Primarily non-striker")
                else:
                    notes.append("Equal striker/non-striker")
                
                if stats['matches_played'] >= 10:
                    notes.append("Regular player")
                elif stats['matches_played'] >= 5:
                    notes.append("Occasional player")
                else:
                    notes.append("Rare appearances")
                
                writer.writerow({
                    'batter_name': batter,
                    'issue_type': issue_type,
                    'current_batter_type': current_batter_type,
                    'new_batter_type': '',  # To be filled manually
                    'total_balls': stats['total_balls'],
                    'striker_balls': stats['striker_balls'],
                    'non_striker_balls': stats['non_striker_balls'],
                    'matches_played': stats['matches_played'],
                    'notes': '; '.join(notes)
                })
        
        print(f"✅ Exported {len(all_batters)} batters with issues")
        return output_file
    
    def add_new_player(self, batter_name: str, batter_data: Dict) -> bool:
        """Add a new player to the players table."""
        try:
            # Check if player already exists
            existing_player = self.session.query(Player).filter(
                Player.name == batter_name
            ).first()
            
            if existing_player:
                print(f"⚠️  Player {batter_name} already exists, skipping add...")
                return False
            
            # Create new player
            new_player = Player(
                name=batter_name,
                batter_type=batter_data.get('new_batter_type') or None,
                bowler_type=batter_data.get('bowler_type') or None,
                bowl_hand=batter_data.get('bowl_hand') or None,
                bowl_type=batter_data.get('bowl_type') or None,
                nationality=batter_data.get('nationality') or None
            )
            
            self.session.add(new_player)
            self.session.commit()
            
            print(f"✅ Added new player: {batter_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding player {batter_name}: {str(e)}")
            self.session.rollback()
            return False
    
    def update_existing_player(self, batter_name: str, batter_data: Dict) -> bool:
        """Update batter_type for existing player."""
        try:
            player = self.session.query(Player).filter(
                Player.name == batter_name
            ).first()
            
            if not player:
                print(f"❌ Player {batter_name} not found in database")
                return False
            
            # Track what we're updating
            updates = []
            
            # Update batter_type if provided
            if batter_data.get('new_batter_type'):
                old_batter_type = player.batter_type or 'NULL'
                player.batter_type = batter_data['new_batter_type']
                updates.append(f"batter_type: {old_batter_type} -> {batter_data['new_batter_type']}")
            
            # Also update other fields if provided
            if batter_data.get('bowler_type'):
                player.bowler_type = batter_data['bowler_type']
                updates.append(f"bowler_type: {batter_data['bowler_type']}")
                
            if batter_data.get('bowl_hand'):
                player.bowl_hand = batter_data['bowl_hand']
                updates.append(f"bowl_hand: {batter_data['bowl_hand']}")
                
            if batter_data.get('bowl_type'):
                player.bowl_type = batter_data['bowl_type']
                updates.append(f"bowl_type: {batter_data['bowl_type']}")
            
            if updates:
                self.session.commit()
                print(f"✅ Updated {batter_name}: {', '.join(updates)}")
                return True
            else:
                print(f"⚠️  No updates needed for {batter_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating player {batter_name}: {str(e)}")
            self.session.rollback()
            return False
    
    def process_batter_updates_csv(self, csv_file: str) -> Dict[str, int]:
        """Process CSV file for batter updates (both new additions and updates)."""
        print(f"📄 Processing batter updates CSV: {csv_file}")
        
        results = {'added': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    batter_name = row['batter_name'].strip()
                    issue_type = row.get('issue_type', '').strip()
                    new_batter_type = row.get('new_batter_type', '').strip()
                    
                    # Skip if no batter name or no new batter_type provided
                    if not batter_name or not new_batter_type:
                        print(f"⏭️  Skipping {batter_name} - missing name or batter_type")
                        results['skipped'] += 1
                        continue
                    
                    # Prepare data
                    batter_data = {
                        'new_batter_type': new_batter_type,
                        'bowler_type': row.get('bowler_type', '').strip() or None,
                        'bowl_hand': row.get('bowl_hand', '').strip() or None,
                        'bowl_type': row.get('bowl_type', '').strip() or None,
                        'nationality': row.get('nationality', '').strip() or None
                    }
                    
                    # Process based on issue type
                    if issue_type == "missing_from_players_table":
                        if self.add_new_player(batter_name, batter_data):
                            results['added'] += 1
                        else:
                            results['errors'] += 1
                    elif issue_type == "empty_batter_type":
                        if self.update_existing_player(batter_name, batter_data):
                            results['updated'] += 1
                        else:
                            results['errors'] += 1
                    else:
                        print(f"⚠️  Unknown issue type for {batter_name}: {issue_type}")
                        results['skipped'] += 1
        
        except FileNotFoundError:
            print(f"❌ CSV file not found: {csv_file}")
            return results
        except Exception as e:
            print(f"❌ Error processing CSV: {str(e)}")
            return results
        
        return results
    
    def interactive_single_update(self, batter_name: str):
        """Interactive update for a single batter."""
        print(f"🔧 Interactive update for: {batter_name}")
        
        # Check if player exists
        player = self.session.query(Player).filter(Player.name == batter_name).first()
        
        if not player:
            print(f"❌ Player {batter_name} not found. Would you like to add them? (y/n)")
            if input().lower().strip() == 'y':
                return self._interactive_add_player(batter_name)
            return
        
        # Show current info
        print(f"\nCurrent player info:")
        print(f"  • batter_type: {player.batter_type or 'None'}")
        print(f"  • bowler_type: {player.bowler_type or 'None'}")
        print(f"  • bowl_hand: {player.bowl_hand or 'None'}")
        print(f"  • bowl_type: {player.bowl_type or 'None'}")
        print(f"  • nationality: {player.nationality or 'None'}")
        
        # Show batter stats
        stats = self.get_batter_stats(batter_name)
        print(f"\nBatter statistics:")
        print(f"  • Total balls faced/at crease: {stats['total_balls']:,}")
        print(f"  • As striker: {stats['striker_balls']:,}")
        print(f"  • As non-striker: {stats['non_striker_balls']:,}")
        print(f"  • Matches played: {stats['matches_played']:,}")
        
        # Get updates
        updates = {}
        
        print(f"\nEnter new values (press Enter to keep current):")
        
        new_batter_type = input(f"batter_type [{player.batter_type or ''}]: ").strip()
        if new_batter_type:
            updates['new_batter_type'] = new_batter_type
        
        new_bowler_type = input(f"bowler_type [{player.bowler_type or ''}]: ").strip()
        if new_bowler_type:
            updates['bowler_type'] = new_bowler_type
            
        new_bowl_hand = input(f"bowl_hand [{player.bowl_hand or ''}]: ").strip()
        if new_bowl_hand:
            updates['bowl_hand'] = new_bowl_hand
            
        new_bowl_type = input(f"bowl_type [{player.bowl_type or ''}]: ").strip()
        if new_bowl_type:
            updates['bowl_type'] = new_bowl_type
        
        new_nationality = input(f"nationality [{player.nationality or ''}]: ").strip()
        if new_nationality:
            updates['nationality'] = new_nationality
        
        if updates:
            if 'new_batter_type' in updates:
                self.update_existing_player(batter_name, updates)
            else:
                # Direct update for other fields
                for field, value in updates.items():
                    setattr(player, field, value)
                self.session.commit()
                print(f"✅ Updated {batter_name}: {', '.join(f'{k}: {v}' for k, v in updates.items())}")
        else:
            print("⚠️  No changes made")
    
    def _interactive_add_player(self, batter_name: str):
        """Interactive addition of new player."""
        print(f"➕ Adding new player: {batter_name}")
        
        # Show batter stats first
        stats = self.get_batter_stats(batter_name)
        print(f"\nBatter statistics:")
        print(f"  • Total balls faced/at crease: {stats['total_balls']:,}")
        print(f"  • As striker: {stats['striker_balls']:,}")
        print(f"  • As non-striker: {stats['non_striker_balls']:,}")
        print(f"  • Matches played: {stats['matches_played']:,}")
        
        batter_data = {}
        
        batter_data['new_batter_type'] = input("batter_type (LHB/RHB): ").strip() or None
        batter_data['bowler_type'] = input("bowler_type (LO/LM/RL/RM/RO/etc, optional): ").strip() or None
        batter_data['bowl_hand'] = input("bowl_hand (Left/Right, optional): ").strip() or None  
        batter_data['bowl_type'] = input("bowl_type (Pace/Spin/etc, optional): ").strip() or None
        batter_data['nationality'] = input("nationality (optional): ").strip() or None
        
        self.add_new_player(batter_name, batter_data)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Enhanced player info update with batter_type validation')
    parser.add_argument('--csv', help='CSV file to process (batter updates)')
    parser.add_argument('--find-missing-batters', action='store_true', help='Find batters missing from players table')
    parser.add_argument('--find-incomplete-batters', action='store_true', help='Find batters with empty batter_type')
    parser.add_argument('--find-all-batter-issues', action='store_true', help='Find all batter issues and export to CSV')
    parser.add_argument('--single-update', help='Single batter name to update interactively')
    parser.add_argument('--export-csv', help='Export batter issues to specified CSV file')
    
    args = parser.parse_args()
    
    if not any([args.csv, args.find_missing_batters, args.find_incomplete_batters, 
                args.find_all_batter_issues, args.single_update]):
        print("❌ Please provide one of the available options")
        parser.print_help()
        sys.exit(1)
    
    print("🏏 Starting Enhanced Player Info Update...")
    print("="*60)
    
    with EnhancedPlayerInfoUpdater() as updater:
        if args.find_missing_batters:
            missing_batters = updater.find_missing_batters()
            if missing_batters:
                print(f"\n📋 First 10 missing batters:")
                for i, batter in enumerate(sorted(missing_batters)[:10]):
                    print(f"   {i+1}. {batter}")
                if len(missing_batters) > 10:
                    print(f"   ... and {len(missing_batters) - 10} more")
        
        elif args.find_incomplete_batters:
            incomplete_batters = updater.find_incomplete_batters()
            if incomplete_batters:
                print(f"\n📋 First 10 batters with empty batter_type:")
                for i, batter in enumerate(sorted(incomplete_batters)[:10]):
                    print(f"   {i+1}. {batter}")
                if len(incomplete_batters) > 10:
                    print(f"   ... and {len(incomplete_batters) - 10} more")
        
        elif args.find_all_batter_issues:
            batter_issues = updater.find_all_batter_issues()
            
            # Export to CSV
            csv_file = args.export_csv or None
            exported_file = updater.export_batter_issues_csv(batter_issues, csv_file)
            
            print(f"\n📄 Next steps:")
            print(f"   1. Open {exported_file}")
            print(f"   2. Fill in the 'new_batter_type' column (LHB/RHB)")
            print(f"   3. Optionally fill other columns if known")
            print(f"   4. Run: python update_player_info_enhanced.py --csv {exported_file}")
        
        elif args.single_update:
            updater.interactive_single_update(args.single_update)
            
        elif args.csv:
            results = updater.process_batter_updates_csv(args.csv)
            print(f"\n📊 Batter Updates Results:")
            print(f"   • New players added: {results['added']}")
            print(f"   • Existing players updated: {results['updated']}")
            print(f"   • Skipped: {results['skipped']}")
            print(f"   • Errors: {results['errors']}")
            print(f"   • Total processed: {results['added'] + results['updated']}")
    
    print("\n✅ Enhanced player info update process completed!")


if __name__ == "__main__":
    main()
