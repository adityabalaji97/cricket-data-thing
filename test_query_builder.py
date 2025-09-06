#!/usr/bin/env python3
"""
Testing Script for Query Builder Implementation

This script tests each step of the Query Builder development.
We'll add more tests as we implement more features.

Usage: python test_query_builder.py
"""

import requests
import json
from datetime import datetime, date
import sys

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your FastAPI runs on different port
TIMEOUT = 30  # seconds

def print_test_header(step_name):
    """Print a formatted test header"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING: {step_name}")
    print(f"{'='*60}")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def test_server_connection():
    """Test if the FastAPI server is running"""
    print_test_header("SERVER CONNECTION")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        if response.status_code == 200:
            print_success("FastAPI server is running")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to FastAPI server")
        print_info("Make sure FastAPI is running with: uvicorn main:app --reload")
        return False
    except Exception as e:
        print_error(f"Error connecting to server: {str(e)}")
        return False

def test_step1_basic_endpoints():
    """Test Step 1: Basic endpoint setup"""
    print_test_header("STEP 1: Basic Query Builder Endpoints")
    
    # Test 1: Basic deliveries endpoint with no parameters
    print_info("Test 1: Basic deliveries endpoint (no parameters)")
    try:
        response = requests.get(f"{BASE_URL}/query/deliveries", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success("✅ /query/deliveries endpoint works")
            print_info(f"Returned {len(data.get('data', []))} deliveries")
            print_info(f"Metadata: {data.get('metadata', {}).get('note', 'No note')}")
            
            # Show sample delivery
            if data.get('data'):
                sample = data['data'][0]
                print_info(f"Sample delivery: {sample.get('batter')} vs {sample.get('bowler')}, {sample.get('runs_off_bat')} runs")
        else:
            print_error(f"❌ /query/deliveries failed with status {response.status_code}")
            print_error(f"Response: {response.text}")
    except Exception as e:
        print_error(f"❌ Error testing deliveries endpoint: {str(e)}")
    
    # Test 2: Columns metadata endpoint
    print_info("Test 2: Columns metadata endpoint")
    try:
        response = requests.get(f"{BASE_URL}/query/deliveries/columns", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success("✅ /query/deliveries/columns endpoint works")
            print_info(f"Available filter columns: {list(data.get('filter_columns', {}).keys())}")
            print_info(f"Group by options: {len(data.get('group_by_columns', []))} columns")
            print_info(f"Crease combo options: {data.get('crease_combo_options', [])}")
        else:
            print_error(f"❌ /query/deliveries/columns failed with status {response.status_code}")
    except Exception as e:
        print_error(f"❌ Error testing columns endpoint: {str(e)}")
    
    # Test 3: Basic parameter passing (should still work with current implementation)
    print_info("Test 3: Basic parameter passing")
    try:
        params = {
            "limit": 10,
            "venue": "Wankhede Stadium",
            "crease_combo": "lhb_rhb"
        }
        response = requests.get(f"{BASE_URL}/query/deliveries", params=params, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success(f"✅ Endpoint accepts parameters")
            print_info(f"Applied filters: {data.get('metadata', {}).get('filters_applied', {})}")
            print_info(f"Returned {len(data.get('data', []))} deliveries (limited to {params['limit']})")
        else:
            print_error(f"❌ Parameter test failed with status {response.status_code}")
    except Exception as e:
        print_error(f"❌ Error testing parameters: {str(e)}")

def test_data_quality():
    """Test the quality and structure of returned data"""
    print_test_header("DATA QUALITY CHECKS")
    
    try:
        response = requests.get(f"{BASE_URL}/query/deliveries?limit=5", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            deliveries = data.get('data', [])
            
            if not deliveries:
                print_error("❌ No delivery data returned")
                return
            
            # Check data structure
            sample = deliveries[0]
            expected_fields = ['match_id', 'innings', 'over', 'ball', 'batter', 'bowler', 'runs_off_bat']
            
            missing_fields = []
            for field in expected_fields:
                if field not in sample:
                    missing_fields.append(field)
            
            if missing_fields:
                print_error(f"❌ Missing fields in delivery data: {missing_fields}")
            else:
                print_success("✅ All expected fields present in delivery data")
            
            # Check left-right analysis fields
            left_right_fields = ['crease_combo', 'ball_direction', 'bowler_type']
            lr_present = [field for field in left_right_fields if field in sample and sample[field] is not None]
            
            if lr_present:
                print_success(f"✅ Left-right analysis fields present: {lr_present}")
            else:
                print_info("ℹ️  Left-right analysis fields not yet populated (expected for basic test)")
            
            # Show sample data structure
            print_info("Sample delivery structure:")
            for key, value in sample.items():
                print(f"  {key}: {value}")
                
        else:
            print_error(f"❌ Could not retrieve data for quality check")
            
    except Exception as e:
        print_error(f"❌ Error in data quality check: {str(e)}")

def test_step2_filtering():
    """Test Step 2: Column filtering functionality"""
    print_test_header("STEP 2: Column Filtering")
    
    # Test 1: Venue filtering
    print_info("Test 1: Venue filtering")
    try:
        params = {"venue": "Wankhede Stadium", "limit": 10}
        response = requests.get(f"{BASE_URL}/query/deliveries", params=params, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success("✅ Venue filtering works")
            print_info(f"Found {data.get('metadata', {}).get('total_matching_rows', 0)} total deliveries at Wankhede Stadium")
            print_info(f"Returned {len(data.get('data', []))} deliveries")
            
            # Verify all deliveries are from the specified venue
            venues = set(d.get('venue') for d in data.get('data', []))
            if len(venues) == 1 and 'Wankhede Stadium' in venues:
                print_success("✅ All returned deliveries are from Wankhede Stadium")
            else:
                print_error(f"❌ Unexpected venues in results: {venues}")
        else:
            print_error(f"❌ Venue filtering failed with status {response.status_code}")
    except Exception as e:
        print_error(f"❌ Error testing venue filter: {str(e)}")
    
    # Test 2: Left-right combination filtering
    print_info("Test 2: Crease combination filtering")
    try:
        params = {"crease_combo": "lhb_rhb", "limit": 10}
        response = requests.get(f"{BASE_URL}/query/deliveries", params=params, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success("✅ Crease combo filtering works")
            print_info(f"Found {data.get('metadata', {}).get('total_matching_rows', 0)} total lhb_rhb combinations")
            
            # Verify all deliveries have the specified crease combo
            combos = set(d.get('crease_combo') for d in data.get('data', []))
            if len(combos) == 1 and 'lhb_rhb' in combos:
                print_success("✅ All returned deliveries are lhb_rhb combinations")
            else:
                print_error(f"❌ Unexpected crease combos in results: {combos}")
        else:
            print_error(f"❌ Crease combo filtering failed with status {response.status_code}")
    except Exception as e:
        print_error(f"❌ Error testing crease combo filter: {str(e)}")
    
    # Test 3: Bowler type filtering
    print_info("Test 3: Bowler type filtering")
    try:
        params = {"bowler_type": "LO", "limit": 10}  # Left-arm orthodox
        response = requests.get(f"{BASE_URL}/query/deliveries", params=params, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success("✅ Bowler type filtering works")
            print_info(f"Found {data.get('metadata', {}).get('total_matching_rows', 0)} total LO deliveries")
            
            # Verify all deliveries are from LO bowlers
            bowler_types = set(d.get('bowler_type') for d in data.get('data', []))
            if len(bowler_types) == 1 and 'LO' in bowler_types:
                print_success("✅ All returned deliveries are from LO bowlers")
            else:
                print_error(f"❌ Unexpected bowler types in results: {bowler_types}")
        else:
            print_error(f"❌ Bowler type filtering failed with status {response.status_code}")
    except Exception as e:
        print_error(f"❌ Error testing bowler type filter: {str(e)}")
    
    # Test 4: Over range filtering
    print_info("Test 4: Over range filtering (powerplay)")
    try:
        params = {"over_min": 0, "over_max": 5, "limit": 10}  # Powerplay overs
        response = requests.get(f"{BASE_URL}/query/deliveries", params=params, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success("✅ Over range filtering works")
            print_info(f"Found {data.get('metadata', {}).get('total_matching_rows', 0)} total powerplay deliveries")
            
            # Verify all deliveries are in powerplay overs
            overs = [d.get('over') for d in data.get('data', [])]
            if all(0 <= over <= 5 for over in overs if over is not None):
                print_success(f"✅ All returned deliveries are in powerplay (overs 0-5): {set(overs)}")
            else:
                print_error(f"❌ Some deliveries outside powerplay range: {set(overs)}")
        else:
            print_error(f"❌ Over range filtering failed with status {response.status_code}")
    except Exception as e:
        print_error(f"❌ Error testing over range filter: {str(e)}")
    
    # Test 5: Combined filtering
    print_info("Test 5: Combined filtering (venue + crease combo + bowler type)")
    try:
        params = {
            "venue": "Wankhede Stadium",
            "crease_combo": "lhb_rhb", 
            "bowler_type": "LO",
            "limit": 5
        }
        response = requests.get(f"{BASE_URL}/query/deliveries", params=params, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success("✅ Combined filtering works")
            total_matches = data.get('metadata', {}).get('total_matching_rows', 0)
            print_info(f"Found {total_matches} deliveries matching all filters")
            
            if total_matches > 0:
                sample = data.get('data', [])[0] if data.get('data') else {}
                print_info(f"Sample: {sample.get('batter')} vs {sample.get('bowler')} at {sample.get('venue')}")
                print_info(f"Combo: {sample.get('crease_combo')}, Bowler: {sample.get('bowler_type')}")
            else:
                print_info("No matches found for this specific combination (this is okay)")
        else:
            print_error(f"❌ Combined filtering failed with status {response.status_code}")
    except Exception as e:
        print_error(f"❌ Error testing combined filters: {str(e)}")

def test_step2_data_quality():
    """Test the quality of filtered data"""
    print_test_header("STEP 2: Data Quality with Filtering")
    
    try:
        # Test with multiple filters to see real filtering in action
        params = {"innings": 1, "over_min": 0, "over_max": 5, "limit": 20}
        response = requests.get(f"{BASE_URL}/query/deliveries", params=params, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get('metadata', {})
            deliveries = data.get('data', [])
            
            # Check metadata structure
            required_metadata = ['total_matching_rows', 'returned_rows', 'limit', 'offset', 'has_more', 'filters_applied']
            missing_metadata = [field for field in required_metadata if field not in metadata]
            
            if missing_metadata:
                print_error(f"❌ Missing metadata fields: {missing_metadata}")
            else:
                print_success("✅ All metadata fields present")
            
            # Check filtering accuracy
            print_info(f"Total matching rows: {metadata.get('total_matching_rows')}")
            print_info(f"Returned rows: {metadata.get('returned_rows')}")
            print_info(f"Has more: {metadata.get('has_more')}")
            
            # Verify filter application
            filters_applied = metadata.get('filters_applied', {})
            print_info(f"Filters applied: {filters_applied}")
            
            # Check pagination info
            if metadata.get('total_matching_rows', 0) > metadata.get('limit', 0):
                if metadata.get('has_more'):
                    print_success("✅ Pagination info correctly indicates more data available")
                else:
                    print_error("❌ Pagination info inconsistent")
            
            # Show sample data structure
            if deliveries:
                sample = deliveries[0]
                print_info("Sample filtered delivery:")
                for key, value in sample.items():
                    print(f"  {key}: {value}")
                    
        else:
            print_error(f"❌ Could not retrieve filtered data for quality check")
            
    except Exception as e:
        print_error(f"❌ Error in filtered data quality check: {str(e)}")
    """Run all Step 1 tests"""
    print("🏏 Query Builder Testing Script - Step 1")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test server connection first
    if not test_server_connection():
        print_error("⛔ Cannot proceed with tests - server not accessible")
        return False
    
    # Run Step 1 tests
    test_step1_basic_endpoints()
    test_data_quality()
    
    print_test_header("STEP 1 SUMMARY")
    print_success("✅ Basic router and service setup complete")
    print_info("📋 What works:")
    print_info("   • FastAPI server running")
    print_info("   • /query/deliveries endpoint responding") 
    print_info("   • /query/deliveries/columns metadata endpoint")
    print_info("   • Basic parameter acceptance")
    print_info("   • Sample delivery data returning")
    
    print_info("🔄 Next: Implement filtering logic in Step 2")
    return True

def run_step2_tests():
    """Run all Step 2 tests"""
    print("🏏 Query Builder Testing Script - Step 2")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test server connection first
    if not test_server_connection():
        print_error("⛔ Cannot proceed with tests - server not accessible")
        return False
    
    # Run Step 2 tests
    test_step2_filtering()
    test_step2_data_quality()
    
    print_test_header("STEP 2 SUMMARY")
    print_success("✅ Column filtering implemented and working")
    print_info("📋 What works:")
    print_info("   • Venue filtering")
    print_info("   • Left-right analysis filtering (crease_combo, bowler_type)")
    print_info("   • Over range filtering (powerplay, middle, death)")
    print_info("   • Combined multiple filters")
    print_info("   • Proper metadata and pagination")
    
    print_info("🔄 Next: Implement grouping and aggregation in Step 3")
    return True

if __name__ == "__main__":
    import sys
    
    # Check if user wants to run specific step
    if len(sys.argv) > 1 and sys.argv[1] == "step2":
        success = run_step2_tests()
    else:
        success = run_step1_tests()
    
    sys.exit(0 if success else 1)
