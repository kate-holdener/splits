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

# Bake environment variables into a runtime hook so os.getenv() works in the
# frozen app. Values come from the environment (set via GitHub Actions secrets
# in CI, or exported locally for manual builds).
echo "Generating runtime hook from environment..."
python3 - << 'PYEOF'
import os
vars_to_embed = [
    'SMTP_HOST', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_SENDER_NAME',
    'SMTP_PASSWORD', 'SMTP_SENDER_EMAIL', 'GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET',
]
lines = ['import os']
for var in vars_to_embed:
    val = os.environ.get(var, '')
    if val:
        lines.append(f'os.environ.setdefault({var!r}, {val!r})')
with open('runtime_hook.py', 'w') as f:
    f.write('\n'.join(lines) + '\n')
PYEOF

# Build the executable
echo "Building executable..."
pyinstaller \
    --name "Splits" \
    --icon "icon/icon.icns" \
    --osx-bundle-identifier "com.splits.app" \
    --runtime-hook=runtime_hook.py \
    --add-data "src/gui/html:src/gui/html" \
    --add-data "src:src" \
    --add-data "data:data" \
    --hidden-import=dotenv \
    --hidden-import=smartcard \
    --hidden-import=smartcard.scard \
    --hidden-import=smartcard.util \
    --hidden-import=pyllrp \
    --hidden-import=sllurp \
    --hidden-import=sllurp.llrp \
    --hidden-import=reportlab \
    --hidden-import=requests \
    --hidden-import=webview \
    --collect-all=webview \
    --collect-all=dotenv \
    --collect-submodules=smartcard \
    --collect-binaries=smartcard \
    --collect-submodules=sllurp \
    --noconfirm \
    main.py
echo "Build completed successfully!"
echo "Executable location: dist/Splits"

if [ -d "dist/Splits.app" ]; then
    echo "✓ App bundle created successfully"
    ls -lh dist/
else
    echo "✗ App bundle not found!"
    exit 1
fi
echo ""
echo "To test the executable:"
echo "  cd dist"
echo "  ./Splits"
