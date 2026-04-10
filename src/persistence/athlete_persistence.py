"""
Athlete persistence module for saving and loading athlete sessions.

This module provides functionality to persist athlete rosters between GUI sessions
using JSON format storage in a platform-appropriate user data directory.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from utils.normalized_timestamp import get_timestamp_now
from persistence.user_data_dir import get_user_data_dir


class SessionPersistenceError(Exception):
    """Raised when session persistence operations fail."""
    pass


def save_athletes_to_session(athletes_list: List, file_path: str) -> bool:
    """
    Save a list of athlete objects to a JSON session file.
    
    Args:
        athletes_list: List of Runner objects to save
        file_path: Path where to save the session file
        
    Returns:
        bool: True if save successful, False otherwise
        
    Raises:
        SessionPersistenceError: If save operation fails critically
    """
    try:
        # Import here to avoid circular imports
        from serializer.json_serializer import runner_to_json
        
        # Create session data structure
        session_data = {
            "session_metadata": {
                "saved_at": datetime.now().isoformat(),
                "saved_timestamp": get_timestamp_now(),
                "athlete_count": len(athletes_list)
            },
            "athletes": []
        }
        
        # Convert each athlete to JSON format
        for athlete in athletes_list:
            try:
                athlete_json = runner_to_json(athlete)
                # Ensure we have the required fields for reconstruction
                required_fields = ["name", "start_id", "lap_id"]
                if all(field in athlete_json for field in required_fields):
                    # Add last name if available (check both 'lname' attribute and JSON structure)
                    if hasattr(athlete, 'lname'):
                        athlete_json["lname"] = athlete.lname
                    session_data["athletes"].append(athlete_json)
                else:
                    print(f"Warning: Skipping athlete {getattr(athlete, 'name', 'Unknown')} due to missing required fields")
            except Exception as e:
                print(f"Warning: Failed to serialize athlete {getattr(athlete, 'name', 'Unknown')}: {e}")
                continue
        
        # Ensure the parent directory exists
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Write to file with atomic operation (write to temp file first)
        temp_path = f"{file_path}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # Atomic move
        os.replace(temp_path, file_path)
        
        print(f"Session saved: {len(session_data['athletes'])} athletes to {file_path}")
        return True
        
    except Exception as e:
        # Clean up temp file if it exists
        temp_path = f"{file_path}.tmp"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        
        print(f"Error saving session to {file_path}: {e}")
        return False


def load_athletes_from_session(file_path: str) -> Optional[List]:
    """
    Load athlete objects from a JSON session file.
    
    Args:
        file_path: Path to the session file to load
        
    Returns:
        List of Runner objects if successful, None if file doesn't exist or is invalid
        
    Raises:
        SessionPersistenceError: If load operation fails critically
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"No session file found at {file_path}")
            return None
        
        # Read and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Validate session data structure
        if not isinstance(session_data, dict) or "athletes" not in session_data:
            print(f"Invalid session file format: {file_path}")
            return None
        
        athletes_data = session_data["athletes"]
        if not isinstance(athletes_data, list):
            print(f"Invalid athletes data in session file: {file_path}")
            return None
        
        # Load metadata if available
        metadata = session_data.get("session_metadata", {})
        saved_at = metadata.get("saved_at", "unknown")
        athlete_count = metadata.get("athlete_count", len(athletes_data))
        
        print(f"Loading session from {saved_at}: {athlete_count} athletes")
        
        # Convert JSON data back to Runner objects
        from serializer.json_serializer import runners_from_json
        athletes = runners_from_json(athletes_data)
        
        if athletes:
            print(f"Successfully loaded {len(athletes)} athletes from session")
            return athletes
        else:
            print("No valid athletes found in session file")
            return None
            
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in session file {file_path}: {e}")
        # Backup corrupt file
        try:
            backup_path = f"{file_path}.corrupt.{get_timestamp_now()}"
            os.rename(file_path, backup_path)
            print(f"Corrupt session file backed up to: {backup_path}")
        except:
            pass
        return None
        
    except Exception as e:
        print(f"Error loading session from {file_path}: {e}")
        return None


def get_session_file_path(data_dir: Optional[str] = None) -> str:
    """
    Get the standard session file path.

    When *data_dir* is ``None`` (default) the path is resolved inside the
    platform-appropriate user data directory returned by
    :func:`get_user_data_dir`.  Pass an explicit *data_dir* string to
    override (useful for tests and legacy callers).

    Args:
        data_dir: Optional base data directory.  Pass ``None`` to use the
                  user data directory, or a string path to override.

    Returns:
        Full path to the session file as a string.
    """
    if data_dir is None:
        return str(get_user_data_dir() / "athletes_session.json")
    return os.path.join(data_dir, "athletes_session.json")


def session_exists(data_dir: Optional[str] = None) -> bool:
    """
    Check if a session file exists.

    Args:
        data_dir: Optional base data directory (``None`` uses user data dir).

    Returns:
        True if session file exists and is readable.
    """
    session_path = get_session_file_path(data_dir)
    return os.path.exists(session_path) and os.access(session_path, os.R_OK)


def clear_session(data_dir: Optional[str] = None) -> bool:
    """
    Clear the current session file.

    Args:
        data_dir: Optional base data directory (``None`` uses user data dir).

    Returns:
        True if session cleared successfully.
    """
    try:
        session_path = get_session_file_path(data_dir)
        if os.path.exists(session_path):
            os.remove(session_path)
            print(f"Session file cleared: {session_path}")
        return True
    except Exception as e:
        print(f"Error clearing session: {e}")
        return False