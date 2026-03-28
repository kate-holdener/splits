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
    --windowed \
    --name "IntervalTimer" \
    --icon "icon/icon.icns" \
    --osx-bundle-identifier "com.intervaltraining.app" \
    --add-data "src/gui/html:src/gui/html" \
    --add-data "src:src" \
    --hidden-import=smartcard \
    --hidden-import=smartcard.scard \
    --hidden-import=smartcard.util \
    --hidden-import=pyllrp \
    --hidden-import=sllurp \
    --hidden-import=sllurp.llrp \
    --hidden-import=reportlab \
    --hidden-import=requests \
    --hidden-import=webview \
    --collect-submodules=webview \
    --collect-submodules=smartcard \
    --collect-submodules=pyscard \
    --collect-submodules=sllurp \
    --noconfirm \
    main.py
echo "Build completed successfully!"
echo "Executable location: dist/IntervalTimer"

if [ -d "dist/IntervalTimer.app" ]; then
    echo "✓ App bundle created successfully"
    ls -lh dist/
else
    echo "✗ App bundle not found!"
    exit 1
fi
echo ""
echo "To test the executable:"
echo "  cd dist"
echo "  ./IntervalTimer"
