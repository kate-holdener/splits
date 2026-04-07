"""
Interval Training GUI - pywebview-based GUI for the Interval Training CLI.

Dependencies:
    pip install pywebview

Usage:
    python interval_training_gui.py

The HTML/CSS/JS frontend communicates with the Python backend via
webview's JavaScript API (js_api). All CLI business logic is preserved;
only the presentation layer changes.
"""

import webview
import os
from api.IntervalTrackApi import IntervalTrackApi
import json as _json


class PyWebViewAPI:
    def __init__(self):
        self.track_api = IntervalTrackApi()
    def log(self, data):
        print(data)

    def get_state(self):
        return self.track_api.get_state()
    
    def load_athletes(self, csv_path: str):
        return self.track_api.load_athletes(csv_path)
    
    def configure_workout(self, distance: str, laps: str):
        return self.track_api.configure_workout(distance, laps)
    
    def connect_rfid(self):
        return self.track_api.connect_rfid()
    
    def connect_rfid_manually(self, address: str, port: int, protocol: str):
        pass

    def list_athletes(self):
        return self.track_api.list_athletes()

    def list_athletes_with_status(self):
        return self.track_api.list_athletes_with_status()
    
    def connect_nfc(self):
        return self.track_api.connect_nfc()

    def start_selected(self, tag_ids_json: str):
        try:
            tag_ids = _json.loads(tag_ids_json)
            self.track_api.start_selected(tag_ids)
        except Exception:
            return {"ok": False, "msg": "Invalid tag IDs format."}
    
    def get_resting(self):
        return self.track_api.get_resting()
    
    def finish_workout(self):
        return self.track_api.finish_workout()
    # ------------------------------------------------------------------
    # File dialog – called from JS to open a native CSV picker
    # ------------------------------------------------------------------
    def pick_csv_file(self):
        import webview as _wv
        # create_file_dialog returns a tuple of selected paths, or None
        result = _wv.windows[0].create_file_dialog(
            dialog_type=_wv.OPEN_DIALOG,
            allow_multiple=False,
            file_types=('CSV files (*.csv)', 'All files (*.*)')
        )
        if result and len(result) > 0:
            return {"path": result[0]}
        return {"path": None}
    
    def add_resting_window(self, resting_window):
        self.resting_window = resting_window

    # ------------------------------------------------------------------
    # Option 2 – Configure workout
    # ------------------------------------------------------------------
    def configure_workout(self, distance: str, laps: str, rest_time: str = "0"):
        try:
            dist_int = int(distance)
            laps_int = int(laps)
            rest_int = int(rest_time)
            self.workout = Workout(datetime.now())
            self.workout.configure(dist_int, laps_int, rest_int)
            self.workout_configured = True
            if self.athletes:
                for a in self.athletes:
                    a.add_workout(self.workout)
            return {
                "ok": True,
                "msg": f"Workout configured: {dist_int}m × {laps_int} laps, {rest_int}s rest.",
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
        return self.connect_rfid_with_address(SCANNER_ADDRESS)

    def connect_rfid_with_address(self, address: str):
        if not (self.athletes_loaded and self.workout_configured):
            return {"ok": False, "msg": "Complete steps 1 and 2 first."}
        try:
            runner_ids = [r.lap_id for r in self.athletes]
            self.rfid_scanner = LLRPReader(self.lap_event_q, address.strip())
            #self.rfid_scanner = ImpinjRestReader(self.lap_event_q, "127.0.0.1:5001")
            self.rfid_scanner.filter_by_id(runner_ids)
            self.rfid_scanner.start()
            self.rfid_connected = True
            self.rfid_scanner_failed = False
            return {"ok": True, "msg": f"RFID scanner connected ({address.strip()}).", "state": self.get_state()}
        except Exception as e:
            self.rfid_scanner_failed = True
            return {"ok": False, "msg": f"RFID failed: {e}", "state": self.get_state()}

    # ------------------------------------------------------------------
    # Option 4 – Connect NFC
    # ------------------------------------------------------------------
    def connect_nfc(self):
        if not (self.athletes_loaded and self.workout_configured):
            return {"ok": False, "msg": "Complete steps 1 and 2 first."}
        try:
            self.nfc_scanner = NFCReader(self.start_event_q)
            self.nfc_scanner.start()
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
    def start_selected(self, tag_ids_json: str):
        import json as _json
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        try:
            tag_ids = _json.loads(tag_ids_json)
        except Exception:
            return {"ok": False, "msg": "Invalid tag IDs format."}
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
    # ------------------------------------------------------------------
    def list_running(self):
        if not self._full_setup_ok():
            return {"ok": False, "msg": "Setup not complete."}
        return {"ok": True, "athletes": [r.to_dict() for r in self.runner_observer.running]}

    # ------------------------------------------------------------------
    # Option 9 – Resting athletes (main window, requires full setup)
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
        rest_duration = (
            self.workout.rest_duration_seconds
            if self.workout and hasattr(self.workout, 'rest_duration_seconds')
            else 90
        )
        athletes = []
        for r in self.runner_observer.resting:
            d = r.to_dict()
            d['rest_elapsed'] = round(self.runner_observer.rest_elapsed(r), 1)
            d['rest_duration'] = rest_duration
            athletes.append(d)
        return {"ok": True, "athletes": athletes}

    # ------------------------------------------------------------------
    # Option 10 – Performance
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
    # Option 12 – Generate reports
    # ------------------------------------------------------------------
    def generate_reports(self, directory: str):
        if not directory.strip():
            return {"ok": False, "msg": "Directory path is required."}
        # Placeholder – wire up your real report generation here
        return {
            "ok": True,
            "msg": f"Reports generated in: {directory.strip()}",
            "files": ["athlete_summary.pdf", "lap_times.csv", "workout_overview.html"]
        }

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
    # Session Management
    # ------------------------------------------------------------------
    def _load_session_on_startup(self):
        """Load previous athlete session on application startup."""
        try:
            from persistence.athlete_persistence import load_athletes_from_session, session_exists
            
            if not session_exists():
                print("No previous session found")
                return
            
            athletes = load_athletes_from_session(self.SESSION_FILE_PATH)
            if athletes:
                self.init_athletes(athletes)           
                print(f"Session loaded: {len(self.athletes)} athletes from previous session")
            else:
                print("Failed to load previous session")
                
        except Exception as e:
            print(f"Error loading session on startup: {e}")
    
    def _save_session(self):
        """Save current athletes to session file."""
        try:
            from persistence.athlete_persistence import save_athletes_to_session
            
            if self.athletes:
                success = save_athletes_to_session(self.athletes, self.SESSION_FILE_PATH)
                if success:
                    print(f"Session saved: {len(self.athletes)} athletes")
                else:
                    print("Failed to save session")
            else:
                print("No athletes to save")
                
        except Exception as e:
            print(f"Error saving session: {e}")
    
    def clear_session(self):
        """Clear the current session (called from frontend)."""
        try:
            from persistence.athlete_persistence import clear_session
            
            success = clear_session()
            if success:
                # Reset application state
                self.athletes = []
                self.athletes_loaded = False
                self.session_loaded = False
                self.csv_file = None
                
                # Stop timer if running
                if self.timer:
                    self.timer.stop()
                    self.timer = None
                
                return {"ok": True, "msg": "Session cleared", "state": self.get_state()}
            else:
                return {"ok": False, "msg": "Failed to clear session"}
                
        except Exception as e:
            return {"ok": False, "msg": f"Error clearing session: {e}"}
    
    def get_session_info(self):
        """Get information about the current session (called from frontend)."""
        try:
            from persistence.athlete_persistence import session_exists
            
            return {
                "ok": True,
                "sessionExists": session_exists(),
                "sessionLoaded": self.session_loaded,
                "athleteCount": len(self.athletes),
                "athletesLoaded": self.athletes_loaded
            }
            
        except Exception as e:
            return {"ok": False, "msg": f"Error getting session info: {e}"}

    def shutdown(self):
        if self.timer:
            self.timer.stop()
        return {"ok": True}


    def show_resting_runners(self):
        print('show resting runners')
        print(self.resting_window)
        if self.resting_window:
            self.resting_window.show()
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    api = PyWebViewAPI()
    
    # Get HTML path - check environment variable first (for bundled app)
    html_path = os.environ.get('GUI_HTML_PATH', os.path.join(os.path.dirname(__file__), "html"))
    ui_path = os.path.join(html_path, "index.html")
    
    # Primary window
    main_window = webview.create_window(
        title="IntervalTrack",
        url=ui_path,
        js_api=api,
        width=1100,
        height=720,
        min_size=(900, 600),
        background_color="#000000",
    )

    # Secondary window – resting runners (shares the same Api instance)
    resting_path=os.path.join(os.path.dirname(__file__), "html", "resting.html")
    resting_window = webview.create_window(
        title="Resting Runners",
        url=resting_path,
        js_api=api,
        width=600,
        height=800,
        min_size=(400, 500),
        background_color="#000000",
        x=1120,
        y=0,
        hidden=True
    )
    api.add_resting_window(resting_window)

    def on_closing_resting():
        print('hiding resting runners')
        resting_window.hide()
        return False

    resting_window.events.closing += on_closing_resting

    def on_closed():
        resting_window.events.closing -= on_closing_resting
        resting_window.destroy()
        api.shutdown()

    main_window.events.closed += on_closed
    webview.start(debug=False)


if __name__ == "__main__":
    main()
