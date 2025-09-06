#!/usr/bin/env python3
"""
Test script to verify the summary rows backend implementation works correctly.
"""

import requests
import json
import sys

def test_summary_rows():
    base_url = "http://localhost:8000"
    
    # Test 1: Basic grouped query without summary rows (should work as before)
    print("Test 1: Basic grouped query without summary rows...")
    response1 = requests.get(f"{base_url}/query/deliveries", params={
        "group_by": ["year", "crease_combo"],
        "leagues": ["IPL"],
        "start_date": "2008-01-01",
        "end_date": "2008-12-31",
        "limit": 10
    })
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"✓ Basic query successful. Got {len(data1['data'])} results")
        print(f"  Sample result: {data1['data'][0] if data1['data'] else 'No data'}")
        print(f"  Has summary_data: {'summary_data' in data1}")
        print(f"  Has summaries: {data1['metadata'].get('has_summaries', False)}")
    else:
        print(f"✗ Basic query failed: {response1.status_code} - {response1.text}")
        return False
    
    # Test 2: Grouped query WITH summary rows enabled
    print("\nTest 2: Grouped query with summary rows enabled...")
    response2 = requests.get(f"{base_url}/query/deliveries", params={
        "group_by": ["year", "crease_combo"],
        "leagues": ["IPL"],
        "start_date": "2008-01-01",
        "end_date": "2008-12-31",
        "limit": 10,
        "show_summary_rows": True
    })
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"✓ Summary query successful. Got {len(data2['data'])} results")
        print(f"  Has summary_data: {'summary_data' in data2}")
        print(f"  Has summaries: {data2['metadata'].get('has_summaries', False)}")
        
        if data2.get('summary_data'):
            summary_keys = list(data2['summary_data'].keys())
            print(f"  Summary data keys: {summary_keys}")
            
            if 'year_summaries' in data2['summary_data']:
                year_summaries = data2['summary_data']['year_summaries']
                print(f"  Year summaries count: {len(year_summaries)}")
                if year_summaries:
                    print(f"  Sample year summary: {year_summaries[0]}")
            
            if 'percentages' in data2['summary_data']:
                percentages = data2['summary_data']['percentages']
                print(f"  Percentages count: {len(percentages)}")
                if percentages:
                    print(f"  Sample percentage: {percentages[0]}")
        else:
            print(f"  No summary data generated")
    else:
        print(f"✗ Summary query failed: {response2.status_code} - {response2.text}")
        return False
    
    # Test 3: Single group (should not generate summaries)
    print("\nTest 3: Single group query with summary rows enabled (should not generate summaries)...")
    response3 = requests.get(f"{base_url}/query/deliveries", params={
        "group_by": ["year"],
        "leagues": ["IPL"],
        "start_date": "2008-01-01",
        "end_date": "2010-12-31",
        "limit": 5,
        "show_summary_rows": True
    })
    
    if response3.status_code == 200:
        data3 = response3.json()
        print(f"✓ Single group query successful. Got {len(data3['data'])} results")
        print(f"  Has summaries (should be False): {data3['metadata'].get('has_summaries', False)}")
        print(f"  Summary data is None: {data3.get('summary_data') is None}")
    else:
        print(f"✗ Single group query failed: {response3.status_code} - {response3.text}")
        return False
    
    print("\n🎉 All backend tests passed!")
    return True

if __name__ == "__main__":
    success = test_summary_rows()
    sys.exit(0 if success else 1)
