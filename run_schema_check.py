#!/usr/bin/env python3

import subprocess
import sys
import os

# Change to project directory
os.chdir('/Users/adityabalaji/cdt/cricket-data-thing')

try:
    # Run the schema check
    result = subprocess.run([sys.executable, 'check_schema.py'], 
                          capture_output=True, text=True, timeout=30)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
except subprocess.TimeoutExpired:
    print("Script timed out after 30 seconds")
except Exception as e:
    print(f"Error running script: {e}")
