"""
Platform-appropriate user data directory resolution.

This module provides a single function for resolving the OS user data directory
for the application. It is shared across all persistence modules.
"""

import os
import sys
from pathlib import Path


def get_user_data_dir() -> Path:
    """
    Get the platform-appropriate user data directory for the application.

    | Platform | Location |
    |----------|----------|
    | Windows  | %APPDATA%\\IntervalTimer\\ |
    | macOS    | ~/Library/Application Support/IntervalTimer/ |
    | Linux    | $XDG_DATA_HOME/IntervalTimer/ or ~/.local/share/IntervalTimer/ |

    Returns:
        Path: User data directory, created automatically if it does not exist.
    """
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif sys.platform == 'darwin':  # macOS
        base = Path.home() / 'Library' / 'Application Support'
    else:  # Linux / other Unix
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

    data_dir = base / 'IntervalTimer'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
