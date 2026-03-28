@echo off
REM Build script for Windows executable using PyInstaller

echo Building Interval Training Application for Windows...

REM Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del *.spec

REM Build the executable
echo Building executable...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "IntervalTraining-windows" ^
    --add-data "src/gui/html;src/gui/html" ^
    --add-data "data;data" ^
    --add-data "src;src" ^
    --hidden-import=smartcard ^
    --hidden-import=smartcard.scard ^
    --hidden-import=smartcard.util ^
    --hidden-import=pyllrp ^
    --hidden-import=sllurp ^
    --hidden-import=reportlab ^
    --hidden-import=requests ^
    --hidden-import=webview ^
    --collect-submodules=webview ^
    --collect-submodules=smartcard ^
    --collect-submodules=pyscard ^
    --noconfirm ^
    main.py

echo Build completed successfully!
echo Executable location: dist\IntervalTraining-windows.exe

REM Test if executable exists
if exist "dist\IntervalTraining-windows.exe" (
    echo ✓ Executable created successfully
    dir dist\IntervalTraining-windows.exe
) else (
    echo ✗ Executable not found!
    exit /b 1
)

echo.
echo To test the executable:
echo   cd dist
echo   IntervalTraining-windows.exe