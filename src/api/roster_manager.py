from typing import Optional

from entity.runner import Runner
from persistence.roster_persistence import (
    get_active_roster,
    create_roster as _create_roster,
    load_roster,
    list_rosters as _list_rosters,
    list_all_rosters as _list_all_rosters,
)


class RosterManager:
    """Owns the athlete list and roster metadata. No timer or scanner knowledge."""

    def __init__(self):
        self.athletes: list[Runner] = []
        self.current_roster: Optional[dict] = None
        self.athletes_loaded = False
        self.session_loaded = False

    # ------------------------------------------------------------------
    # Roster queries
    # ------------------------------------------------------------------
    def get_current_roster(self):
        return {"ok": True, "roster": self.current_roster}

    def list_rosters(self):
        try:
            return {"ok": True, "rosters": _list_rosters()}
        except Exception as e:
            return {"ok": False, "msg": str(e), "rosters": []}

    def list_all_rosters_with_archived(self):
        try:
            return {"ok": True, "rosters": _list_all_rosters()}
        except Exception as e:
            return {"ok": False, "msg": str(e), "rosters": []}

    def list_all_athletes(self):
        try:
            from persistence.roster_persistence import list_all_athletes as _list_all_athletes
            athletes = _list_all_athletes()
            return {"ok": True, "athletes": athletes}
        except Exception as e:
            return {"ok": False, "msg": str(e), "athletes": []}

    def list_athletes_for_roster_including_archived(self, roster_id: str):
        try:
            from serializer.json_serializer import runner_to_json
            athletes = load_roster(roster_id, include_archived=True)
            athletes_data = [runner_to_json(a) for a in (athletes or [])]
            return {"ok": True, "athletes": athletes_data}
        except Exception as e:
            return {"ok": False, "msg": str(e), "athletes": []}

    def list_athletes(self):
        return {"ok": True, "athletes": [a.to_dict() for a in self.athletes]}

    def get_session_info(self):
        return {
            "ok": True,
            "sessionLoaded":  self.session_loaded,
            "athleteCount":   len(self.athletes),
            "athletesLoaded": self.athletes_loaded,
            "currentRoster":  self.current_roster,
        }

    # ------------------------------------------------------------------
    # Roster mutations (pure DB, no timer side-effects)
    # ------------------------------------------------------------------
    def archive_roster(self, roster_id: str):
        try:
            from persistence.roster_persistence import archive_roster as _archive_roster
            success = _archive_roster(roster_id)
            if not success:
                return {"ok": False, "msg": "Failed to archive roster."}
            rosters = _list_rosters()
            cleared_current = False
            if self.current_roster and self.current_roster["id"] == roster_id:
                self.current_roster = None
                self.athletes = []
                self.athletes_loaded = False
                self.session_loaded = False
                cleared_current = True
            return {"ok": True, "msg": "Roster archived successfully.", "rosters": rosters,
                    "_cleared_current": cleared_current}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def restore_roster(self, roster_id: str):
        try:
            from persistence.roster_persistence import restore_roster as _restore_roster
            success = _restore_roster(roster_id)
            if success:
                rosters = _list_rosters()
                return {"ok": True, "msg": "Roster restored successfully.", "rosters": rosters}
            return {"ok": False, "msg": "Failed to restore roster."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def archive_athlete(self, athlete_id: str):
        try:
            from persistence.roster_persistence import find_athlete_by_id, archive_athlete as _archive_athlete
            result = find_athlete_by_id(athlete_id)
            if not result:
                return {"ok": False, "msg": "Athlete not found."}
            roster_id, _ = result
            success = _archive_athlete(roster_id, athlete_id)
            if success:
                if self.current_roster and self.current_roster["id"] == roster_id:
                    self.athletes[:] = [a for a in self.athletes if a.lap_id != athlete_id]
                return {"ok": True, "msg": "Athlete deactivated."}
            return {"ok": False, "msg": "Failed to deactivate athlete."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def add_athlete_to_roster(self, roster_id: str, data: dict):
        from persistence.roster_persistence import load_roster, save_roster, load_rosters_index
        index = load_rosters_index()
        roster_meta = next((r for r in index.get("rosters", []) if r["id"] == roster_id), None)
        if not roster_meta:
            return {"ok": False, "msg": "Roster not found."}
        rfid_tag = data.get("rfid_tag", "").strip()
        if not rfid_tag:
            return {"ok": False, "msg": "RFID tag is required."}
        athletes = load_roster(roster_id, include_archived=True) or []
        if any(a.lap_id == rfid_tag for a in athletes):
            return {"ok": False, "msg": f"An athlete with RFID tag '{rfid_tag}' already exists in this roster."}
        runner = Runner()
        runner.name     = data.get("first_name", "").strip()
        runner.lname    = data.get("last_name",  "").strip()
        runner.lap_id   = rfid_tag
        runner.start_id = data.get("nfc_tag", "").strip()
        runner.email    = data.get("email", "").strip() or None
        athletes.append(runner)
        save_roster(roster_id, roster_meta["name"], athletes)
        return {"ok": True, "msg": f"{runner.name} added to roster."}

    def update_athlete(self, athlete_id: str, data: dict):
        from persistence.roster_persistence import find_athlete_by_id, load_roster, save_roster, load_rosters_index
        result = find_athlete_by_id(athlete_id)
        if not result:
            return {"ok": False, "msg": "Athlete not found."}
        roster_id, _ = result
        index = load_rosters_index()
        roster_meta = next((r for r in index.get("rosters", []) if r["id"] == roster_id), None)
        if not roster_meta:
            return {"ok": False, "msg": "Roster not found."}
        athletes = load_roster(roster_id, include_archived=True) or []
        for a in athletes:
            if a.lap_id == athlete_id:
                a.name     = data.get("first_name", "").strip()
                a.lname    = data.get("last_name",  "").strip()
                a.start_id = data.get("nfc_tag", "").strip()
                a.email    = data.get("email", "").strip() or None
                break
        save_roster(roster_id, roster_meta["name"], athletes)
        return {"ok": True, "msg": "Athlete updated."}

    def update_athlete_email(self, lap_id: str, email: str):
        from persistence.roster_persistence import find_athlete_by_id, load_roster, save_roster, load_rosters_index
        result = find_athlete_by_id(lap_id)
        if not result:
            return {"ok": False, "msg": "Athlete not found."}
        roster_id, _ = result
        index = load_rosters_index()
        roster_meta = next((r for r in index.get("rosters", []) if r["id"] == roster_id), None)
        if not roster_meta:
            return {"ok": False, "msg": "Roster not found."}
        athletes = load_roster(roster_id, include_archived=True) or []
        for a in athletes:
            if a.lap_id == lap_id:
                a.email = email.strip() if email else ""
                break
        save_roster(roster_id, roster_meta["name"], athletes)
        return {"ok": True}
