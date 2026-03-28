@echo off
REM Test script for Windows executable
REM This script validates that the executable works correctly

echo Testing IntervalTraining-windows.exe executable...

REM Check if executable exists
if not exist "dist\IntervalTraining-windows.exe" (
    echo ❌ Executable not found at dist\IntervalTraining-windows.exe
    echo Run scripts\build-windows.bat first
    exit /b 1
)

REM Check file size (should be substantial)
for %%A in ("dist\IntervalTraining-windows.exe") do set SIZE=%%~zA
if %SIZE% LSS 100000000 (
    echo ⚠️  Warning: Executable size is only %SIZE% bytes - may be incomplete
) else (
    echo ✅ Executable found and properly sized (%SIZE% bytes)
)

REM Test basic execution (launch and quickly close)
echo Testing executable launch...
start /B dist\IntervalTraining-windows.exe
timeout /t 3 /nobreak >nul

REM Check if process is running
tasklist /FI "IMAGENAME eq IntervalTraining-windows.exe" 2>NUL | find /I /N "IntervalTraining-windows.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo ✅ Application started successfully
    REM Kill the process
    taskkill /IM "IntervalTraining-windows.exe" /F >nul 2>&1
) else (
    echo ❌ Application failed to start or closed immediately
    exit /b 1
)

echo.
echo ✅ Basic executable test passed!
echo To manually test the application:
echo   cd dist
echo   IntervalTraining-windows.exe