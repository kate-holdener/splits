# Build Documentation - Interval Training Executables

## Overview

This document describes how to build cross-platform executables for the Interval Training application using PyInstaller. The application uses a pywebview-based GUI and bundles all Python dependencies for distribution.

## Prerequisites

### Development Environment
- Python 3.11+ (tested with 3.11)
- Git
- Platform-specific requirements (see below)

### Platform-Specific Requirements

#### macOS
- Xcode Command Line Tools (`xcode-select --install`)
- Homebrew (recommended): `brew install pcsc-lite`
- Note: pcsc-lite is optional for development but recommended for NFC functionality

#### Windows
- Windows 10+ (WinSCard API is built-in)
- Visual Studio Build Tools (installed automatically with Python)

## Building Executables

### Quick Start

#### macOS
```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build executable
./scripts/build-macos.sh

# Test executable
cd dist
./IntervalTraining-macos
```

#### Windows
```cmd
REM Install dependencies
pip install -r requirements.txt
pip install pyinstaller

REM Build executable
scripts\build-windows.bat

REM Test executable
cd dist
IntervalTraining-windows.exe
```

### Build Scripts

The build scripts are located in the `scripts/` directory:

- `scripts/build-macos.sh` - macOS build script
- `scripts/build-windows.bat` - Windows build script
- `scripts/IntervalTraining-macos.spec` - PyInstaller spec file for macOS
- `scripts/IntervalTraining-windows.spec` - PyInstaller spec file for Windows

### Build Output

Executables are created in the `dist/` directory:
- macOS: `dist/IntervalTraining-macos` (single file, ~400MB)
- Windows: `dist/IntervalTraining-windows.exe` (single file, ~350MB)

## Automated Releases (GitHub Actions)

### Workflow Triggers

The workflow (`.github/workflows/build-release.yml`) can be triggered in two ways:

1. **Automatic (Tag-based)**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Manual (Workflow Dispatch)**:
   - Go to GitHub Actions tab
   - Select "Build and Release Executables"
   - Click "Run workflow"
   - Enter version number (e.g., v1.0.0)

### Release Process

1. Creates executables for both macOS and Windows
2. Uploads artifacts for download
3. Creates a GitHub release with both executables attached
4. Generates release notes with installation instructions

## Testing Executables

### Validation Checklist

Before releasing, test the executables on clean systems:

#### Basic Functionality
- [ ] Application starts without errors
- [ ] GUI loads and displays correctly
- [ ] All HTML/CSS assets load properly
- [ ] Data files are accessible

#### Core Features
- [ ] Can load runner/athlete data from CSV
- [ ] Timer functionality works
- [ ] RFID/NFC simulation works (if hardware not available)
- [ ] Session persistence works
- [ ] PDF report generation works

#### System Integration
- [ ] No dependency errors
- [ ] Application doesn't require Python installation
- [ ] Proper handling of file paths
- [ ] Clean shutdown and cleanup

### Test Environment Setup

#### macOS
- Use a macOS system without Python development tools
- Test both Intel and Apple Silicon if possible
- Verify Gatekeeper behavior (may need "right-click + Open")

#### Windows
- Use a Windows system without Python installed
- Test with Windows Defender SmartScreen
- Verify all features work on Windows 10 and 11

## Troubleshooting

### Common Build Issues

#### macOS
```bash
# Issue: pcsc-lite not found
brew install pcsc-lite

# Issue: Permission denied
chmod +x scripts/build-macos.sh

# Issue: PyInstaller not found
pip install pyinstaller
```

#### Windows
```cmd
REM Issue: PyInstaller not found
pip install pyinstaller

REM Issue: Missing Visual C++ tools
REM Install Visual Studio Build Tools or Visual Studio Community
```

### Runtime Issues

#### Application Won't Start
- Check that all assets are bundled correctly
- Verify environment variables are set properly
- Check PyInstaller warnings during build

#### Missing Dependencies
- Add missing modules to hidden imports in .spec files
- Use `--collect-submodules` for complex packages
- Check import paths in the application code

#### Large Executable Size
- Use `--exclude-module` to remove unused packages
- Consider `--onedir` instead of `--onefile` for development
- Review collected submodules and data files

### Asset Path Issues
- Verify HTML/CSS files are in correct bundled paths
- Check `sys._MEIPASS` path handling in main.py
- Ensure data files are accessible via environment variables

## Development Workflow

### Adding New Dependencies
1. Add to `requirements.txt`
2. Update `hiddenimports` in .spec files if needed
3. Test build on both platforms
4. Update documentation

### Modifying GUI Assets
1. Update HTML/CSS files in `src/gui/html/`
2. Verify build scripts include new assets
3. Test bundled paths work correctly
4. Rebuild and test executables

### Version Management
- Use semantic versioning (v1.0.0, v1.1.0, etc.)
- Update version in appropriate files before tagging
- Test release process in a fork first

## Architecture Notes

### Entry Point
- `main.py` - Primary entry point that handles PyInstaller bundling
- Sets up Python paths and environment variables
- Launches `src/gui/interval_training_gui.py`

### Resource Bundling
- HTML/CSS assets: `src/gui/html/` → bundled as `src/gui/html/`
- Data files: `data/` → bundled as `data/`
- Source code: `src/` → bundled as `src/`

### Key Dependencies
- `pywebview` - Cross-platform GUI framework
- `pyscard` - NFC/smart card support (platform-specific)
- `pyllrp` - RFID protocol library
- `reportlab` - PDF generation
- `requests` - HTTP client for RFID readers

## Support

For build issues:
1. Check this documentation
2. Review GitHub Actions logs for automated builds
3. Test on a clean environment
4. Check PyInstaller documentation for advanced troubleshooting