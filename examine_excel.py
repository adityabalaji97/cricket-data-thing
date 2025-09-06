#!/usr/bin/env python3
"""
Script to examine the T20_masterPlayers.xlsx file structure
"""

import pandas as pd
import os

def examine_excel_file(file_path):
    """Examine the Excel file structure"""
    try:
        print(f"Examining Excel file: {file_path}")
        
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        print(f"\nBasic Info:")
        print(f"- Total rows: {len(df)}")
        print(f"- Total columns: {len(df.columns)}")
        
        print(f"\nColumn names:")
        for i, col in enumerate(df.columns):
            print(f"  {i}: '{col}'")
        
        print(f"\nFirst 5 rows:")
        print(df.head())
        
        print(f"\nData types:")
        print(df.dtypes)
        
        print(f"\nSample values for key columns:")
        key_columns = ['Player', 'batterType', 'bowlerType', 'bowlHand', 'bowlType']
        for col in key_columns:
            if col in df.columns:
                print(f"\n{col}:")
                unique_vals = df[col].dropna().unique()[:10]  # First 10 unique values
                print(f"  Unique values (first 10): {list(unique_vals)}")
                print(f"  Total unique: {len(df[col].dropna().unique())}")
                print(f"  Null count: {df[col].isna().sum()}")
            else:
                print(f"\n{col}: Column not found!")
        
        return True
        
    except Exception as e:
        print(f"Error examining Excel file: {str(e)}")
        return False

def main():
    """Main function"""
    excel_file = '/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx'
    
    if not os.path.exists(excel_file):
        print(f"Excel file not found: {excel_file}")
        return False
    
    return examine_excel_file(excel_file)

if __name__ == "__main__":
    main()
