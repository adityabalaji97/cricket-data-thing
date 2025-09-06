#!/bin/bash

echo "=== Context Model Testing Suite ==="
echo ""

cd /Users/adityabalaji/cdt/cricket-data-thing

echo "1. Running basic import test..."
python basic_test.py

echo ""
echo "2. Running comprehensive test..."
python comprehensive_test.py

echo ""
echo "=== Testing Complete ==="
