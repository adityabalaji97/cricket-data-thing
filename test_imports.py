"""
Simple import test for WPA modules
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing imports...")
    
    # Test basic imports
    from wpa_curve_trainer import WPACurveTrainer
    print("✅ wpa_curve_trainer imported successfully")
    
    from wpa_lookup_builder import WPALookupTableBuilder  
    print("✅ wpa_lookup_builder imported successfully")
    
    from wpa_fallback import WPAEngineWithFallback
    print("✅ wpa_fallback imported successfully")
    
    # Test initialization
    trainer = WPACurveTrainer()
    print("✅ WPACurveTrainer initialized")
    
    lookup_builder = WPALookupTableBuilder(trainer)
    print("✅ WPALookupTableBuilder initialized")
    
    engine = WPAEngineWithFallback()
    print("✅ WPAEngineWithFallback initialized")
    
    print("\n🎉 All WPA modules imported and initialized successfully!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
