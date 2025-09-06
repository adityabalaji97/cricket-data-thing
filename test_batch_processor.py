"""
Test script for batch processor - basic functionality test
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from batch_processor import PrecomputationPipeline
from datetime import date
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_batch_processor_basic():
    """Test basic batch processor functionality."""
    print("🔧 Testing Batch Processor Basic Functionality")
    print("=" * 50)
    
    try:
        # Initialize pipeline
        pipeline = PrecomputationPipeline()
        print("✅ Pipeline initialized successfully")
        
        # Test with a safe date (not too much data)
        test_date = date(2025, 12, 31)  # Process recent data to see actual results
        print(f"📅 Testing with date: {test_date}")
        
        # Execute pipeline
        result = pipeline.execute_weekly_rebuild(test_date)
        
        print("\n📊 Pipeline Results:")
        print(f"Status: {result['status']}")
        print(f"Duration: {result.get('total_duration_seconds', 0):.2f} seconds")
        print(f"Total records processed: {result['total_records_processed']}")
        
        # Show step details
        print("\n📋 Step Details:")
        for step_name, step_result in result.get('steps', {}).items():
            status = step_result.get('status', 'unknown')
            duration = step_result.get('duration_seconds', 0)
            print(f"  {step_name}: {status} ({duration:.2f}s)")
        
        if result['status'] == 'completed':
            print("\n✅ Basic batch processor test PASSED!")
        else:
            print(f"\n❌ Test failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_processor_basic()
