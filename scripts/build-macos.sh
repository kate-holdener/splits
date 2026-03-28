#!/bin/bash
# Build script for macOS executable using PyInstaller

set -e  # Exit on any error

echo "Building Interval Training Application for macOS..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.spec

# Build the executable
echo "Building executable..."
pyinstaller \
    --onefile \
    --windowed \
    --name "IntervalTraining-macos" \
    --add-data "src/gui/html:src/gui/html" \
    --add-data "data:data" \
    --add-data "src:src" \
    --hidden-import=smartcard \
    --hidden-import=smartcard.scard \
    --hidden-import=smartcard.util \
    --hidden-import=pyllrp \
    --hidden-import=sllurp \
    --hidden-import=reportlab \
    --hidden-import=requests \
    --hidden-import=webview \
    --collect-submodules=webview \
    --collect-submodules=smartcard \
    --collect-submodules=pyscard \
    --noconfirm \
    main.py

echo "Build completed successfully!"
echo "Executable location: dist/IntervalTraining-macos"

# Test if executable exists
if [ -f "dist/IntervalTraining-macos" ]; then
    echo "✓ Executable created successfully"
    ls -lh dist/IntervalTraining-macos
else
    echo "✗ Executable not found!"
    exit 1
fi

echo ""
echo "To test the executable:"
echo "  cd dist"
echo "  ./IntervalTraining-macos"