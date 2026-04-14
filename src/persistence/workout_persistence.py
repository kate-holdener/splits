"""
Workout configuration persistence.

Stores named workout configurations so coaches can reuse them across sessions.

File structure:
  <user_data_dir>/
  └── workouts/
      └── index.json  (list of all saved workouts)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from persistence.user_data_dir import get_user_data_dir


def get_workouts_dir(data_dir=None) -> Path:
    """Return the workouts directory, creating it if needed."""
    if data_dir is None:
        base = get_user_data_dir()
    else:
        base = Path(data_dir)
    workouts_dir = base / "workouts"
    workouts_dir.mkdir(parents=True, exist_ok=True)
    return workouts_dir


def get_workouts_index_path(data_dir=None) -> str:
    return str(get_workouts_dir(data_dir) / "index.json")


def _make_workout_id(distance: int, laps: int, rest: int) -> str:
    """Generate a stable, unique ID from workout parameters."""
    return f"{distance}m-rest{rest}s-laps{laps}"


def _make_workout_name(distance: int, laps: int, rest: int) -> str:
    """Generate a human-readable label from workout parameters."""
    return f"{distance}m \u00d7 {laps} laps, {rest}s rest"


def load_workouts_index(data_dir=None) -> dict:
    """Load the workouts index file. Returns an empty index if missing or corrupt."""
    index_path = get_workouts_index_path(data_dir)
    if not os.path.exists(index_path):
        return {"workouts": []}
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading workouts index: {e}")
        return {"workouts": []}


def save_workouts_index(index_data: dict, data_dir=None) -> bool:
    """Atomically write the workouts index file."""
    index_path = get_workouts_index_path(data_dir)
    temp_path = index_path + ".tmp"
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, index_path)
        return True
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        print(f"Error saving workouts index: {e}")
        return False


def list_workouts(data_dir=None) -> list:
    """Return all saved workouts, most recently added first."""
    index = load_workouts_index(data_dir)
    result = list(index.get("workouts", []))
    result.reverse()
    return result


def save_workout(distance: int, laps: int, rest: int, data_dir=None) -> dict:
    """
    Save a workout configuration.

    If a workout with the same distance, laps, and rest already exists, return it
    without creating a duplicate. Otherwise create and persist a new entry.

    Args:
        distance: Interval distance in metres.
        laps: Number of lap-sensor crossings per interval.
        rest: Rest time between intervals in seconds.
        data_dir: Optional base data directory (``None`` uses user data dir).

    Returns:
        The workout dict (new or existing).
    """
    workout_id = _make_workout_id(distance, laps, rest)
    index = load_workouts_index(data_dir)

    for w in index.get("workouts", []):
        if w["id"] == workout_id:
            return w  # already exists — no duplicate

    new_workout = {
        "id": workout_id,
        "name": _make_workout_name(distance, laps, rest),
        "distance": distance,
        "laps": laps,
        "rest": rest,
        "created_at": datetime.now().isoformat(),
    }
    index.setdefault("workouts", []).append(new_workout)
    save_workouts_index(index, data_dir)
    return new_workout


def get_workout_by_id(workout_id: str, data_dir=None) -> Optional[dict]:
    """Return the workout dict for the given ID, or None if not found."""
    index = load_workouts_index(data_dir)
    for w in index.get("workouts", []):
        if w["id"] == workout_id:
            return w
    return None
