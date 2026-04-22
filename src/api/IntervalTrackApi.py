import uuid
from datetime import datetime

from entity.runner import Runner
from entity.RunnerState import RunnerState
from parser.runner_parser import parse_runner_data
from persistence.roster_persistence import (
    get_active_roster,
    create_roster as _create_roster,
    load_roster,
    merge_athletes_from_csv,
    list_rosters as _list_rosters,
    set_active_roster,
    list_all_rosters as _list_all_rosters,
)
from persistence.session_persistence import restore_session_from_dict

from api.workout_manager import WorkoutManager
from api.session_history_manager import SessionHistoryManager
from api.scanner_manager import ScannerManager
from api.roster_manager import RosterManager
from api.workout_session import WorkoutSession


class AppApi:
    """
    Lightweight coordinator that owns one instance of each sub-manager and handles
    cross-cutting orchestration (athlete initialization, timer lifecycle, workout wiring).
    Sub-managers are exposed as public attributes so callers can access them directly.
    """

    def __init__(self):
        self.workout = WorkoutManager()
        self.history = SessionHistoryManager()
        self.session = WorkoutSession()
        self.scanner = ScannerManager(self.session.lap_event_q, self.session.start_event_q)
        self.roster  = RosterManager()

        self._load_active_roster()
        self.session.check_for_recovery()

    # ------------------------------------------------------------------
    # Aggregated state for the frontend
    # ------------------------------------------------------------------
    def get_state(self):
        return {
            "athletesLoaded":      self.roster.athletes_loaded,
            "workoutConfigured":   self.workout.workout_configured,
            "rfidConnected":       self.scanner.rfid_connected,
            "nfcConnected":        self.scanner.nfc_connected,
            "rfidFailed":          self.scanner.rfid_scanner_failed,
            "nfcFailed":           self.scanner.nfc_scanner_failed,
            "workoutActive":       self.session.workout_active,
            "athleteCount":        len(self.roster.athletes),
            "sessionLoaded":       self.roster.session_loaded,
            "currentRoster":       self.roster.current_roster,
            "rfidProtocol":        self.scanner.rfid_protocol,
            "rfidAddress":         self.scanner.rfid_address,
            "rfidPort":            self.scanner.rfid_port,
            "currentWorkoutConfig": self.workout.current_workout_config,
        }

    # ------------------------------------------------------------------
    # Athlete initialization (internal orchestration)
    # ------------------------------------------------------------------
    def _init_athletes(self, athletes):
        """Set up athletes with observers and (re)start the timer."""
        self.roster.athletes = athletes
        self.roster.athletes_loaded = bool(athletes)
        for a in athletes:
            a.add_observer(self.session.runner_observer)
            if self.session.session_persistence is not None:
                a.add_observer(self.session.session_persistence)
        if self.workout.workout:
            for a in athletes:
                a.add_workout(self.workout.workout)
        self.session._start_timer(athletes)

    def _load_active_roster(self):
        """Load the active roster on application startup."""
        try:
            roster = get_active_roster()
            if not roster:
                return
            self.roster.current_roster = roster
            athletes = load_roster(roster["id"])
            if athletes:
                self._init_athletes(athletes)
                self.roster.session_loaded = True
        except Exception as e:
            print(f"Error loading active roster on startup: {e}")

    # ------------------------------------------------------------------
    # Roster management (orchestrated — touch timer + roster data)
    # ------------------------------------------------------------------
    def select_roster(self, roster_id: str):
        try:
            roster = set_active_roster(roster_id)
            if not roster:
                return {"ok": False, "msg": f"Roster '{roster_id}' not found."}
            self.roster.current_roster = roster
            athletes = load_roster(roster_id)
            self.session._stop_timer()
            self._init_athletes(athletes or [])
            self.roster.session_loaded = bool(athletes)
            return {"ok": True, "msg": f"Roster '{roster['name']}' selected.",
                    "roster": roster, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def create_roster(self, name: str):
        if not name or not name.strip():
            return {"ok": False, "msg": "Roster name is required."}
        try:
            roster = _create_roster(name.strip())
            self.roster.current_roster = roster
            self.session._stop_timer()
            self.roster.athletes = []
            self.roster.athletes_loaded = False
            self.roster.session_loaded = False
            rosters = _list_rosters()
            return {"ok": True, "msg": f"Roster '{roster['name']}' created.",
                    "roster": roster, "rosters": rosters, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def add_athletes_from_csv(self, csv_path: str):
        if not csv_path.strip():
            return {"ok": False, "msg": "CSV file path is required."}
        if not self.roster.current_roster:
            return {"ok": False, "msg": "No active roster. Create a roster first."}
        try:
            new_runners = parse_runner_data(csv_path.strip())
            counts = merge_athletes_from_csv(
                self.roster.current_roster["id"],
                self.roster.current_roster["name"],
                new_runners,
            )
            merged = load_roster(self.roster.current_roster["id"])
            self.session._stop_timer()
            self._init_athletes(merged or [])
            rosters = _list_rosters()
            msg = f"Added {counts['added']}, updated {counts['updated']} athletes ({counts['total']} total)."
            return {"ok": True, "msg": msg, "counts": counts, "rosters": rosters, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def add_athletes_to_roster_from_csv(self, roster_id: str, csv_path: str):
        if not roster_id or not roster_id.strip():
            return {"ok": False, "msg": "Roster ID is required."}
        if not csv_path.strip():
            return {"ok": False, "msg": "CSV file path is required."}
        try:
            rosters = _list_all_rosters()
            roster = next((r for r in rosters if r["id"] == roster_id), None)
            if not roster:
                return {"ok": False, "msg": f"Roster '{roster_id}' not found."}
            new_runners = parse_runner_data(csv_path.strip())
            counts = merge_athletes_from_csv(roster_id, roster["name"], new_runners)
            if self.roster.current_roster and self.roster.current_roster["id"] == roster_id:
                merged = load_roster(roster_id)
                self.session._stop_timer()
                self._init_athletes(merged or [])
            msg = f"Added {counts['added']}, updated {counts['updated']} athletes to {roster['name']} ({counts['total']} total)."
            return {"ok": True, "msg": msg, "counts": counts}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def archive_roster(self, roster_id: str):
        result = self.roster.archive_roster(roster_id)
        if result.get("ok") and result.pop("_cleared_current", False):
            self.session._stop_timer()
        result["state"] = self.get_state()
        return result

    def restore_athlete(self, athlete_id: str):
        try:
            from persistence.roster_persistence import find_athlete_by_id, restore_athlete as _restore_athlete
            result = find_athlete_by_id(athlete_id)
            if not result:
                return {"ok": False, "msg": "Athlete not found."}
            roster_id, athlete = result
            success = _restore_athlete(roster_id, athlete_id)
            if success:
                if self.roster.current_roster and self.roster.current_roster["id"] == roster_id:
                    already_present = any(a.lap_id == athlete_id for a in self.roster.athletes)
                    if not already_present:
                        athlete.archived = False
                        athlete.add_observer(self.session.runner_observer)
                        if self.workout.workout:
                            athlete.add_workout(self.workout.workout)
                        self.roster.athletes.append(athlete)
                return {"ok": True, "msg": "Athlete activated.", "state": self.get_state()}
            return {"ok": False, "msg": "Failed to activate athlete."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def archive_athlete(self, athlete_id: str):
        result = self.roster.archive_athlete(athlete_id)
        if result.get("ok"):
            result["state"] = self.get_state()
        return result

    def load_athletes(self, csv_path: str):
        """Backward-compatibility alias for add_athletes_from_csv."""
        return self.add_athletes_from_csv(csv_path)

    def clear_session(self):
        """Clear the current athlete roster."""
        self.session._stop_timer()
        self.roster.athletes = []
        self.roster.athletes_loaded = False
        self.roster.session_loaded = False
        return {"ok": True, "msg": "Athletes cleared.", "state": self.get_state()}

    # ------------------------------------------------------------------
    # Workout configuration (orchestrated — pushes workout to athletes)
    # ------------------------------------------------------------------
    def configure_workout(self, distance: int, laps: int, rest: int):
        try:
            new_workout = self.workout._set_workout(distance, laps, rest)
            for a in self.roster.athletes:
                a.add_workout(new_workout)
            if self.session.session_persistence is None and self.roster.current_roster:
                self.session._wire_session_persistence(
                    session_id=str(uuid.uuid4()),
                    roster_id=self.roster.current_roster["id"],
                    athletes=self.roster.athletes,
                )
            return {
                "ok": True,
                "msg": f"Workout configured: {distance}m × {laps} laps with {rest} second rest.",
                "state": self.get_state(),
            }
        except ValueError:
            return {"ok": False, "msg": "Invalid input – please enter numeric values."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def save_and_configure_workout(self, distance: int, laps: int, rest: int):
        try:
            workout_entry = self.workout.save_workout_entry(distance, laps, rest)
            result = self.configure_workout(distance, laps, rest)
            if result["ok"]:
                self.workout.current_workout_config = workout_entry
                result["state"] = self.get_state()
                result["workouts"] = self.workout.get_all_workouts()
                result["workout_config"] = workout_entry
            return result
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # Live workout controls (orchestrated — span session + roster)
    # ------------------------------------------------------------------
    def start_selected(self, tag_ids: list):
        if not tag_ids:
            return {"ok": False, "msg": "No athletes selected."}
        valid_ids = {a.start_id for a in self.roster.athletes}
        ids_to_start = [t for t in tag_ids if t in valid_ids]
        if not ids_to_start:
            return {"ok": False, "msg": "None of the selected tag IDs match known athletes."}
        self.session.manual_start_controller.start(ids_to_start)
        self.session.workout_active = True
        return {"ok": True, "msg": f"Started {len(ids_to_start)} athletes.", "state": self.get_state()}

    def list_athletes_with_status(self):
        running_ids = {id(r) for r in self.session.runner_observer.running}
        resting_ids = {id(r) for r in self.session.runner_observer.resting}
        now_ms = datetime.now().timestamp() * 1000
        result = []
        for a in self.roster.athletes:
            if getattr(a, 'archived', False):
                continue
            d = a.to_dict()
            all_intervals = a.get_intervals()
            completed = [iv for iv in all_intervals if not iv.incomplete]
            in_progress = [iv for iv in all_intervals if iv.incomplete]
            d['intervals'] = [iv.get_end_time() - iv.get_start_time() for iv in completed]
            rests = [
                completed[i + 1].get_start_time() - completed[i].get_end_time()
                for i in range(len(completed) - 1)
            ]
            if completed and in_progress:
                rests.append(in_progress[0].start_time - completed[-1].get_end_time())
            d['rests'] = rests
            if id(a) in running_ids:
                elapsed = round((now_ms - all_intervals[-1].start_time) / 1000) if all_intervals else 0
                d['status'] = 'RUNNING'
                d['elapsed_seconds'] = max(0, elapsed)
            elif id(a) in resting_ids:
                rest_duration = self.workout.workout.get_rest_time()
                rest_elapsed = self.session.runner_observer.rest_elapsed(a)
                d['status'] = 'RESTING'
                d['elapsed_seconds'] = round(rest_elapsed)
                d['rest_remaining_seconds'] = max(0, round(rest_duration - rest_elapsed))
            else:
                d['status'] = 'INACTIVE'
                d['elapsed_seconds'] = None
            result.append(d)
        return {"ok": True, "athletes": result}

    def finish_workout(self):
        last_id = self.session.finish_workout()
        self.history._last_session_id = last_id
        return {"ok": True, "msg": "Workout finished.", "state": self.get_state()}

    def shutdown(self):
        return self.session.shutdown()

    # ------------------------------------------------------------------
    # Session recovery (orchestrated — restores athletes + wires session)
    # ------------------------------------------------------------------
    def resume_session(self) -> dict:
        """Restore a previously interrupted workout session."""
        if not self.session.pending_recovery:
            return {"ok": False, "msg": "No pending session."}
        try:
            athletes = restore_session_from_dict(self.session.pending_recovery)
            first_workout = athletes[0].current_workout if athletes else None
            self.workout.workout = first_workout
            self.workout.workout_configured = bool(first_workout)
            self.workout.current_workout_config = {
                "distance": first_workout.interval_distance,
                "laps":     first_workout.laps_per_interval,
                "rest":     first_workout.rest_time,
            } if first_workout else None
            roster_id = self.session.pending_recovery.get("roster_id")
            self.session._stop_timer()
            self._init_athletes(athletes)
            for a in self.roster.athletes:
                self.session.runner_observer.update(a)
                if a.current_status == RunnerState.RESTING:
                    completed = [iv for iv in a.intervals if not iv.incomplete]
                    if completed:
                        self.session.runner_observer._rest_start[id(a)] = completed[-1].end_time / 1000
            self.session._wire_session_persistence(
                session_id=self.session.pending_recovery["session_id"],
                roster_id=roster_id,
                athletes=self.roster.athletes,
            )
            self.session.workout_active = True
            self.session.pending_recovery = None
            return {"ok": True, "msg": "Session resumed.", "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": f"Failed to resume: {e}"}


# Backward-compatibility alias so existing imports keep working.
SplitsApi = AppApi
