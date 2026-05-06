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
from api.IntervalTrackApi import AppApi
import json as _json

# Default (light-mode) background color — must match --bg in shared.css
LIGHT_MODE_BG = "#f0f0f0"

resting_window = None

class PyWebViewAPI:
    def __init__(self):
        self.api = AppApi()
        self._theme = 'light'

    def log(self, data):
        print(data)

    def get_state(self):
        return self.api.get_state()

    def load_athletes(self, csv_path: str):
        return self.api.load_athletes(csv_path)

    # ------------------------------------------------------------------
    # Roster management
    # ------------------------------------------------------------------
    def get_current_roster(self):
        return self.api.roster.get_current_roster()

    def list_rosters(self):
        return self.api.roster.list_rosters()

    def list_all_rosters_with_archived(self):
        return self.api.roster.list_all_rosters_with_archived()

    def create_roster(self, name: str):
        return self.api.create_roster(name)

    def select_roster(self, roster_id: str):
        return self.api.select_roster(roster_id)

    def add_athletes_from_csv(self, csv_path: str):
        return self.api.add_athletes_from_csv(csv_path)

    def add_athletes_to_roster_from_csv(self, roster_id: str, csv_path: str):
        return self.api.add_athletes_to_roster_from_csv(roster_id, csv_path)

    # ------------------------------------------------------------------
    # Archive methods
    # ------------------------------------------------------------------
    def archive_roster(self, roster_id: str):
        return self.api.archive_roster(roster_id)

    def restore_roster(self, roster_id: str):
        return self.api.roster.restore_roster(roster_id)

    def list_all_athletes(self):
        return self.api.roster.list_all_athletes()

    def list_athletes_for_roster_including_archived(self, roster_id: str):
        return self.api.roster.list_athletes_for_roster_including_archived(roster_id)

    def archive_athlete(self, athlete_id: str):
        return self.api.archive_athlete(athlete_id)

    def restore_athlete(self, athlete_id: str):
        return self.api.restore_athlete(athlete_id)

    # ------------------------------------------------------------------
    # Workout configuration
    # ------------------------------------------------------------------
    def configure_workout(self, distance: str, laps: str, rest_time: str, roster_id: str):
        return self.api.configure_workout(int(distance), int(laps), int(rest_time), roster_id)

    def list_workouts(self):
        return self.api.workout.list_workouts()

    def save_and_configure_workout(self, distance: str, laps: str, rest_time: str, roster_id: str):
        return self.api.save_and_configure_workout(int(distance), int(laps), int(rest_time), roster_id)

    # ------------------------------------------------------------------
    # RFID scanner connection methods
    # ------------------------------------------------------------------
    def connect_rfid(self):
        result = self.api.scanner.connect_rfid()
        result["state"] = self.api.get_state()
        return result

    def connect_rfid_with_address(self, address: str):
        result = self.api.scanner.connect_rfid_with_address(address)
        result["state"] = self.api.get_state()
        return result

    def connect_rfid_manual(self, address: str, port: int, protocol: str,
                            tx_power_dbm=None):
        result = self.api.scanner.connect_rfid_manual(address, port, protocol,
                                                      tx_power_dbm=tx_power_dbm)
        result["state"] = self.api.get_state()
        return result

    def get_saved_scanner_config(self):
        return self.api.scanner.get_saved_scanner_config()

    def try_auto_connect_rfid(self):
        result = self.api.scanner.try_auto_connect_rfid()
        result["state"] = self.api.get_state()
        return result

    def get_rfid_connection_info(self):
        return self.api.scanner.get_rfid_connection_info()

    def connect_nfc(self):
        result = self.api.scanner.connect_nfc()
        result["state"] = self.api.get_state()
        return result

    def disconnect_rfid(self):
        result = self.api.scanner.disconnect_rfid()
        result["state"] = self.api.get_state()
        return result

    def disconnect_nfc(self):
        result = self.api.scanner.disconnect_nfc()
        result["state"] = self.api.get_state()
        return result

    def start_nfc_capture(self):
        return self.api.start_nfc_capture()

    def poll_nfc_capture(self):
        return self.api.poll_nfc_capture()

    def cancel_nfc_capture(self):
        return self.api.cancel_nfc_capture()

    # ------------------------------------------------------------------
    # Live workout controls
    # ------------------------------------------------------------------
    def list_athletes(self):
        return self.api.roster.list_athletes()

    def list_athletes_with_status(self):
        return self.api.list_athletes_with_status()

    def start_timer(self):
        return self.api.start_timer()

    def start_selected(self, tag_ids_json: str):
        try:
            tag_ids = _json.loads(tag_ids_json)
            return self.api.start_selected(tag_ids)
        except Exception:
            return {"ok": False, "msg": "Invalid tag IDs format."}

    def get_resting(self):
        return self.api.session.get_resting()

    def finish_workout(self):
        return self.api.finish_workout()

    # ------------------------------------------------------------------
    # Session recovery
    # ------------------------------------------------------------------
    def get_pending_recovery(self):
        return self.api.session.get_pending_recovery()

    def resume_session(self):
        return self.api.resume_session()

    def discard_recovery(self):
        return self.api.session.discard_recovery()

    # ------------------------------------------------------------------
    # Performance reports / history
    # ------------------------------------------------------------------
    def list_completed_sessions(self):
        return self.api.history.list_completed_sessions()

    def get_session_details(self, session_id: str):
        return self.api.history.get_session_details(session_id)

    def delete_completed_session(self, session_id: str):
        return self.api.history.delete_completed_session(session_id)

    def send_reports(self, reports: list):
        return self.api.history.send_reports(reports)

    # ------------------------------------------------------------------
    # Roster athlete management
    # ------------------------------------------------------------------
    def add_athlete_to_roster(self, roster_id: str, data: dict):
        return self.api.roster.add_athlete_to_roster(roster_id, data)

    def update_athlete(self, athlete_id: str, data: dict):
        return self.api.roster.update_athlete(athlete_id, data)

    def update_athlete_email(self, lap_id: str, email: str):
        return self.api.roster.update_athlete_email(lap_id, email)

    # ------------------------------------------------------------------
    # File utilities
    # ------------------------------------------------------------------
    def write_files(self, files: list):
        """Write a list of {path, content} dicts to disk. Used for HTML report export."""
        written = []
        for entry in files:
            path    = entry['path']
            content = entry['content']
            try:
                parent = os.path.dirname(os.path.abspath(path))
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(content)
                written.append(path)
            except Exception as e:
                return {"ok": False, "msg": f"Failed to write {os.path.basename(path)}: {e}"}
        n = len(written)
        return {"ok": True, "msg": f"Exported {n} report{'s' if n != 1 else ''}.", "files": written}

    def pick_directory(self):
        import webview as _wv
        result = _wv.windows[0].create_file_dialog(
            dialog_type=_wv.FileDialog.FOLDER,
            allow_multiple=False,
        )
        if result and len(result) > 0:
            return {"path": result[0]}
        return {"path": None}

    def pick_csv_file(self):
        import webview as _wv
        result = _wv.windows[0].create_file_dialog(
            dialog_type=_wv.FileDialog.OPEN,
            allow_multiple=False,
            file_types=('CSV files (*.csv)', 'All files (*.*)')
        )
        if result and len(result) > 0:
            return {"path": result[0]}
        return {"path": None}

    def download_csv_template(self):
        import webview as _wv
        result = _wv.windows[0].create_file_dialog(
            dialog_type=_wv.FileDialog.SAVE,
            save_filename='athletes_template.csv',
            file_types=('CSV files (*.csv)', 'All files (*.*)')
        )
        if not result:
            return {"ok": False}
        path = result if isinstance(result, str) else result[0]
        content = (
            'First Name,Last Name,NFC TAG,RFID TAG,Email\n'
            'Jane,Smith,AAA111,BBB222,jane@example.com\n'
        )
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"ok": True, "msg": "Template saved."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ------------------------------------------------------------------
    # Gmail OAuth
    # ------------------------------------------------------------------
    def _gmail_auth_mod(self):
        import importlib.util, os, sys
        if "_gmail_auth" in sys.modules:
            return sys.modules["_gmail_auth"]
        path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "email", "gmail_auth.py")
        )
        spec = importlib.util.spec_from_file_location("_gmail_auth", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["_gmail_auth"] = mod
        return mod

    def get_gmail_auth_status(self):
        return self._gmail_auth_mod().get_auth_status()

    def start_gmail_sign_in(self):
        return self._gmail_auth_mod().start_sign_in()

    def poll_gmail_sign_in(self):
        return self._gmail_auth_mod().poll_sign_in()

    def cancel_gmail_sign_in(self):
        return self._gmail_auth_mod().cancel_sign_in()

    def gmail_sign_out(self):
        return self._gmail_auth_mod().sign_out()

    # ------------------------------------------------------------------
    # Theme & secondary window
    # ------------------------------------------------------------------
    def get_theme(self):
        return self._theme

    def set_theme(self, mode: str):
        if mode not in ('light', 'dark'):
            return
        self._theme = mode
        global resting_window
        if resting_window:
            resting_window.evaluate_js(f'applyTheme("{mode}")')

    def show_resting_runners(self):
        global resting_window
        resting_window.show()
        return {"ok": True, "msg": ""}

    def shutdown(self):
        return self.api.shutdown()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

    api = PyWebViewAPI()

    html_path = os.environ.get('GUI_HTML_PATH', os.path.join(os.path.dirname(__file__), "html"))
    ui_path = os.path.join(html_path, "index.html")
    api._html_path = html_path

    main_window = webview.create_window(
        title="Splits",
        url=ui_path,
        js_api=api,
        width=1100,
        height=720,
        min_size=(900, 600),
        background_color=LIGHT_MODE_BG,
    )

    _shutting_down = [False]

    def on_closed():
        api.shutdown()
        _shutting_down[0] = True
        if resting_window:
            resting_window.destroy()

    main_window.events.closed += on_closed

    # Pre-create the resting window hidden before webview.start().
    # On Windows, creating a window after webview.start() causes pywebview to
    # Invoke back onto the UI thread, where the WinForms accessibility probe of
    # Rectangle.Empty triggers infinite recursion that threading.excepthook
    # cannot catch (it runs on the main UI thread, not a background thread).
    # Creating it upfront — like the POC — avoids that code path entirely.
    resting_path = os.path.join(html_path, "resting.html")
    global resting_window
    resting_window = webview.create_window(
        title="Resting Runners",
        url=resting_path,
        js_api=api,
        width=600,
        height=800,
        min_size=(400, 500),
        background_color=LIGHT_MODE_BG,
        x=1120,
        y=0,
        hidden=True,
    )

    def on_closing_resting():
        if _shutting_down[0]:
            return True  # allow destroy during app shutdown
        global resting_window
        resting_window.hide()
        return False

    resting_window.events.closing += on_closing_resting

    webview.start(debug=False)


if __name__ == "__main__":
    main()
