#!/bin/bash
echo "=== Testing AI Behavior Mandate Enforcement ==="
echo ""

# Test 1: Request with TODO placeholders
echo "Test 1: Request code with TODO placeholders"
echo "Input: 'Write a function that TODO: implement later'"
echo ""
echo -e "Development\nWrite a function that TODO: implement later\nexit" | ./build/VersaAIApp | grep -A 50 "Development"
echo "---"
echo ""

# Test 2: Request complete implementation
echo "Test 2: Request complete implementation"
echo "Input: 'Implement a complete binary search function in C++'"
echo ""
echo -e "Development\nImplement a complete binary search function in C++\nexit" | ./build/VersaAIApp | grep -A 50 "Development"
echo "---"
echo ""

# Test 3: User explicitly requests simplified version
echo "Test 3: User explicitly requests simplified version"
echo "Input: 'Please give me a SIMPLE and EASY example of a hash map'"
echo ""
echo -e "Development\nPlease give me a SIMPLE and EASY example of a hash map\nexit" | ./build/VersaAIApp | grep -A 50 "Development"
echo "---"

echo ""
echo "=== All Tests Complete ==="
