"""
Athlete roster persistence.

Organizes athlete rosters by name (e.g., "Spring 2026") using JSON files.

File structure:
  <user_data_dir>/
  └── rosters/
      ├── index.json          (roster list + active roster pointer)
      ├── spring_2026.json    (roster for "Spring 2026")
      └── fall_2025.json      (archived roster)
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from persistence.user_data_dir import get_user_data_dir


def get_rosters_dir(data_dir=None) -> Path:
    """Return the rosters directory, creating it if needed."""
    if data_dir is None:
        base = get_user_data_dir()
    else:
        base = Path(data_dir)
    rosters_dir = base / "rosters"
    rosters_dir.mkdir(parents=True, exist_ok=True)
    return rosters_dir


def get_rosters_index_path(data_dir=None) -> str:
    return str(get_rosters_dir(data_dir) / "index.json")


def get_roster_path(roster_id: str, data_dir=None) -> str:
    return str(get_rosters_dir(data_dir) / f"{roster_id}.json")


def _slugify(name: str) -> str:
    """Convert a roster name to a comparison/file ID by lowercasing and stripping all
    non-alphanumeric characters, so 'Spring 2026', 'spring2026', and ' SPRING  2026 '
    all produce the same ID: 'spring2026'."""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def load_rosters_index(data_dir=None) -> dict:
    """Load the rosters index file. Returns an empty index if missing or corrupt."""
    index_path = get_rosters_index_path(data_dir)
    if not os.path.exists(index_path):
        return {"active_roster_id": None, "rosters": []}
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading rosters index: {e}")
        return {"active_roster_id": None, "rosters": []}


def save_rosters_index(index_data: dict, data_dir=None) -> bool:
    """Atomically write the rosters index file."""
    index_path = get_rosters_index_path(data_dir)
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
        print(f"Error saving rosters index: {e}")
        return False


def get_active_roster(data_dir=None) -> Optional[dict]:
    """Return the active roster dict {id, name, created_at} or None."""
    index = load_rosters_index(data_dir)
    active_id = index.get("active_roster_id")
    if not active_id:
        return None
    for roster in index.get("rosters", []):
        if roster["id"] == active_id:
            return roster
    return None


def list_rosters(data_dir=None) -> list:
    """Return all rosters with an is_active flag, most recent first."""
    index = load_rosters_index(data_dir)
    active_id = index.get("active_roster_id")
    result = [
        {**s, "is_active": s["id"] == active_id}
        for s in index.get("rosters", [])
    ]
    result.reverse()  # most recently created first
    return result


def set_active_roster(roster_id: str, data_dir=None) -> Optional[dict]:
    """Set the given roster as active. Returns the roster dict or None if not found."""
    index = load_rosters_index(data_dir)
    for roster in index.get("rosters", []):
        if roster["id"] == roster_id:
            index["active_roster_id"] = roster_id
            save_rosters_index(index, data_dir)
            return roster
    return None


def create_roster(name: str, data_dir=None) -> dict:
    """
    Create a new roster and set it as active. Returns the new roster dict.
    If a roster with the same slug ID already exists, raises ValueError.
    """
    roster_id = _slugify(name)
    now = datetime.now().isoformat()

    index = load_rosters_index(data_dir)

    # Reject duplicate names (compared by slug — ignores case and whitespace)
    for roster in index.get("rosters", []):
        if roster["id"] == roster_id:
            raise ValueError(f"A roster named \"{roster['name']}\" already exists.")

    new_roster = {"id": roster_id, "name": name, "created_at": now}
    index.setdefault("rosters", []).append(new_roster)
    index["active_roster_id"] = roster_id
    save_rosters_index(index, data_dir)

    # Create an empty roster file
    _save_raw_roster(roster_id, name, [], data_dir)

    return new_roster


def load_roster(roster_id: str, data_dir=None, include_archived=False):
    """
    Load Runner objects for the given roster.
    Returns a list (possibly empty) or None on error.
    By default, excludes archived athletes unless include_archived=True.
    """
    roster_path = get_roster_path(roster_id, data_dir)
    if not os.path.exists(roster_path):
        return []
    try:
        with open(roster_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        athletes_data = data.get("athletes", [])
        from serializer.json_serializer import runners_from_json
        all_athletes = runners_from_json(athletes_data)

        if include_archived:
            return all_athletes
        else:
            return [athlete for athlete in all_athletes if not getattr(athlete, 'archived', False)]
    except Exception as e:
        print(f"Error loading roster for {roster_id}: {e}")
        return None


def save_roster(roster_id: str, roster_name: str, athletes_list: list, data_dir=None) -> bool:
    """Save a list of Runner objects to a roster file."""
    from serializer.json_serializer import runner_to_json

    athletes_json = []
    for athlete in athletes_list:
        try:
            athletes_json.append(runner_to_json(athlete))
        except Exception as e:
            print(f"Warning: failed to serialize athlete: {e}")

    return _save_raw_roster(roster_id, roster_name, athletes_json, data_dir)


def _save_raw_roster(roster_id: str, roster_name: str, athletes_json: list, data_dir=None) -> bool:
    """Atomically write roster JSON to the roster file."""
    roster_path = get_roster_path(roster_id, data_dir)
    temp_path = roster_path + ".tmp"
    data = {
        "roster_metadata": {
            "roster_id": roster_id,
            "roster_name": roster_name,
            "saved_at": datetime.now().isoformat(),
            "athlete_count": len(athletes_json)
        },
        "athletes": athletes_json
    }
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, roster_path)
        return True
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        print(f"Error saving roster for {roster_id}: {e}")
        return False


def merge_athletes_from_csv(roster_id: str, roster_name: str, new_runners: list, data_dir=None) -> dict:
    """
    Merge new_runners (list of Runner objects parsed from CSV) into the roster.
    Matches existing athletes by lap_id (RFID tag).
    Updates name fields on match; appends as new if no match.
    Returns {"added": N, "updated": M, "total": T}.
    """
    existing = load_roster(roster_id, data_dir, include_archived=True) or []
    by_lap_id = {r.lap_id: r for r in existing}

    added = 0
    updated = 0
    for runner in new_runners:
        if runner.lap_id in by_lap_id:
            existing_runner = by_lap_id[runner.lap_id]
            existing_runner.name = runner.name
            existing_runner.lname = runner.lname
            existing_runner.start_id = runner.start_id
            if runner.email is not None:
                existing_runner.email = runner.email
            updated += 1
        else:
            existing.append(runner)
            by_lap_id[runner.lap_id] = runner
            added += 1

    save_roster(roster_id, roster_name, existing, data_dir)
    return {"added": added, "updated": updated, "total": len(existing)}


def archive_roster(roster_id: str, data_dir=None) -> bool:
    """
    Archive a roster by setting its archived flag to True.
    If the archived roster was active, clear the active roster.
    Returns True on success, False on error.
    """
    index = load_rosters_index(data_dir)

    for roster in index.get("rosters", []):
        if roster["id"] == roster_id:
            roster["archived"] = True
            roster["archived_at"] = datetime.now().isoformat()

            # Clear active roster if archiving the active one
            if index.get("active_roster_id") == roster_id:
                index["active_roster_id"] = None

            return save_rosters_index(index, data_dir)

    return False


def restore_roster(roster_id: str, data_dir=None) -> bool:
    """
    Restore an archived roster by removing its archived flag.
    Returns True on success, False on error.
    """
    index = load_rosters_index(data_dir)

    for roster in index.get("rosters", []):
        if roster["id"] == roster_id and roster.get("archived"):
            roster.pop("archived", None)
            roster.pop("archived_at", None)
            return save_rosters_index(index, data_dir)

    return False


def list_all_rosters(data_dir=None) -> list:
    """
    Return all rosters including archived ones with status flags and athlete counts.
    Returns list with is_active, archived flags, and athlete_count.
    """
    index = load_rosters_index(data_dir)
    active_id = index.get("active_roster_id")
    result = []

    for roster in index.get("rosters", []):
        athletes = load_roster(roster["id"], data_dir, include_archived=False) or []
        roster_dict = {
            **roster,
            "is_active": roster["id"] == active_id,
            "archived": roster.get("archived", False),
            "athlete_count": len(athletes)
        }
        result.append(roster_dict)

    result.reverse()  # most recently created first
    return result


def list_all_athletes(data_dir=None) -> list:
    """
    Return all athletes from all rosters with roster information and archive status.
    Returns list of athlete dicts with roster_id, roster_name, and archived flags.
    """
    all_athletes = []
    rosters = list_all_rosters(data_dir)

    for roster in rosters:
        athletes = load_roster(roster["id"], data_dir, include_archived=True) or []

        for athlete in athletes:
            from serializer.json_serializer import runner_to_json
            athlete_dict = runner_to_json(athlete)
            athlete_dict.update({
                "roster_id": roster["id"],
                "roster_name": roster["name"],
                "roster_archived": roster.get("archived", False),
                "archived": athlete_dict.get("archived", False)
            })
            all_athletes.append(athlete_dict)

    return all_athletes


def archive_athlete(roster_id: str, athlete_lap_id: str, data_dir=None) -> bool:
    """
    Archive an athlete within their roster by setting their archived flag.
    Returns True on success, False on error.
    """
    athletes = load_roster(roster_id, data_dir, include_archived=True) or []
    roster = None

    # Get roster name for saving
    index = load_rosters_index(data_dir)
    for r in index.get("rosters", []):
        if r["id"] == roster_id:
            roster = r
            break

    if not roster:
        return False

    found = False
    for athlete in athletes:
        if athlete.lap_id == athlete_lap_id:
            athlete.archived = True
            athlete.archived_at = datetime.now().isoformat()
            found = True
            break

    if found:
        return save_roster(roster_id, roster["name"], athletes, data_dir)

    return False


def restore_athlete(roster_id: str, athlete_lap_id: str, data_dir=None) -> bool:
    """
    Restore an archived athlete within their roster by removing their archived flag.
    Returns True on success, False on error.
    """
    athletes = load_roster(roster_id, data_dir, include_archived=True) or []
    roster = None

    # Get roster name for saving
    index = load_rosters_index(data_dir)
    for r in index.get("rosters", []):
        if r["id"] == roster_id:
            roster = r
            break

    if not roster:
        return False

    found = False
    for athlete in athletes:
        if athlete.lap_id == athlete_lap_id and getattr(athlete, 'archived', False):
            athlete.archived = False
            if hasattr(athlete, 'archived_at'):
                delattr(athlete, 'archived_at')
            found = True
            break

    if found:
        return save_roster(roster_id, roster["name"], athletes, data_dir)

    return False


def find_athlete_by_id(athlete_id: str, data_dir=None) -> Optional[tuple]:
    """
    Find an athlete by their unique ID across all rosters.
    Returns (roster_id, athlete) tuple if found, None otherwise.
    """
    rosters = list_all_rosters(data_dir)

    for roster in rosters:
        athletes = load_roster(roster["id"], data_dir, include_archived=True) or []

        for athlete in athletes:
            if athlete.lap_id == athlete_id:
                return (roster["id"], athlete)

    return None
