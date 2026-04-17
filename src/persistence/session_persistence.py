"""
Real-time workout session persistence.

Writes a full snapshot of all runners to disk on every runner state change so
that a crashed session can be detected on the next startup and resumed.

File structure:
  <user_data_dir>/
  └── sessions/
      ├── active_session.json      # present only while a workout is in progress
      └── <session_id>.json        # archived on finish_workout()
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from persistence.user_data_dir import get_user_data_dir
from serializer.json_serializer import runner_to_session_json


def get_sessions_dir(data_dir=None) -> Path:
    """Return the sessions directory, creating it if needed."""
    base = Path(data_dir) if data_dir is not None else get_user_data_dir()
    sessions_dir = base / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def get_active_session_path(data_dir=None) -> str:
    return str(get_sessions_dir(data_dir) / "active_session.json")


def has_active_session(data_dir=None) -> bool:
    return os.path.exists(get_active_session_path(data_dir))


def load_active_session(data_dir=None) -> Optional[dict]:
    """Return the active session dict, or None if absent or corrupt."""
    path = get_active_session_path(data_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[session_persistence] Corrupt active session, ignoring: {e}")
        return None


def restore_session_from_dict(session_dict: dict) -> list:
    """
    Deserialize a session snapshot back into a list of Runner objects.

    Each Runner has its intervals, current_status, lap_count, and current_workout
    fully restored from the session data.

    Returns:
        list[Runner]
    """
    from entity.runner import Runner
    from entity.interval import Interval
    from entity.workout import Workout
    from entity.RunnerState import RunnerState

    runners = []
    for r_dict in session_dict.get("runners", []):
        runner = Runner()
        runner.name = r_dict.get("name", "")
        runner.lname = r_dict.get("lname", "")
        runner.start_id = r_dict.get("start_id", "")
        runner.lap_id = r_dict.get("lap_id", "")
        runner.archived = r_dict.get("archived", False)
        runner.archived_at = r_dict.get("archived_at", None)

        # Restore workout
        w_data = r_dict.get("workout")
        if w_data:
            workout = Workout(datetime.fromisoformat(w_data["date_and_time"]))
            workout.configure(
                w_data["interval_distance"],
                w_data["laps_per_interval"],
                w_data["rest_time"],
            )
            runner.add_workout(workout)

        # Restore interval history
        for iv_dict in r_dict.get("session_intervals", []):
            iv = Interval()
            iv.distance = iv_dict.get("distance", 0)
            iv.start_time = iv_dict.get("start_time", 0)
            iv.end_time = iv_dict.get("end_time", 0)
            iv.incomplete = iv_dict.get("incomplete", True)
            runner.intervals.append(iv)

        # Restore runtime state
        runner.current_status = RunnerState(r_dict.get("current_status", 0))
        runner.lap_count = r_dict.get("lap_count", 0)

        runners.append(runner)

    return runners


def discard_active_session(data_dir=None) -> None:
    """Delete active_session.json without archiving (user declined recovery)."""
    path = get_active_session_path(data_dir)
    try:
        Path(path).unlink(missing_ok=True)
    except Exception as e:
        print(f"[session_persistence] Failed to discard session: {e}")


class WorkoutSessionPersistence:
    """
    Observer that persists runner performance data to disk in real time.

    Registers as an observer of each Runner. On every state change notification
    it serializes the changed runner, updates the in-memory snapshot, and
    atomically writes the full session to active_session.json.
    """

    def __init__(self, session_id: str, roster_id: str, athletes: list,
                 data_dir=None):
        self._session_id = session_id
        self._roster_id = roster_id
        self._started_at = datetime.now().isoformat()
        self._data_dir = data_dir

        # In-memory snapshots keyed by lap_id
        self._runner_snapshots: dict = {
            r.lap_id: runner_to_session_json(r) for r in athletes
        }
        self._persist()  # write initial file before any events fire

    # ------------------------------------------------------------------
    # Observer protocol
    # ------------------------------------------------------------------
    def update(self, runner) -> None:
        """Called by Runner.notify_observers() on every state change.

        Serializes the specific runner whose state just changed, updates its
        entry in the snapshot dict, then writes the full session to disk.
        """
        try:
            self._runner_snapshots[runner.lap_id] = runner_to_session_json(runner)
            self._persist()
        except Exception as e:
            print(f"[session_persistence] Warning: failed to persist: {e}")

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    def finish_session(self) -> None:
        """Write a final snapshot and archive the session file."""
        self._persist()
        src = get_active_session_path(self._data_dir)
        dst = str(get_sessions_dir(self._data_dir) / f"{self._session_id}.json")
        if os.path.exists(src):
            os.replace(src, dst)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _persist(self) -> None:
        """Atomically write current session state to active_session.json."""
        path = get_active_session_path(self._data_dir)
        tmp = path + ".tmp"
        data = {
            "session_id": self._session_id,
            "roster_id":  self._roster_id,
            "started_at": self._started_at,
            "saved_at":   datetime.now().isoformat(),
            "runners":    list(self._runner_snapshots.values()),
        }
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
