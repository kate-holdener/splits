from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from entity.runner import Runner
from entity.RunnerState import RunnerState


class RunnersScreen(QWidget):
    """
    Secondary window displayed to runners during a workout.

    Shows only resting runners and their countdown until they can start the
    next interval.  Runner add/remove is driven by the Observer pattern
    (via TimerViewGUI.runner_state_changed).  A QTimer ticks every second
    to update the countdown numbers.

    The window hides on close rather than quitting; the coach can reopen it.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resting Runners")
        self.setMinimumSize(500, 400)
        self._countdowns: dict[str, int] = {}  # start_id -> remaining seconds
        self._runners: dict[str, Runner] = {}   # start_id -> Runner

        self._setup_ui()

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(1000)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        title = QLabel("Resting Runners")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._list_layout = QVBoxLayout()
        self._list_layout.setSpacing(8)
        layout.addLayout(self._list_layout)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Observer-driven add / remove
    # ------------------------------------------------------------------

    def on_runner_state_changed(self, runner: Runner):
        """Slot connected to TimerViewGUI.runner_state_changed."""
        if runner.current_status == RunnerState.RESTING:
            rest_time = runner.current_workout.rest_time if runner.current_workout else 60
            self._add_runner(runner, rest_time)
        else:
            self._remove_runner(runner)

    def _add_runner(self, runner: Runner, rest_time: int):
        key = runner.start_id
        if key in self._runners:
            return
        self._runners[key] = runner
        self._countdowns[key] = rest_time
        self._refresh_display()

    def _remove_runner(self, runner: Runner):
        key = runner.start_id
        if key not in self._runners:
            return
        del self._runners[key]
        del self._countdowns[key]
        self._refresh_display()

    # ------------------------------------------------------------------
    # Countdown tick
    # ------------------------------------------------------------------

    def _tick(self):
        for key in list(self._countdowns):
            if self._countdowns[key] > 0:
                self._countdowns[key] -= 1
        self._refresh_display()

    # ------------------------------------------------------------------
    # Display refresh
    # ------------------------------------------------------------------

    def _refresh_display(self):
        # Remove all existing labels
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._runners:
            empty = QLabel("No runners currently resting")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #888; font-size: 14px;")
            self._list_layout.addWidget(empty)
            return

        label_font = QFont()
        label_font.setPointSize(16)

        for key, runner in self._runners.items():
            remaining = self._countdowns.get(key, 0)
            if remaining > 0:
                text = f"{runner.name} {runner.lname}  —  {remaining}s remaining"
                color = "#2c3e50"
            else:
                text = f"{runner.name} {runner.lname}  —  Ready to run!"
                color = "#27ae60"

            lbl = QLabel(text)
            lbl.setFont(label_font)
            lbl.setStyleSheet(f"color: {color}; padding: 8px; background: #f8f9fa; border-radius: 4px;")
            lbl.setAlignment(Qt.AlignCenter)
            self._list_layout.addWidget(lbl)

    # ------------------------------------------------------------------
    # Close behaviour: hide instead of destroying
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        event.ignore()
        self.hide()
