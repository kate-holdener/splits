from queue import Queue
from typing import Optional, Set
from datetime import datetime

from interactors.interval_timer import IntervalTimer
from interactors.stats_calculator import calculate_performance
from readers.acr122u_nfc import NFCReader
from controller.start_controller import ManualStartController
from api.runnerObserver import RunnerObserver
from entity.runner import Runner
from entity.workout import Workout
from parser.runner_parser import parse_runner_data
from discovery.auto_connect import auto_connect_to_rfid_scanner
from persistence.season_persistence import (
    get_active_season, create_season as _create_season,
    load_season_roster, merge_athletes_from_csv,
    list_seasons as _list_seasons, set_active_season
)

class IntervalTrackApi:

    def __init__(self):
        self.athletes: list[Runner] = []
        self.workout: Optional[object] = None
        self.current_season: Optional[dict] = None  # {id, name, created_at}

        self.rfid_connected = False
        self.nfc_connected = False
        self.rfid_scanner_failed = False
        self.nfc_scanner_failed = False
        self.athletes_loaded = False
        self.workout_configured = False
        self.workout_active = False
        self.session_loaded = False  # True when an active season with athletes is loaded

        # Protocol information for scanners
        self.rfid_protocol = None      # 'llrp' or 'rest' when connected
        self.rfid_address = None       # IP address when connected
        self.rfid_port = None          # Port number when connected

        self.group_start_athletes: Set = set()
        self.runner_observer = RunnerObserver()

        self.start_event_q = Queue()
        self.lap_event_q = Queue()
        self.manual_start_controller = ManualStartController(self.start_event_q)

        self.nfc_scanner = None
        self.rfid_scanner = None
        self.timer = None

        self.resting_window = None

        # Load the active season's roster on startup
        self._load_active_season()



    # ------------------------------------------------------------------
    # State helper returned to the frontend
    # ------------------------------------------------------------------
    def get_state(self):
        return {
            "athletesLoaded": self.athletes_loaded,
            "workoutConfigured": self.workout_configured,
            "rfidConnected": self.rfid_connected,
            "nfcConnected": self.nfc_connected,
            "rfidFailed": self.rfid_scanner_failed,
            "nfcFailed": self.nfc_scanner_failed,
            "workoutActive": self.workout_active,
            "athleteCount": len(self.athletes),
            "groupCount": len(self.group_start_athletes),
            "sessionLoaded": self.session_loaded,
            "currentSeason": self.current_season,
            # Protocol information for scanners
            "rfidProtocol": self.rfid_protocol,
            "rfidAddress": self.rfid_address,
            "rfidPort": self.rfid_port,
        }

    # ------------------------------------------------------------------
    # Season management
    # ------------------------------------------------------------------
    def get_current_season(self):
        return {"ok": True, "season": self.current_season}

    def list_seasons(self):
        try:
            seasons = _list_seasons()
            return {"ok": True, "seasons": seasons}
        except Exception as e:
            return {"ok": False, "msg": str(e), "seasons": []}

    def select_season(self, season_id: str):
        try:
            season = set_active_season(season_id)
            if not season:
                return {"ok": False, "msg": f"Season '{season_id}' not found."}
            self.current_season = season
            athletes = load_season_roster(season_id)
            self._stop_timer()
            self.init_athletes(athletes or [])
            self.session_loaded = bool(athletes)
            return {"ok": True, "msg": f"Season '{season['name']}' selected.", "season": season, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def create_season(self, name: str):
        if not name or not name.strip():
            return {"ok": False, "msg": "Season name is required."}
        try:
            season = _create_season(name.strip())
            self.current_season = season
            self._stop_timer()
            self.athletes = []
            self.athletes_loaded = False
            self.session_loaded = False
            seasons = _list_seasons()
            return {"ok": True, "msg": f"Season '{season['name']}' created.", "season": season, "seasons": seasons, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def add_athletes_from_csv(self, csv_path: str):
        if not csv_path.strip():
            return {"ok": False, "msg": "CSV file path is required."}
        if not self.current_season:
            return {"ok": False, "msg": "No active season. Create a season first."}
        try:
            new_runners = parse_runner_data(csv_path.strip())
            counts = merge_athletes_from_csv(
                self.current_season["id"],
                self.current_season["name"],
                new_runners
            )
            merged = load_season_roster(self.current_season["id"])
            self._stop_timer()
            self.init_athletes(merged or [])
            seasons = _list_seasons()
            msg = f"Added {counts['added']}, updated {counts['updated']} athletes ({counts['total']} total)."
            return {"ok": True, "msg": msg, "counts": counts, "seasons": seasons, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # Load athletes (kept for backward compatibility)
    # ------------------------------------------------------------------
    def load_athletes(self, csv_path: str):
        return self.add_athletes_from_csv(csv_path)
        
    def init_athletes(self, athletes):
        self.athletes = athletes
        self.athletes_loaded = True
        for a in self.athletes:
            a.add_observer(self.runner_observer)
        if self.workout:
            for a in self.athletes:
                a.add_workout(self.workout) 
        self.timer = IntervalTimer(self.start_event_q, self.lap_event_q, self.athletes)
        self.timer.start()
        self.athletes_loaded = True
        
        return {"ok": True, "msg": f"Loaded {len(self.athletes)} athletes.", "state": self.get_state()}

    # ------------------------------------------------------------------
    # Configure workout
    # ------------------------------------------------------------------
    def configure_workout(self, distance: int, laps: int, rest: int):
        try:
            self.workout = Workout(datetime.now())
            self.workout.configure(distance, laps, rest)
            self.workout_configured = True
            if self.athletes:
                for a in self.athletes:
                    a.add_workout(self.workout)
            return {
                "ok": True,
                "msg": f"Workout configured: {distance}m × {laps} laps with {rest} second rest.",
                "state": self.get_state()
            }
        except ValueError:
            return {"ok": False, "msg": "Invalid input – please enter numeric values."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # Option 3 – Connect RFID
    # ------------------------------------------------------------------
    def connect_rfid(self):
        print("connecting rfid")
        """Connect to RFID scanner with auto-discovery."""
        if not (self.athletes_loaded and self.workout_configured):
            return {"ok": False, "msg": "Complete steps 1 and 2 first.", "state": self.get_state()}
            
        try:
            self.rfid_scanner = auto_connect_to_rfid_scanner()
            self.rfid_scanner.start(self.lap_event_q)
            self.rfid_connected = True
            self.rfid_protocol = self.rfid_scanner.get_protocol()
            self.rfid_address = self.rfid_scanner.get_address()

            return {"ok": True, "msg": f"Connected to {self.rfid_protocol} on {self.rfid_address}", "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": f"Auto-connection failed: {e}", "state": self.get_state()}

    # ------------------------------------------------------------------
    # Option 4 – Connect NFC
    # ------------------------------------------------------------------
    def connect_nfc(self):
        print("Connecting nfc")
        if not (self.athletes_loaded and self.workout_configured):
            print("Not ready")
            return {"ok": False, "msg": "Complete steps 1 and 2 first."}
        try:
            self.nfc_scanner = NFCReader()
            self.nfc_scanner.start(self.start_event_q)
            self.nfc_connected = True
            self.nfc_scanner_failed = False
            print("Connected to NFC")
            return {"ok": True, "msg": "NFC scanner connected.", "state": self.get_state()}
        except Exception as e:
            self.nfc_scanner_failed = True
            print("Failed to connect")
            return {"ok": False, "msg": f"NFC failed: {e}", "state": self.get_state()}

    # ------------------------------------------------------------------
    # Option 5 – List all athletes
    # ------------------------------------------------------------------
    def list_athletes(self):
        return {
            "ok": True,
            "athletes": [a.to_dict() for a in self.athletes]
        }

    # ------------------------------------------------------------------
    # List all athletes with live status (for workout tab)
    # ------------------------------------------------------------------
    def list_athletes_with_status(self):
        running_ids = {id(r) for r in self.runner_observer.running}
        resting_ids = {id(r) for r in self.runner_observer.resting}
        now_ms = datetime.now().timestamp() * 1000
        result = []
        for a in self.athletes:
            d = a.to_dict()

            # Performance: completed interval durations and inter-interval rests (all in ms)
            all_intervals = a.get_intervals()
            completed = [iv for iv in all_intervals if not iv.incomplete]
            in_progress = [iv for iv in all_intervals if iv.incomplete]
            d['intervals'] = [iv.get_end_time() - iv.get_start_time() for iv in completed]
            rests = [
                completed[i + 1].get_start_time() - completed[i].get_end_time()
                for i in range(len(completed) - 1)
            ]
            # If there's a current in-progress interval, compute the rest that preceded it
            if completed and in_progress:
                rests.append(in_progress[0].start_time - completed[-1].get_end_time())
            d['rests'] = rests

            if id(a) in running_ids:
                if all_intervals:
                    elapsed = round((now_ms - all_intervals[-1].start_time) / 1000)
                else:
                    elapsed = 0
                d['status'] = 'RUNNING'
                d['elapsed_seconds'] = max(0, elapsed)
            elif id(a) in resting_ids:
                rest_duration = (
                    self.workout.rest_duration_seconds
                    if self.workout and hasattr(self.workout, 'rest_duration_seconds')
                    else 90
                )
                rest_elapsed = self.runner_observer.rest_elapsed(a)
                d['status'] = 'RESTING'
                d['elapsed_seconds'] = round(rest_elapsed)
                d['rest_remaining_seconds'] = max(0, round(rest_duration - rest_elapsed))
            else:
                d['status'] = 'INACTIVE'
                d['elapsed_seconds'] = None
            result.append(d)
        return {"ok": True, "athletes": result}

    # ------------------------------------------------------------------
    # Start a specific set of athletes by start_tag (new UI)
    # ------------------------------------------------------------------
    def start_selected(self, tag_ids: list[str]):
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        if not tag_ids:
            return {"ok": False, "msg": "No athletes selected."}
        valid_ids = {a.start_id for a in self.athletes}
        ids_to_start = [t for t in tag_ids if t in valid_ids]
        if not ids_to_start:
            return {"ok": False, "msg": "None of the selected tag IDs match known athletes."}
        self.manual_start_controller.start(ids_to_start)
        self.workout_active = True
        return {"ok": True, "msg": f"Started {len(ids_to_start)} athletes.",
                "state": self.get_state()}

    # ------------------------------------------------------------------
    # Option 6 – Add athlete to group start
    # TODO: THIS IS NOT USED
    # ------------------------------------------------------------------
    def add_to_group(self, tag_id: str):
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        for athlete in self.athletes:
            if athlete.start_id == tag_id:
                self.group_start_athletes.add(athlete)
                return {"ok": True, "msg": f"Athlete {tag_id} added to group.",
                        "state": self.get_state()}
        return {"ok": False, "msg": f"No athlete found with tag ID '{tag_id}'."}

    # ------------------------------------------------------------------
    # Option 7 – Start group
    # TODO: THIS IS NOT USED
    # ------------------------------------------------------------------
    def start_group(self):
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        if not self.group_start_athletes:
            return {"ok": False, "msg": "No athletes in the group start."}
        ids = [r.start_id for r in self.group_start_athletes]
        self.manual_start_controller.start(ids)
        self.group_start_athletes.clear()
        self.workout_active = True
        return {"ok": True, "msg": f"Started {len(ids)} athletes: {', '.join(ids)}",
                "state": self.get_state()}

    # ------------------------------------------------------------------
    # Option 8 – Running athletes
    # TODO: THIS IS NOT USED
    # ------------------------------------------------------------------
    def list_running(self):
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        return {"ok": True, "athletes": [r.to_dict() for r in self.runner_observer.running]}

    # ------------------------------------------------------------------
    # Option 9 – Resting athletes (main window, requires full setup)
    # TODO: THIS IS NOT USED
    # ------------------------------------------------------------------
    def list_resting(self):
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        return self.get_resting()

    # ------------------------------------------------------------------
    # Resting athletes – ungated, for the second window
    # ------------------------------------------------------------------
    def get_resting(self):
        """Always returns the current resting list with timing data; no setup check."""
        athletes = []
        for r in self.runner_observer.resting:
            rest_duration = r.get_workout().get_rest_time()
            d = r.to_dict()
            d['rest_elapsed'] = round(self.runner_observer.rest_elapsed(r), 1)
            d['rest_duration'] = rest_duration
            athletes.append(d)
        return {"ok": True, "athletes": athletes}

    # ------------------------------------------------------------------
    # Option 10 – Performance
    # TODO: THIS IS NOT USED
    # ------------------------------------------------------------------
    def view_performance(self):
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        results = []
        for r in self.athletes:
            p = calculate_performance(r)
            results.append({"athlete": r.to_dict(), "performance": str(p) if p else "N/A"})
        return {"ok": True, "results": results}

    # ------------------------------------------------------------------
    # Option 11 – Finish workout
    # ------------------------------------------------------------------
    def finish_workout(self):
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        self.runner_observer.running.clear()
        self.runner_observer.resting.clear()
        self.workout_active = False
        return {"ok": True, "msg": "Workout finished.", "state": self.get_state()}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _full_setup_ok(self) -> bool:
        return (
            self.athletes_loaded and self.workout_configured
            and self.rfid_connected and self.nfc_connected
            and not self.rfid_scanner_failed and not self.nfc_scanner_failed
        )

    # ------------------------------------------------------------------
    # Session / Season Management
    # ------------------------------------------------------------------
    def _load_active_season(self):
        """Load the active season's roster on application startup."""
        try:
            season = get_active_season()
            if not season:
                print("No active season found")
                return
            self.current_season = season
            athletes = load_season_roster(season["id"])
            if athletes:
                self.init_athletes(athletes)
                self.session_loaded = True
                print(f"Season '{season['name']}' loaded: {len(self.athletes)} athletes")
            else:
                print(f"Season '{season['name']}' loaded with empty roster")
        except Exception as e:
            print(f"Error loading active season on startup: {e}")

    def _stop_timer(self):
        """Stop the interval timer if it is running."""
        if self.timer:
            self.timer.stop()
            self.timer = None

    def clear_session(self):
        """Clear the current athlete roster (kept for frontend compatibility)."""
        self._stop_timer()
        self.athletes = []
        self.athletes_loaded = False
        self.session_loaded = False
        return {"ok": True, "msg": "Athletes cleared.", "state": self.get_state()}

    def get_session_info(self):
        """Return session/season info for the frontend."""
        return {
            "ok": True,
            "sessionLoaded": self.session_loaded,
            "athleteCount": len(self.athletes),
            "athletesLoaded": self.athletes_loaded,
            "currentSeason": self.current_season,
        }

    def shutdown(self):
        if self.timer:
            self.timer.stop()
        return {"ok": True}
