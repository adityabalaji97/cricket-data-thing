#!/usr/bin/env python3
"""
Script to update players table with latest data from T20_masterPlayers.xlsx

This script:
1. Reads T20_masterPlayers.xlsx 
2. Deletes all existing records from players table
3. Repopulates with fresh data from Excel

Column mapping:
Player -> name
batterType -> batter_type  
bowlerType -> bowler_type
bowlHand -> bowl_hand
bowlType -> bowl_type
"""

import pandas as pd
import os
import sys
from sqlalchemy import create_engine, text
from models import Base, Player
from database import get_database_url

def read_excel_data(excel_path):
    """Read and validate Excel file"""
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    
    print(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    
    print(f"Loaded {len(df)} rows from Excel")
    print(f"Columns: {list(df.columns)}")
    
    # Validate required columns exist
    required_columns = ['Player', 'batterType', 'bowlerType', 'bowlHand', 'bowlType']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    return df

def clean_and_transform_data(df):
    """Clean and transform Excel data for database insertion"""
    print("Cleaning and transforming data...")
    
    # Create a copy to avoid modifying original
    clean_df = df.copy()
    
    # Remove rows where Player name is null/empty
    initial_count = len(clean_df)
    clean_df = clean_df.dropna(subset=['Player'])
    clean_df = clean_df[clean_df['Player'].str.strip() != '']
    
    print(f"Removed {initial_count - len(clean_df)} rows with empty player names")
    
    # Clean string columns - strip whitespace and handle nulls
    string_columns = ['Player', 'batterType', 'bowlerType', 'bowlHand', 'bowlType']
    for col in string_columns:
        if col in clean_df.columns:
            # Convert to string and strip whitespace
            clean_df[col] = clean_df[col].astype(str).str.strip()
            # Replace 'nan' string with None
            clean_df[col] = clean_df[col].replace('nan', None)
            # Replace empty strings with None
            clean_df[col] = clean_df[col].replace('', None)
    
    # Remove duplicates based on Player name (keep first occurrence)
    initial_count = len(clean_df)
    clean_df = clean_df.drop_duplicates(subset=['Player'], keep='first')
    print(f"Removed {initial_count - len(clean_df)} duplicate player records")
    
    return clean_df

def update_players_table(df):
    """Update players table with new data"""
    print("Connecting to database...")
    
    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    try:
        with engine.begin() as conn:
            print("Deleting existing players records...")
            # Delete all existing records
            result = conn.execute(text("DELETE FROM players"))
            print(f"Deleted {result.rowcount} existing records")
            
            print("Inserting new players records...")
            # Prepare data for insertion
            records_inserted = 0
            
            for _, row in df.iterrows():
                try:
                    # Map Excel columns to database columns
                    player_data = {
                        'name': row['Player'],
                        'batter_type': row['batterType'] if pd.notna(row['batterType']) else None,
                        'bowler_type': row['bowlerType'] if pd.notna(row['bowlerType']) else None,
                        'bowl_hand': row['bowlHand'] if pd.notna(row['bowlHand']) else None,
                        'bowl_type': row['bowlType'] if pd.notna(row['bowlType']) else None,
                        # Set other columns to None for now
                        'batting_hand': None,
                        'bowling_type': None,
                        'nationality': None,
                        'league_teams': None
                    }
                    
                    # Insert record
                    insert_query = text("""
                        INSERT INTO players (name, batter_type, bowler_type, bowl_hand, bowl_type, 
                                           batting_hand, bowling_type, nationality, league_teams)
                        VALUES (:name, :batter_type, :bowler_type, :bowl_hand, :bowl_type,
                                :batting_hand, :bowling_type, :nationality, :league_teams)
                    """)
                    
                    conn.execute(insert_query, player_data)
                    records_inserted += 1
                    
                except Exception as e:
                    print(f"Error inserting player {row['Player']}: {str(e)}")
                    continue
            
            print(f"Successfully inserted {records_inserted} player records")
            
    except Exception as e:
        print(f"Database error: {str(e)}")
        raise
    finally:
        engine.dispose()

def main():
    """Main function"""
    try:
        excel_path = '/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx'
        
        # Read Excel data
        df = read_excel_data(excel_path)
        
        # Clean and transform data
        clean_df = clean_and_transform_data(df)
        
        print(f"Final dataset: {len(clean_df)} players ready for insertion")
        
        # Show sample of data
        print("\nSample of data to be inserted:")
        sample_cols = ['Player', 'batterType', 'bowlerType', 'bowlHand', 'bowlType']
        print(clean_df[sample_cols].head(10).to_string(index=False))
        
        # Confirm before proceeding
        confirm = input("\nProceed with updating players table? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled")
            return
        
        # Update database
        update_players_table(clean_df)
        
        print("\nPlayers table update completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
