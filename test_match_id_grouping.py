#!/usr/bin/env python3

"""
Test script to verify that match_id can be used in group_by queries.
This script tests the new match_id grouping functionality.
"""

import requests
import json
from datetime import datetime

def test_match_id_grouping():
    """Test match_id grouping functionality"""
    
    base_url = "http://localhost:8000"  # Adjust if your API runs on different port
    
    print("Testing match_id grouping functionality...")
    print("=" * 50)
    
    # Test 1: Check if match_id is available in columns endpoint
    print("\n1. Checking available columns...")
    try:
        response = requests.get(f"{base_url}/query/deliveries/columns")
        if response.status_code == 200:
            columns_data = response.json()
            group_by_columns = columns_data.get("group_by_columns", [])
            
            if "match_id" in group_by_columns:
                print("✅ match_id is available in group_by_columns")
                print(f"   Available columns: {group_by_columns}")
            else:
                print("❌ match_id NOT found in group_by_columns")
                print(f"   Available columns: {group_by_columns}")
                return False
        else:
            print(f"❌ Failed to fetch columns: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching columns: {e}")
        return False
    
    # Test 2: Try a simple query with match_id grouping
    print("\n2. Testing simple match_id grouping...")
    try:
        params = {
            "group_by": ["match_id"],
            "leagues": ["IPL"],
            "limit": 5,
            "min_balls": 50  # Only matches with at least 50 balls
        }
        
        response = requests.get(f"{base_url}/query/deliveries", params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            
            if results:
                print(f"✅ Successfully grouped by match_id. Found {len(results)} matches")
                print("   Sample result:")
                print(f"   {json.dumps(results[0], indent=4)}")
            else:
                print("⚠️  Query successful but no results returned")
                
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error in match_id grouping query: {e}")
        return False
    
    # Test 3: Try combined grouping with match_id and another column
    print("\n3. Testing combined grouping (match_id + innings)...")
    try:
        params = {
            "group_by": ["match_id", "innings"],
            "leagues": ["IPL"],
            "limit": 10,
            "min_balls": 20
        }
        
        response = requests.get(f"{base_url}/query/deliveries", params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            
            if results:
                print(f"✅ Successfully grouped by match_id + innings. Found {len(results)} groups")
                print("   Sample result:")
                print(f"   {json.dumps(results[0], indent=4)}")
            else:
                print("⚠️  Query successful but no results returned")
                
        else:
            print(f"❌ Combined grouping failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error in combined grouping query: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All tests passed! match_id grouping is working correctly.")
    return True

if __name__ == "__main__":
    success = test_match_id_grouping()
    if not success:
        exit(1)
    else:
        print("\n🎉 match_id grouping implementation is ready!")
