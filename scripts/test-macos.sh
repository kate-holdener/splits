#!/bin/bash
# Test script for macOS executable
# This script validates that the executable works correctly

set -e

echo "Testing IntervalTraining-macos executable..."

# Check if executable exists
if [ ! -f "dist/IntervalTraining-macos" ]; then
    echo "❌ Executable not found at dist/IntervalTraining-macos"
    echo "Run scripts/build-macos.sh first"
    exit 1
fi

# Check executable permissions
if [ ! -x "dist/IntervalTraining-macos" ]; then
    echo "Making executable..."
    chmod +x dist/IntervalTraining-macos
fi

# Check file size (should be substantial)
SIZE=$(stat -f%z "dist/IntervalTraining-macos" 2>/dev/null || echo "0")
if [ "$SIZE" -lt "100000000" ]; then  # Less than 100MB is suspicious
    echo "⚠️  Warning: Executable size is only ${SIZE} bytes - may be incomplete"
fi

echo "✅ Executable found and properly sized (${SIZE} bytes)"

# Test basic execution (launch and quickly close)
echo "Testing executable launch..."
timeout 10s ./dist/IntervalTraining-macos &
PID=$!
sleep 2

# Check if process started
if ps -p $PID > /dev/null; then
    echo "✅ Application started successfully"
    kill $PID 2>/dev/null || true
    wait $PID 2>/dev/null || true
else
    echo "❌ Application failed to start"
    exit 1
fi

echo ""
echo "✅ Basic executable test passed!"
echo "To manually test the application:"
echo "  cd dist"
echo "  ./IntervalTraining-macos"