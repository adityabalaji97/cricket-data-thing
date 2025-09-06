"""
Player Data Updater for Phase 3: Data Update

Updates the Player table using T20_masterPlayers.xlsx with the mapping:
- Player → name
- batterType → batter_type  
- bowlHand → bowl_hand
- bowlType → bowl_type
- bowlerType → bowler_type

This module follows the PRD requirements for modular, manageable code chunks.
"""

import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from models import Player, Base
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class PlayerDataUpdater:
    """Handles updating player data from Excel file to database."""
    
    def __init__(self, db_url: str, excel_path: str):
        """
        Initialize the player data updater.
        
        Args:
            db_url: Database connection string
            excel_path: Path to T20_masterPlayers.xlsx file
        """
        self.db_url = db_url
        self.excel_path = excel_path
        self.engine = create_engine(db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_excel_data(self) -> pd.DataFrame:
        """
        Load player data from Excel file.
        
        Returns:
            DataFrame with player data from Excel
        """
        try:
            df = pd.read_excel(self.excel_path)
            self.logger.info(f"Loaded {len(df)} rows from Excel file")
            self.logger.info(f"Columns in Excel: {list(df.columns)}")
            return df
        except Exception as e:
            self.logger.error(f"Error loading Excel file: {e}")
            raise
    
    def validate_excel_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that required columns exist in Excel data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if validation passes
        """
        required_columns = ['Player', 'batterType', 'bowlHand', 'bowlType', 'bowlerType']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            self.logger.error(f"Missing required columns: {missing_columns}")
            return False
            
        self.logger.info("Excel data validation passed")
        return True
    
    def get_current_players(self) -> Dict[str, Player]:
        """
        Get current players from database.
        
        Returns:
            Dictionary mapping player name to Player object
        """
        players = self.session.query(Player).all()
        player_dict = {player.name: player for player in players}
        self.logger.info(f"Found {len(player_dict)} existing players in database")
        return player_dict
    
    def process_player_updates(self, df: pd.DataFrame) -> Tuple[int, int, int]:
        """
        Process player data updates from Excel.
        
        Args:
            df: DataFrame with Excel player data
            
        Returns:
            Tuple of (updated_count, new_count, error_count)
        """
        current_players = self.get_current_players()
        updated_count = 0
        new_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                player_name = str(row['Player']).strip()
                
                # Skip empty names
                if pd.isna(player_name) or player_name == '' or player_name == 'nan':
                    continue
                
                # Get or create player
                if player_name in current_players:
                    player = current_players[player_name]
                    action = "updated"
                else:
                    player = Player(name=player_name)
                    self.session.add(player)
                    action = "created"
                    new_count += 1
                
                # Update player attributes according to mapping
                player.batter_type = self._clean_value(row.get('batterType'))
                player.bowl_hand = self._clean_value(row.get('bowlHand'))
                player.bowl_type = self._clean_value(row.get('bowlType'))
                player.bowler_type = self._clean_value(row.get('bowlerType'))
                
                if action == "updated":
                    updated_count += 1
                    
                if (index + 1) % 100 == 0:
                    self.logger.info(f"Processed {index + 1} players...")
                    
            except Exception as e:
                self.logger.error(f"Error processing player {row.get('Player', 'Unknown')}: {e}")
                error_count += 1
                continue
        
        return updated_count, new_count, error_count
    
    def _clean_value(self, value) -> Optional[str]:
        """
        Clean and normalize a value from Excel.
        
        Args:
            value: Raw value from Excel cell
            
        Returns:
            Cleaned string value or None
        """
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return None
        return str(value).strip()
    
    def update_players(self) -> Dict[str, int]:
        """
        Main method to update player data from Excel file.
        
        Returns:
            Dictionary with update statistics
        """
        try:
            # Load and validate Excel data
            df = self.load_excel_data()
            if not self.validate_excel_data(df):
                raise ValueError("Excel data validation failed")
            
            # Process updates
            self.logger.info("Starting player data update process...")
            updated_count, new_count, error_count = self.process_player_updates(df)
            
            # Commit changes
            self.session.commit()
            self.logger.info("Player data update completed successfully")
            
            return {
                'total_processed': len(df),
                'updated': updated_count,
                'new': new_count,
                'errors': error_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error during player update process: {e}")
            raise
        finally:
            self.session.close()


def main():
    """
    Main execution function for player data update.
    """
    # Database configuration - using the same connection as main app
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
    
    updater = PlayerDataUpdater(db_url, excel_path)
    
    try:
        results = updater.update_players()
        print("\n=== Player Data Update Results ===")
        print(f"Total processed: {results['total_processed']}")
        print(f"Updated existing: {results['updated']}")
        print(f"New players added: {results['new']}")
        print(f"Errors: {results['errors']}")
        print(f"Completed at: {results['timestamp']}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
