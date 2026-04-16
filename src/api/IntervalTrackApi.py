from queue import Queue
from typing import Optional
from datetime import datetime

from interactors.interval_timer import IntervalTimer
from readers.acr122u_nfc import NFCReader
from reader import Reader
from controller.start_controller import ManualStartController
from api.runnerObserver import RunnerObserver
from entity.runner import Runner
from entity.workout import Workout
from parser.runner_parser import parse_runner_data
from discovery.auto_connect import auto_connect_to_rfid_scanner, connect_rfid_with_scanner_info
from persistence.roster_persistence import (
    get_active_roster, create_roster as _create_roster,
    load_roster, merge_athletes_from_csv,
    list_rosters as _list_rosters, set_active_roster,
    list_all_rosters as _list_all_rosters
)
from persistence.scanner_persistence import save_scanner_config, load_scanner_config
from persistence.workout_persistence import (
    list_workouts as _list_workouts,
    save_workout as _save_workout,
    get_workout_by_id as _get_workout_by_id,
)

class IntervalTrackApi:

    def __init__(self):
        self.athletes: list[Runner] = []
        self.workout: Optional[object] = None
        self.current_roster: Optional[dict] = None  # {id, name, created_at}

        self.rfid_connected = False
        self.nfc_connected = False
        self.rfid_scanner_failed = False
        self.nfc_scanner_failed = False
        self.athletes_loaded = False
        self.workout_configured = False
        self.workout_active = False
        self.session_loaded = False  # True when an active roster with athletes is loaded
        self.current_workout_config: Optional[dict] = None  # {distance, laps, rest}

        # Protocol information for scanners
        self.rfid_protocol = None      # 'llrp' or 'rest' when connected
        self.rfid_address = None       # IP address when connected
        self.rfid_port = None          # Port number when connected
        
        # Load saved scanner configuration for potential auto-connect
        self.saved_scanner_config = load_scanner_config()

        self.runner_observer = RunnerObserver()

        self.start_event_q = Queue()
        self.lap_event_q = Queue()
        self.manual_start_controller = ManualStartController(self.start_event_q)

        self.nfc_scanner = None
        self.rfid_scanner = None
        self.timer = None

        self.resting_window = None

        # Load the active roster on startup
        self._load_active_roster()



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
            "sessionLoaded": self.session_loaded,
            "currentRoster": self.current_roster,
            # Protocol information for scanners
            "rfidProtocol": self.rfid_protocol,
            "rfidAddress": self.rfid_address,
            "rfidPort": self.rfid_port,
            "currentWorkoutConfig": self.current_workout_config,
        }

    # ------------------------------------------------------------------
    # Roster management
    # ------------------------------------------------------------------
    def get_current_roster(self):
        return {"ok": True, "roster": self.current_roster}

    def list_rosters(self):
        try:
            rosters = _list_rosters()
            return {"ok": True, "rosters": rosters}
        except Exception as e:
            return {"ok": False, "msg": str(e), "rosters": []}

    def list_all_rosters_with_archived(self):
        try:
            rosters = _list_all_rosters()
            return {"ok": True, "rosters": rosters}
        except Exception as e:
            return {"ok": False, "msg": str(e), "rosters": []}

    def select_roster(self, roster_id: str):
        try:
            roster = set_active_roster(roster_id)
            if not roster:
                return {"ok": False, "msg": f"Roster '{roster_id}' not found."}
            self.current_roster = roster
            athletes = load_roster(roster_id)
            self._stop_timer()
            self.init_athletes(athletes or [])
            self.session_loaded = bool(athletes)
            return {"ok": True, "msg": f"Roster '{roster['name']}' selected.", "roster": roster, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def create_roster(self, name: str):
        if not name or not name.strip():
            return {"ok": False, "msg": "Roster name is required."}
        try:
            roster = _create_roster(name.strip())
            self.current_roster = roster
            self._stop_timer()
            self.athletes = []
            self.athletes_loaded = False
            self.session_loaded = False
            rosters = _list_rosters()
            return {"ok": True, "msg": f"Roster '{roster['name']}' created.", "roster": roster, "rosters": rosters, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def add_athletes_from_csv(self, csv_path: str):
        if not csv_path.strip():
            return {"ok": False, "msg": "CSV file path is required."}
        if not self.current_roster:
            return {"ok": False, "msg": "No active roster. Create a roster first."}
        try:
            new_runners = parse_runner_data(csv_path.strip())
            counts = merge_athletes_from_csv(
                self.current_roster["id"],
                self.current_roster["name"],
                new_runners
            )
            merged = load_roster(self.current_roster["id"])
            self._stop_timer()
            self.init_athletes(merged or [])
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
            counts = merge_athletes_from_csv(
                roster_id,
                roster["name"],
                new_runners
            )

            # If this is the current roster, refresh the athletes
            if self.current_roster and self.current_roster["id"] == roster_id:
                merged = load_roster(roster_id)
                self._stop_timer()
                self.init_athletes(merged or [])

            msg = f"Added {counts['added']}, updated {counts['updated']} athletes to {roster['name']} ({counts['total']} total)."
            return {"ok": True, "msg": msg, "counts": counts}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # Archive functionality
    # ------------------------------------------------------------------
    def archive_roster(self, roster_id: str):
        try:
            from persistence.roster_persistence import archive_roster as _archive_roster
            success = _archive_roster(roster_id)
            if success:
                rosters = _list_rosters()
                if self.current_roster and self.current_roster["id"] == roster_id:
                    self.current_roster = None
                    self._stop_timer()
                    self.athletes = []
                    self.athletes_loaded = False
                    self.session_loaded = False
                return {"ok": True, "msg": "Roster archived successfully.", "rosters": rosters, "state": self.get_state()}
            else:
                return {"ok": False, "msg": "Failed to archive roster."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def restore_roster(self, roster_id: str):
        try:
            from persistence.roster_persistence import restore_roster as _restore_roster
            success = _restore_roster(roster_id)
            if success:
                rosters = _list_rosters()
                return {"ok": True, "msg": "Roster restored successfully.", "rosters": rosters}
            else:
                return {"ok": False, "msg": "Failed to restore roster."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def list_all_athletes(self):
        try:
            from persistence.roster_persistence import list_all_athletes as _list_all_athletes
            athletes = _list_all_athletes()
            return {"ok": True, "athletes": athletes}
        except Exception as e:
            return {"ok": False, "msg": str(e), "athletes": []}

    def list_athletes_for_roster_including_archived(self, roster_id: str):
        try:
            from persistence.roster_persistence import load_roster
            from serializer.json_serializer import runner_to_json
            athletes = load_roster(roster_id, include_archived=True)
            athletes_data = [runner_to_json(a) for a in (athletes or [])]
            return {"ok": True, "athletes": athletes_data}
        except Exception as e:
            return {"ok": False, "msg": str(e), "athletes": []}

    def archive_athlete(self, athlete_id: str):
        try:
            from persistence.roster_persistence import find_athlete_by_id, archive_athlete as _archive_athlete
            result = find_athlete_by_id(athlete_id)
            if not result:
                return {"ok": False, "msg": "Athlete not found."}

            roster_id, athlete = result
            success = _archive_athlete(roster_id, athlete_id)
            if success:
                # Remove from the live athletes list without restarting the timer
                if self.current_roster and self.current_roster["id"] == roster_id:
                    self.athletes[:] = [a for a in self.athletes if a.lap_id != athlete_id]
                return {"ok": True, "msg": "Athlete deactivated.", "state": self.get_state()}
            else:
                return {"ok": False, "msg": "Failed to deactivate athlete."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def restore_athlete(self, athlete_id: str):
        try:
            from persistence.roster_persistence import find_athlete_by_id, restore_athlete as _restore_athlete
            result = find_athlete_by_id(athlete_id)
            if not result:
                return {"ok": False, "msg": "Athlete not found."}

            roster_id, athlete = result
            success = _restore_athlete(roster_id, athlete_id)
            if success:
                # Add the athlete back to the live list without restarting the timer
                if self.current_roster and self.current_roster["id"] == roster_id:
                    already_present = any(a.lap_id == athlete_id for a in self.athletes)
                    if not already_present:
                        athlete.archived = False
                        athlete.add_observer(self.runner_observer)
                        if self.workout:
                            athlete.add_workout(self.workout)
                        self.athletes.append(athlete)
                return {"ok": True, "msg": "Athlete activated.", "state": self.get_state()}
            else:
                return {"ok": False, "msg": "Failed to activate athlete."}
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
            self.current_workout_config = {"distance": distance, "laps": laps, "rest": rest}
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
    # Workout persistence
    # ------------------------------------------------------------------
    def list_workouts(self):
        """Return all saved workout configurations."""
        try:
            return {"ok": True, "workouts": _list_workouts()}
        except Exception as e:
            return {"ok": False, "msg": str(e), "workouts": []}

    def save_and_configure_workout(self, distance: int, laps: int, rest: int):
        """
        Persist the workout configuration and apply it to the current session.

        If an identical workout (same distance, laps, rest) already exists in the
        saved list it is returned as-is rather than duplicated.
        """
        try:
            workout_entry = _save_workout(distance, laps, rest)
            result = self.configure_workout(distance, laps, rest)
            if result["ok"]:
                # Store the full entry (including id) so the frontend can use it directly
                self.current_workout_config = workout_entry
                result["state"] = self.get_state()
                result["workouts"] = _list_workouts()
                result["workout_config"] = workout_entry
            return result
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # Option 3 – Connect RFID
    # ------------------------------------------------------------------
    def connect_rfid(self):
        """Connect to RFID scanner with auto-discovery."""
        if not (self.athletes_loaded and self.workout_configured):
            return {"ok": False, "msg": "Complete steps 1 and 2 first.", "state": self.get_state()}

        try:
            self.rfid_scanner = auto_connect_to_rfid_scanner()
            self.rfid_scanner.start(self.lap_event_q)
            self.rfid_connected = True
            
            # Get the connection information directly from the reader
            reader_protocol = self.rfid_scanner.get_protocol().lower()
            reader_address = self.rfid_scanner.get_address()
            reader_port = self.rfid_scanner.get_port()
            
            # Store normalized values
            self.rfid_protocol = reader_protocol
            if reader_protocol == 'llrp':
                # LLRP get_address() returns "host:port"
                hostname = reader_address.split(':')[0]
            else:
                # REST get_address() returns "http://host:port"
                hostname = reader_address.replace('http://', '').split(':')[0]
            
            self.rfid_address = hostname
            self.rfid_port = reader_port

            connection_details = {
                "address": hostname,
                "port": reader_port,
                "protocol": reader_protocol
            }
            
            # Persist successful auto-connection
            save_scanner_config(hostname, reader_port, reader_protocol)

            return {
                "ok": True, 
                "msg": f"Connected to {reader_protocol.upper()} on {hostname}:{reader_port}", 
                "state": self.get_state(),
                "connection_details": connection_details
            }
        except Exception as e:
            return {"ok": False, "msg": f"Auto-connection failed: {e}", "state": self.get_state()}

    def connect_rfid_with_address(self, address: str):
        """Connect to RFID scanner at a specific IP address, trying LLRP then REST."""
        if not address or not address.strip():
            return {"ok": False, "msg": "IP address is required.", "state": self.get_state()}
        address = address.strip()
        # Try LLRP first, then REST
        for protocol in ('llrp', 'rest'):
            scanner_info = {"address": address, "protocol": protocol, "port": 5084}
            result, reader = connect_rfid_with_scanner_info(scanner_info)
            if result["ok"] and reader:
                reader.start(self.lap_event_q)
                self.rfid_scanner = reader
                self.rfid_connected = True
                self.rfid_scanner_failed = False
                self.rfid_protocol = protocol  # Use the input protocol, already validated
                self.rfid_address = address.strip()
                self.rfid_port = 5084
                
                # Persist successful connection
                save_scanner_config(address.strip(), 5084, protocol)
                
                return {"ok": True, "msg": f"Connected via {protocol.upper()} to {address}:5084", "state": self.get_state()}
        self.rfid_scanner_failed = True
        return {"ok": False, "msg": f"Could not connect to RFID scanner at {address}.", "state": self.get_state()}

    def connect_rfid_manual(self, address: str, port: int, protocol: str):
        """Connect to RFID scanner with manual configuration (IP, port, protocol)."""
        if not address or not address.strip():
            return {"ok": False, "msg": "IP address is required.", "state": self.get_state()}
        if protocol not in ('llrp', 'rest'):
            return {"ok": False, "msg": "Protocol must be 'llrp' or 'rest'.", "state": self.get_state()}
        if not isinstance(port, int) or port < 1 or port > 65535:
            return {"ok": False, "msg": "Port must be between 1 and 65535.", "state": self.get_state()}
            
        address = address.strip()
        scanner_info = {"address": address, "protocol": protocol, "port": port}
        result, reader = connect_rfid_with_scanner_info(scanner_info)
        
        if result["ok"] and reader:
            reader.start(self.lap_event_q)
            self.rfid_scanner = reader
            self.rfid_connected = True
            self.rfid_scanner_failed = False
            self.rfid_protocol = reader.get_protocol().lower()  # Normalize to lowercase
            self.rfid_address = address.strip()  # Store the original address, not display format
            self.rfid_port = port
            
            # Persist successful connection parameters
            save_scanner_config(address.strip(), port, protocol)
            
            return {"ok": True, "msg": f"Connected via {protocol.upper()} to {address}:{port}", "state": self.get_state()}
        else:
            self.rfid_scanner_failed = True
            return {"ok": False, "msg": f"Could not connect to RFID scanner at {address}:{port} using {protocol.upper()}.", "state": self.get_state()}

    def get_rfid_connection_info(self):
        return self._get_connection_info(self.rfid_scanner)


    def get_nfc_connection_info(self):
        return self.get_connection_info(self.nfc_scanner)
 
    def _get_connection_info(self, reader: Reader):
        if reader and reader.is_connected():
            return {"connected": True, 
                    "address": self.rfid_scanner.get_address(), 
                    "port": self.rfid_scanner.get_port(),
                    "protocol": self.rfid_scanner.get_protocol()}
        else:
            return {"connected": False}
      
    def get_saved_scanner_config(self):
        """Return the saved scanner configuration if available."""
        return self.saved_scanner_config

    def try_auto_connect_rfid(self):
        """Attempt to auto-connect using saved scanner configuration."""
        if not self.saved_scanner_config:
            return {"ok": False, "msg": "No saved scanner configuration.", "state": self.get_state()}
            
        if self.rfid_connected:
            return {"ok": False, "msg": "RFID scanner already connected.", "state": self.get_state()}
            
        config = self.saved_scanner_config
        return self.connect_rfid_manual(config['hostname'], config['port'], config['protocol'])

    # ------------------------------------------------------------------
    # Option 4 – Connect NFC
    # ------------------------------------------------------------------
    def connect_nfc(self):
        try:
            self.nfc_scanner = NFCReader()
            self.nfc_scanner.start(self.start_event_q)
            self.nfc_connected = True
            self.nfc_scanner_failed = False
            return {"ok": True, "msg": "NFC scanner connected.", "state": self.get_state()}
        except Exception as e:
            self.nfc_scanner_failed = True
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
            if getattr(a, 'archived', False):
                continue
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
                rest_duration = self.workout.get_rest_time()
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
        #if not self._full_setup_ok():
        #    return {"ok": False, "msg": "Setup not complete."}
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
    # Resting athletes – ungated, for the second window
    # ------------------------------------------------------------------
    def get_resting(self):
        """Always returns the current resting list with timing data; no setup check."""
        athletes = []
        for r in self.runner_observer.resting:
            rest_duration = r.get_workout().get_rest_time()
            d = r.to_dict()
            rest_elapsed = self.runner_observer.rest_elapsed(r)
            d['rest_elapsed'] = round(rest_elapsed, 1)
            d['rest_duration'] = rest_duration
            d['rest_remaining_seconds'] = max(0, round(rest_duration - rest_elapsed))
            athletes.append(d)
        return {"ok": True, "athletes": athletes}

    # ------------------------------------------------------------------
    # Option 10 – Performance
    # ------------------------------------------------------------------
    def generate_reports(self, output_dir: str):
        """Generate PDF reports for all athletes with recorded intervals."""
        if not output_dir or not output_dir.strip():
            return {"ok": False, "msg": "Output directory is required."}
        import os
        output_dir = output_dir.strip()
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return {"ok": False, "msg": f"Cannot create directory: {e}"}
        if not self.athletes:
            return {"ok": False, "msg": "No athletes loaded."}
        from report.pdf_report_runner import generate_runner_report
        generated = []
        for athlete in self.athletes:
            if not athlete.get_intervals():
                continue
            safe_name = f"{athlete.name}_{athlete.lname}".replace(" ", "_")
            filename = os.path.join(output_dir, f"{safe_name}_report.pdf")
            try:
                generate_runner_report(athlete, filename)
                generated.append(filename)
            except Exception as e:
                print(f"Failed to generate report for {athlete.name}: {e}")
        if not generated:
            return {"ok": True, "msg": "No athletes with interval data — no reports generated.", "files": []}
        return {"ok": True, "msg": f"Generated {len(generated)} report(s).", "files": generated}

    # ------------------------------------------------------------------
    # Option 11 – Finish workout
    # ------------------------------------------------------------------
    def finish_workout(self):
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
    # Session / Roster Management
    # ------------------------------------------------------------------
    def _load_active_roster(self):
        """Load the active roster on application startup."""
        try:
            roster = get_active_roster()
            if not roster:
                return
            self.current_roster = roster
            athletes = load_roster(roster["id"])
            if athletes:
                self.init_athletes(athletes)
                self.session_loaded = True
            else:
                pass  # roster exists but has no athletes yet
        except Exception as e:
            print(f"Error loading active roster on startup: {e}")

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
        """Return session/roster info for the frontend."""
        return {
            "ok": True,
            "sessionLoaded": self.session_loaded,
            "athleteCount": len(self.athletes),
            "athletesLoaded": self.athletes_loaded,
            "currentRoster": self.current_roster,
        }

    def shutdown(self):
        if self.timer:
            self.timer.stop()
        return {"ok": True}
