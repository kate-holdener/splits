#!/usr/bin/env python3
"""
Main entry point for Interval Training Application
Handles PyInstaller bundled resources and launches the pywebview GUI.
"""

import os
import sys
from pathlib import Path

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Development mode - use current script directory
        base_path = Path(__file__).parent
    
    return os.path.join(base_path, relative_path)

def setup_python_path():
    """Setup Python path to include src directory"""
    # Get the src directory path
    src_path = get_resource_path('src')
    
    # Add src to Python path if not already there
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

def main():
    """Main entry point for the application"""
    # Setup Python path for imports
    setup_python_path()
    
    # Set environment variables for resource paths
    os.environ['GUI_HTML_PATH'] = get_resource_path('src/gui/html')
    os.environ['DATA_PATH'] = get_resource_path('data')
    
    # Import and run the GUI
    try:
        from gui.interval_training_gui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"Failed to import GUI module: {e}")
        print("Make sure all dependencies are installed and src/ is in Python path")
        sys.exit(1)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()