from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QDialog, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt

from report.pdf_report_runner import generate_runner_report
from parser.runner_parser import parse_runner_data
from view.workout_setup_dialog import WorkoutSetupDialog
from view.timer_view_gui import TimerViewGUI
from view.runners_screen import RunnersScreen
from view.coach_screen import CoachScreen


class LandingScreen(QMainWindow):
    """
    First window the user sees.  Offers two paths:
      - Workout  → WorkoutSetupDialog → CoachScreen + RunnersScreen
      - Reports  → directory picker → generate PDFs
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Interval Training")
        self.setMinimumSize(420, 320)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        title = QLabel("Interval Training")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Select an option to continue")
        subtitle.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        workout_btn = QPushButton("Workout")
        workout_btn.setStyleSheet(
            "QPushButton {background:#27ae60;color:white;font-size:18px;"
            "font-weight:bold;padding:20px;border-radius:6px;}"
            "QPushButton:hover {background:#219a52;}"
        )
        workout_btn.clicked.connect(self._start_workout)
        layout.addWidget(workout_btn)

        reports_btn = QPushButton("Reports")
        reports_btn.setStyleSheet(
            "QPushButton {background:#2980b9;color:white;font-size:18px;"
            "font-weight:bold;padding:20px;border-radius:6px;}"
            "QPushButton:hover {background:#2471a3;}"
        )
        reports_btn.clicked.connect(self._generate_reports)
        layout.addWidget(reports_btn)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Workout flow
    # ------------------------------------------------------------------

    def _start_workout(self):
        dialog = WorkoutSetupDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        self._timer_view = TimerViewGUI()
        self._runners_screen = RunnersScreen()

        # Wire observer signal to runners screen
        self._timer_view.runner_state_changed.connect(self._runners_screen.on_runner_state_changed)

        self._coach = CoachScreen(
            workout=dialog.workout,
            start_event_q=dialog.start_event_q,
            lap_event_q=dialog.lap_event_q,
            manual_start_controller=dialog.manual_start_controller,
            nfc_reader=dialog.nfc_reader,
            rfid_reader=dialog.rfid_reader,
            timer_view=self._timer_view,
            runners_screen=self._runners_screen,
        )

        self._runners_screen.show()
        self._coach.show()
        self.hide()

    # ------------------------------------------------------------------
    # Reports flow
    # ------------------------------------------------------------------

    def _generate_reports(self):
        csv_path, _ = QFileDialog.getOpenFileName(
            self, "Open Athletes CSV", "", "CSV files (*.csv)"
        )
        if not csv_path:
            return
        try:
            runners = parse_runner_data(csv_path)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not out_dir:
            return

        errors = []
        for runner in runners:
            try:
                generate_runner_report(runner, f"{out_dir}/runner_{runner.start_id}.pdf")
            except Exception as e:
                errors.append(f"{runner.name}: {e}")

        if errors:
            QMessageBox.warning(self, "Some Reports Failed", "\n".join(errors))
        else:
            QMessageBox.information(
                self, "Done", f"Reports saved to:\n{out_dir}"
            )
