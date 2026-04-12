"""
Season-based athlete roster persistence.

Organizes athlete rosters by season (e.g., "Spring 2026") using JSON files,
following the same patterns as athlete_persistence.py.

File structure:
  <user_data_dir>/
  └── seasons/
      ├── index.json          (season list + active season pointer)
      ├── spring_2026.json    (roster for "Spring 2026")
      └── fall_2025.json      (roster for archived seasons)
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from persistence.user_data_dir import get_user_data_dir


def get_seasons_dir(data_dir=None) -> Path:
    """Return the seasons directory, creating it if needed."""
    if data_dir is None:
        base = get_user_data_dir()
    else:
        base = Path(data_dir)
    seasons_dir = base / "seasons"
    seasons_dir.mkdir(parents=True, exist_ok=True)
    return seasons_dir


def get_seasons_index_path(data_dir=None) -> str:
    return str(get_seasons_dir(data_dir) / "index.json")


def get_season_roster_path(season_id: str, data_dir=None) -> str:
    return str(get_seasons_dir(data_dir) / f"{season_id}.json")


def _slugify(name: str) -> str:
    """Convert a season name to a comparison/file ID by lowercasing and stripping all
    non-alphanumeric characters, so 'Spring 2026', 'spring2026', and ' SPRING  2026 '
    all produce the same ID: 'spring2026'."""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def load_seasons_index(data_dir=None) -> dict:
    """Load the seasons index file. Returns an empty index if missing or corrupt."""
    index_path = get_seasons_index_path(data_dir)
    if not os.path.exists(index_path):
        return {"active_season_id": None, "seasons": []}
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading seasons index: {e}")
        return {"active_season_id": None, "seasons": []}


def save_seasons_index(index_data: dict, data_dir=None) -> bool:
    """Atomically write the seasons index file."""
    index_path = get_seasons_index_path(data_dir)
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
        print(f"Error saving seasons index: {e}")
        return False


def get_active_season(data_dir=None) -> Optional[dict]:
    """Return the active season dict {id, name, created_at} or None."""
    index = load_seasons_index(data_dir)
    active_id = index.get("active_season_id")
    if not active_id:
        return None
    for season in index.get("seasons", []):
        if season["id"] == active_id:
            return season
    return None


def list_seasons(data_dir=None) -> list:
    """Return all seasons with an is_active flag, most recent first."""
    index = load_seasons_index(data_dir)
    active_id = index.get("active_season_id")
    result = [
        {**s, "is_active": s["id"] == active_id}
        for s in index.get("seasons", [])
    ]
    result.reverse()  # most recently created first
    return result


def set_active_season(season_id: str, data_dir=None) -> Optional[dict]:
    """Set the given season as active. Returns the season dict or None if not found."""
    index = load_seasons_index(data_dir)
    for season in index.get("seasons", []):
        if season["id"] == season_id:
            index["active_season_id"] = season_id
            save_seasons_index(index, data_dir)
            return season
    return None


def create_season(name: str, data_dir=None) -> dict:
    """
    Create a new season and set it as active. Returns the new season dict.
    If a season with the same slug ID already exists, it is set as active.
    """
    season_id = _slugify(name)
    now = datetime.now().isoformat()

    index = load_seasons_index(data_dir)

    # Reject duplicate names (compared by slug — ignores case and whitespace)
    for season in index.get("seasons", []):
        if season["id"] == season_id:
            raise ValueError(f"A season named \"{season['name']}\" already exists.")

    new_season = {"id": season_id, "name": name, "created_at": now}
    index.setdefault("seasons", []).append(new_season)
    index["active_season_id"] = season_id
    save_seasons_index(index, data_dir)

    # Create an empty roster file
    _save_raw_roster(season_id, name, [], data_dir)

    return new_season


def load_season_roster(season_id: str, data_dir=None, include_archived=False):
    """
    Load Runner objects for the given season.
    Returns a list (possibly empty) or None on error.
    By default, excludes archived athletes unless include_archived=True.
    """
    roster_path = get_season_roster_path(season_id, data_dir)
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
            # Filter out archived athletes
            return [athlete for athlete in all_athletes if not getattr(athlete, 'archived', False)]
    except Exception as e:
        print(f"Error loading season roster for {season_id}: {e}")
        return None


def save_season_roster(season_id: str, season_name: str, athletes_list: list, data_dir=None) -> bool:
    """Save a list of Runner objects to a season roster file."""
    from serializer.json_serializer import runner_to_json

    athletes_json = []
    for athlete in athletes_list:
        try:
            athletes_json.append(runner_to_json(athlete))
        except Exception as e:
            print(f"Warning: failed to serialize athlete: {e}")

    return _save_raw_roster(season_id, season_name, athletes_json, data_dir)


def _save_raw_roster(season_id: str, season_name: str, athletes_json: list, data_dir=None) -> bool:
    """Atomically write roster JSON to the season file."""
    roster_path = get_season_roster_path(season_id, data_dir)
    temp_path = roster_path + ".tmp"
    data = {
        "season_metadata": {
            "season_id": season_id,
            "season_name": season_name,
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
        print(f"Error saving season roster for {season_id}: {e}")
        return False


def merge_athletes_from_csv(season_id: str, season_name: str, new_runners: list, data_dir=None) -> dict:
    """
    Merge new_runners (list of Runner objects parsed from CSV) into the season roster.
    Matches existing athletes by lap_id (RFID tag).
    Updates name fields on match; appends as new if no match.
    Returns {"added": N, "updated": M, "total": T}.
    """
    existing = load_season_roster(season_id, data_dir, include_archived=True) or []
    by_lap_id = {r.lap_id: r for r in existing}

    added = 0
    updated = 0
    for runner in new_runners:
        if runner.lap_id in by_lap_id:
            existing_runner = by_lap_id[runner.lap_id]
            existing_runner.name = runner.name
            existing_runner.lname = runner.lname
            existing_runner.start_id = runner.start_id
            updated += 1
        else:
            existing.append(runner)
            by_lap_id[runner.lap_id] = runner
            added += 1

    save_season_roster(season_id, season_name, existing, data_dir)
    return {"added": added, "updated": updated, "total": len(existing)}


def archive_season(season_id: str, data_dir=None) -> bool:
    """
    Archive a season by setting its archived flag to True.
    If the archived season was active, clear the active season.
    Returns True on success, False on error.
    """
    index = load_seasons_index(data_dir)
    
    for season in index.get("seasons", []):
        if season["id"] == season_id:
            season["archived"] = True
            season["archived_at"] = datetime.now().isoformat()
            
            # Clear active season if archiving the active one
            if index.get("active_season_id") == season_id:
                index["active_season_id"] = None
            
            return save_seasons_index(index, data_dir)
    
    return False


def restore_season(season_id: str, data_dir=None) -> bool:
    """
    Restore an archived season by removing its archived flag.
    Returns True on success, False on error.
    """
    index = load_seasons_index(data_dir)
    
    for season in index.get("seasons", []):
        if season["id"] == season_id and season.get("archived"):
            season.pop("archived", None)
            season.pop("archived_at", None)
            return save_seasons_index(index, data_dir)
    
    return False


def list_all_seasons(data_dir=None) -> list:
    """
    Return all seasons including archived ones with status flags and athlete counts.
    Returns list with is_active, archived flags, and athlete_count.
    """
    index = load_seasons_index(data_dir)
    active_id = index.get("active_season_id")
    result = []
    
    for season in index.get("seasons", []):
        # Count active athletes in this season
        roster = load_season_roster(season["id"], data_dir, include_archived=False) or []
        athlete_count = len(roster)
        
        season_dict = {
            **season,
            "is_active": season["id"] == active_id,
            "archived": season.get("archived", False),
            "athlete_count": athlete_count
        }
        result.append(season_dict)
    
    result.reverse()  # most recently created first
    return result


def list_all_athletes(data_dir=None) -> list:
    """
    Return all athletes from all seasons with season information and archive status.
    Returns list of athlete dicts with season_id, season_name, and archived flags.
    """
    all_athletes = []
    seasons = list_all_seasons(data_dir)
    
    for season in seasons:
        roster = load_season_roster(season["id"], data_dir, include_archived=True) or []
        
        for athlete in roster:
            from serializer.json_serializer import runner_to_json
            athlete_dict = runner_to_json(athlete)
            athlete_dict.update({
                "season_id": season["id"],
                "season_name": season["name"],
                "season_archived": season.get("archived", False),
                "archived": athlete_dict.get("archived", False)
            })
            all_athletes.append(athlete_dict)
    
    return all_athletes


def archive_athlete(season_id: str, athlete_lap_id: str, data_dir=None) -> bool:
    """
    Archive an athlete within their season by setting their archived flag.
    Returns True on success, False on error.
    """
    roster = load_season_roster(season_id, data_dir, include_archived=True) or []
    season = None
    
    # Get season name for saving
    index = load_seasons_index(data_dir)
    for s in index.get("seasons", []):
        if s["id"] == season_id:
            season = s
            break
    
    if not season:
        return False
    
    # Find and archive the athlete
    found = False
    for athlete in roster:
        if athlete.lap_id == athlete_lap_id:
            athlete.archived = True
            athlete.archived_at = datetime.now().isoformat()
            found = True
            break
    
    if found:
        return save_season_roster(season_id, season["name"], roster, data_dir)
    
    return False


def restore_athlete(season_id: str, athlete_lap_id: str, data_dir=None) -> bool:
    """
    Restore an archived athlete within their season by removing their archived flag.
    Returns True on success, False on error.
    """
    roster = load_season_roster(season_id, data_dir, include_archived=True) or []
    season = None
    
    # Get season name for saving
    index = load_seasons_index(data_dir)
    for s in index.get("seasons", []):
        if s["id"] == season_id:
            season = s
            break
    
    if not season:
        return False
    
    # Find and restore the athlete
    found = False
    for athlete in roster:
        if athlete.lap_id == athlete_lap_id and getattr(athlete, 'archived', False):
            athlete.archived = False
            if hasattr(athlete, 'archived_at'):
                delattr(athlete, 'archived_at')
            found = True
            break
    
    if found:
        return save_season_roster(season_id, season["name"], roster, data_dir)
    
    return False


def find_athlete_by_id(athlete_id: str, data_dir=None) -> Optional[tuple]:
    """
    Find an athlete by their unique ID across all seasons.
    Returns (season_id, athlete) tuple if found, None otherwise.
    """
    seasons = list_all_seasons(data_dir)
    
    for season in seasons:
        roster = load_season_roster(season["id"], data_dir, include_archived=True) or []
        
        for athlete in roster:
            # Use lap_id as the unique athlete identifier
            if athlete.lap_id == athlete_id:
                return (season["id"], athlete)
    
    return None
