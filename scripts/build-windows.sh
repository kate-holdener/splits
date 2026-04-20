#!/bin/bash
# Build script for Windows installer using PyInstaller + NSIS

set -e

echo "Building Splits Application for Windows..."

# Convert PNG icon to ICO format for Windows
echo "Converting icon to .ico..."
if command -v magick &> /dev/null; then
    magick icon/splits.png -define icon:auto-resize="256,128,64,48,32,16" icon/splits.ico
elif command -v convert &> /dev/null; then
    convert icon/splits.png -define icon:auto-resize="256,128,64,48,32,16" icon/splits.ico
else
    echo "ImageMagick not found, using Python (Pillow) to convert icon..."
    python -c "
from PIL import Image
img = Image.open('icon/splits.png').convert('RGBA')
img.save('icon/splits.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
"
fi

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.spec

# Build the executable (onefile bundles Python + all deps into a single .exe)
echo "Building executable..."
pyinstaller \
    --onefile \
    --name "Splits" \
    --icon "icon/splits.ico" \
    --add-data "src/gui/html;src/gui/html" \
    --add-data "data;data" \
    --add-data "src;src" \
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

if [ ! -f "dist/Splits.exe" ]; then
    echo "✗ Executable not found!"
    exit 1
fi
echo "✓ Executable created: dist/Splits.exe"

# Install NSIS if not available, then ensure it's on PATH
if ! command -v makensis &> /dev/null; then
    echo "NSIS not found. Installing via Chocolatey..."
    choco install nsis -y --no-progress
    # Chocolatey doesn't refresh PATH in the current shell, add it manually
    export PATH="$PATH:/c/Program Files (x86)/NSIS"
fi

# Write NSIS installer script
echo "Generating NSIS installer script..."
cat > installer.nsi << 'NSIS_EOF'
!define APP_NAME "Splits"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Splits"
!define APP_EXE "Splits.exe"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "dist\Splits-installer.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin
SetCompressor lzma

; Branding
Icon "icon\splits.ico"
UninstallIcon "icon\splits.ico"

; Pages
Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Splits (required)"
    SectionIn RO
    SetOutPath "$INSTDIR"

    ; Copy application files
    File "dist\${APP_EXE}"
    File "icon\splits.ico"

    ; Desktop shortcut
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" "$INSTDIR\splits.ico" 0

    ; Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" "$INSTDIR\splits.ico" 0
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" \
        "$INSTDIR\Uninstall.exe"

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Add to Windows Add/Remove Programs
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayIcon" "$INSTDIR\splits.ico"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayVersion" "${APP_VERSION}"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\splits.ico"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"

    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    DeleteRegKey HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKLM "Software\${APP_NAME}"
SectionEnd
NSIS_EOF

# Build the installer
echo "Building installer..."
makensis installer.nsi

if [ -f "dist/Splits-installer.exe" ]; then
    echo "✓ Installer created successfully"
    ls -lh dist/Splits-installer.exe
else
    echo "✗ Installer not found!"
    exit 1
fi

echo ""
echo "Installer location: dist/Splits-installer.exe"
