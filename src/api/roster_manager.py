import threading
from queue import Queue, Empty
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
    """Owns the athlete list, roster metadata, and NFC tag capture for roster configuration."""

    def __init__(self):
        self.athletes: list[Runner] = []
        self.current_roster: Optional[dict] = None
        self.athletes_loaded = False
        self.session_loaded = False

        self._nfc_capture_active = False
        self._nfc_capture_result = None
        self._nfc_capture_lock = threading.Lock()
        self._nfc_capture_done = threading.Event()
        self._nfc_capture_done.set()
        self._nfc_capture_queue = Queue()
        self._original_nfc_queue = None
        self._nfc_scanner_ref = None

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
        try:
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
            first_name = data.get("first_name", "").strip()
            last_name  = data.get("last_name",  "").strip()
            nfc_tag    = data.get("nfc_tag", "").strip()
            email      = data.get("email", "").strip() or None
            for a in athletes:
                if a.lap_id == athlete_id:
                    a.name     = first_name
                    a.lname    = last_name
                    a.start_id = nfc_tag
                    a.email    = email
                    break
            saved = save_roster(roster_id, roster_meta["name"], athletes)
            if not saved:
                return {"ok": False, "msg": "Failed to save athlete changes."}
            # Keep the in-memory list in sync when the athlete belongs to the active roster
            if self.current_roster and self.current_roster["id"] == roster_id:
                for a in self.athletes:
                    if a.lap_id == athlete_id:
                        a.name     = first_name
                        a.lname    = last_name
                        a.start_id = nfc_tag
                        a.email    = email
                        break
            return {"ok": True, "msg": "Athlete updated."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

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

    # ------------------------------------------------------------------
    # NFC tag capture (for assigning tags to athletes in Settings)
    # ------------------------------------------------------------------

    def start_nfc_capture(self, nfc_scanner, timeout_seconds: int = 15) -> dict:
        """Begin capturing the next NFC tag scan into a side-channel queue.

        nfc_scanner is the live NFCReader instance supplied by ScannerManager via AppApi.
        """
        with self._nfc_capture_lock:
            if self._nfc_capture_active:
                return {"ok": False, "msg": "A scan is already in progress."}
            self._nfc_capture_active = True
            self._nfc_capture_result = None
            self._nfc_capture_done.clear()

        # Drain any stale events from a previous capture before reuse.
        while not self._nfc_capture_queue.empty():
            try:
                self._nfc_capture_queue.get_nowait()
            except Empty:
                break

        self._nfc_scanner_ref = nfc_scanner
        self._original_nfc_queue = nfc_scanner.queue
        nfc_scanner.queue = self._nfc_capture_queue

        threading.Thread(
            target=self._nfc_capture_worker,
            args=(timeout_seconds,),
            daemon=True,
        ).start()
        return {"ok": True}

    def _nfc_capture_worker(self, timeout_seconds: int) -> None:
        try:
            event = self._nfc_capture_queue.get(timeout=timeout_seconds)
            if event is None:
                result = {"ok": False, "msg": "Scan cancelled."}
            else:
                result = {"ok": True, "tag": event.id}
        except Empty:
            result = {"ok": False, "msg": "Scan timed out."}
        finally:
            if self._nfc_scanner_ref:
                self._nfc_scanner_ref.queue = self._original_nfc_queue
            self._nfc_scanner_ref = None
            with self._nfc_capture_lock:
                self._nfc_capture_result = result
                self._nfc_capture_active = False
            self._nfc_capture_done.set()

    def poll_nfc_capture(self) -> dict:
        """Return the current capture state. Clears the result once it's been read."""
        with self._nfc_capture_lock:
            if self._nfc_capture_active and self._nfc_capture_result is None:
                return {"ok": False, "pending": True}
            result = self._nfc_capture_result
            self._nfc_capture_result = None
        return result if result is not None else {"ok": False, "pending": False, "msg": "No scan in progress."}

    def cancel_nfc_capture(self) -> dict:
        """Cancel an in-progress capture and wait for the worker to finish."""
        with self._nfc_capture_lock:
            if not self._nfc_capture_active:
                return {"ok": True}
        if self._nfc_capture_queue:
            self._nfc_capture_queue.put(None)
        self._nfc_capture_done.wait(timeout=2.0)
        return {"ok": True}
