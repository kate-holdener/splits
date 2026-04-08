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

# Default (light-mode) background color — must match --bg in shared.css
LIGHT_MODE_BG = "#f0f0f0"


class PyWebViewAPI:
    def __init__(self):
        self.track_api = IntervalTrackApi()
        self._theme = 'light'
    def log(self, data):
        print(data)

    def get_state(self):
        return self.track_api.get_state()
    
    def load_athletes(self, csv_path: str):
        return self.track_api.load_athletes(csv_path)
    
    def configure_workout(self, distance: str, laps: str, rest_time: str):
        dist_int = int(distance)
        laps_int = int(laps)
        rest_int = int(rest_time)
        return self.track_api.configure_workout(dist_int, laps_int, rest_int)

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

    def get_theme(self):
        return self._theme

    def set_theme(self, mode: str):
        if mode not in ('light', 'dark'):
            return
        self._theme = mode
        if hasattr(self, 'resting_window') and self.resting_window:
            self.resting_window.evaluate_js(f'applyTheme("{mode}")')
    
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
        background_color=LIGHT_MODE_BG,
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
        background_color=LIGHT_MODE_BG,
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
