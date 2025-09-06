"""
Excel Data Inspector for T20_masterPlayers.xlsx

Quick inspection script to verify the Excel file structure and data
before running the player data update.
"""

import pandas as pd
import sys


def inspect_excel_data(excel_path: str):
    """
    Inspect Excel file structure and provide summary.
    
    Args:
        excel_path: Path to Excel file
    """
    try:
        # Load Excel file
        df = pd.read_excel(excel_path)
        
        print("=== T20_masterPlayers.xlsx Data Inspection ===")
        print(f"Total rows: {len(df)}")
        print(f"Total columns: {len(df.columns)}")
        print(f"\nColumns found: {list(df.columns)}")
        
        # Check for required columns
        required_columns = ['Player', 'batterType', 'bowlHand', 'bowlType', 'bowlerType']
        print(f"\nRequired columns: {required_columns}")
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
        else:
            print("✅ All required columns found")
        
        # Sample data preview
        print(f"\n=== Sample Data (first 5 rows) ===")
        for col in required_columns:
            if col in df.columns:
                print(f"\n{col}:")
                sample_values = df[col].head().tolist()
                print(f"  Sample values: {sample_values}")
                unique_count = df[col].nunique()
                null_count = df[col].isnull().sum()
                print(f"  Unique values: {unique_count}, Null values: {null_count}")
        
        # Check for specific data types we expect
        if 'batterType' in df.columns:
            print(f"\n=== batterType Analysis ===")
            batter_types = df['batterType'].value_counts()
            print(f"batterType distribution:\n{batter_types}")
        
        if 'bowlerType' in df.columns:
            print(f"\n=== bowlerType Analysis ===")
            bowler_types = df['bowlerType'].value_counts()
            print(f"bowlerType distribution:\n{bowler_types}")
            
        return True
        
    except Exception as e:
        print(f"Error inspecting Excel file: {e}")
        return False


if __name__ == "__main__":
    excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
    
    success = inspect_excel_data(excel_path)
    
    if success:
        print("\n✅ Excel inspection completed successfully")
        print("You can now proceed with the player data update.")
    else:
        print("\n❌ Excel inspection failed")
        sys.exit(1)
