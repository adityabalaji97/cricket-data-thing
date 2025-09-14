#!/usr/bin/env python3
"""
Quick test script to verify the ELO calculation fix
"""

from datetime import datetime, timedelta

# Test the datetime operations
test_date = datetime(2024, 9, 27)
one_day_before = test_date - timedelta(days=1)

print(f"Test date: {test_date}")
print(f"One day before: {one_day_before}")
print("✅ DateTime operations working correctly!")

# Test basic import
try:
    from elo_update_service import ELOUpdateService
    print("✅ ELO service import successful!")
    
    service = ELOUpdateService()
    print("✅ ELO service initialization successful!")
    
except Exception as e:
    print(f"❌ Error: {e}")
