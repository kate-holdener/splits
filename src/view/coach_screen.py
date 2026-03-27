"""
CoachScreen — main workout management window.

Closing this window asks for confirmation, then stops the IntervalTimer
and all readers before quitting the application.
"""

from queue import Queue

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from entity.runner import Runner
from entity.RunnerState import RunnerState
from entity.workout import Workout
from interactors.interval_timer import IntervalTimer
from interactors.stats_calculator import calculate_performance
from controller.start_controller import ManualStartController
from parser.runner_parser import parse_runner_data
from report.pdf_report_runner import generate_runner_report
from view.timer_view_gui import TimerViewGUI
from view.runners_screen import RunnersScreen


_STATUS_COLORS = {
    RunnerState.INACTIVE:  ("#ecf0f1", "#2c3e50"),   # bg, fg
    RunnerState.RUNNING:   ("#d5f5e3", "#1e8449"),
    RunnerState.RESTING:   ("#fef9e7", "#b7950b"),
    RunnerState.FINISHED:  ("#eaecee", "#5d6d7e"),
}

_STATUS_LABELS = {
    RunnerState.INACTIVE:  "Inactive",
    RunnerState.RUNNING:   "Running",
    RunnerState.RESTING:   "Resting",
    RunnerState.FINISHED:  "Finished",
}


class CoachScreen(QMainWindow):
    """
    Main window for the coach.  Stays open for the duration of the workout;
    closing it (with confirmation) terminates the application.
    """

    def __init__(
        self,
        workout: Workout,
        start_event_q: Queue,
        lap_event_q: Queue,
        manual_start_controller: ManualStartController,
        nfc_reader,
        rfid_reader,
        timer_view: TimerViewGUI,
        runners_screen: RunnersScreen,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Coach — Interval Training")
        self.setMinimumSize(900, 600)

        self._workout = workout
        self._start_q = start_event_q
        self._lap_q = lap_event_q
        self._manual_start = manual_start_controller
        self._nfc_reader = nfc_reader
        self._rfid_reader = rfid_reader
        self._timer_view = timer_view
        self._runners_screen = runners_screen

        self._runners: list[Runner] = []
        self._interval_timer: IntervalTimer | None = None
        self._group_start: set[str] = set()  # start_ids

        # Connect observer signal to our update slot
        self._timer_view.runner_state_changed.connect(self._on_runner_state_changed)

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(16)
        root.setContentsMargins(16, 16, 16, 16)

        root.addLayout(self._build_runner_table(), stretch=3)
        root.addLayout(self._build_controls(), stretch=2)

    def _build_runner_table(self):
        layout = QVBoxLayout()

        title = QLabel("Athletes")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Name", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        return layout

    def _build_controls(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        layout.addWidget(self._section_label("Setup"))

        load_btn = QPushButton("Load Athletes from CSV…")
        load_btn.setStyleSheet(self._btn_style("#3498db"))
        load_btn.clicked.connect(self._load_athletes)
        layout.addWidget(load_btn)

        layout.addWidget(self._section_label("Group Start"))

        self._group_list = QListWidget()
        self._group_list.setMaximumHeight(120)
        layout.addWidget(self._group_list)

        add_group_btn = QPushButton("Add Selected to Group Start")
        add_group_btn.setStyleSheet(self._btn_style("#8e44ad"))
        add_group_btn.clicked.connect(self._add_to_group_start)
        layout.addWidget(add_group_btn)

        start_btn = QPushButton("▶  Start Group")
        start_btn.setStyleSheet(self._btn_style("#27ae60"))
        start_btn.clicked.connect(self._start_group)
        layout.addWidget(start_btn)

        layout.addWidget(self._section_label("Workout"))

        perf_btn = QPushButton("View Performance")
        perf_btn.setStyleSheet(self._btn_style("#2980b9"))
        perf_btn.clicked.connect(self._show_performance)
        layout.addWidget(perf_btn)

        finish_btn = QPushButton("Finish Workout")
        finish_btn.setStyleSheet(self._btn_style("#e67e22"))
        finish_btn.clicked.connect(self._finish_workout)
        layout.addWidget(finish_btn)

        layout.addWidget(self._section_label("Reports"))

        reports_btn = QPushButton("Generate Reports…")
        reports_btn.setStyleSheet(self._btn_style("#16a085"))
        reports_btn.clicked.connect(self._generate_reports)
        layout.addWidget(reports_btn)

        layout.addStretch()

        reopen_btn = QPushButton("Open Runners Screen")
        reopen_btn.setStyleSheet(self._btn_style("#7f8c8d"))
        reopen_btn.clicked.connect(self._runners_screen.show)
        layout.addWidget(reopen_btn)

        return layout

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; color: #555; border-top: 1px solid #ddd; padding-top: 6px;")
        return lbl

    @staticmethod
    def _btn_style(color: str) -> str:
        return (
            f"QPushButton {{background:{color};color:white;font-weight:bold;"
            f"padding:8px;border-radius:4px;}}"
            f"QPushButton:hover {{opacity:0.9;}}"
            f"QPushButton:disabled {{background:#bdc3c7;}}"
        )

    # ------------------------------------------------------------------
    # Runner table helpers
    # ------------------------------------------------------------------

    def _populate_table(self):
        self._table.setRowCount(0)
        for runner in self._runners:
            self._insert_row(runner)

    def _insert_row(self, runner: Runner):
        row = self._table.rowCount()
        self._table.insertRow(row)

        name_item = QTableWidgetItem(f"{runner.name} {runner.lname}")
        name_item.setData(Qt.UserRole, runner.start_id)
        self._table.setItem(row, 0, name_item)

        status_item = QTableWidgetItem(_STATUS_LABELS[runner.current_status])
        self._color_status_item(status_item, runner.current_status)
        self._table.setItem(row, 1, status_item)

    def _color_status_item(self, item: QTableWidgetItem, state: RunnerState):
        bg, fg = _STATUS_COLORS.get(state, ("#fff", "#000"))
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))

    def _find_row(self, start_id: str) -> int:
        for row in range(self._table.rowCount()):
            if self._table.item(row, 0).data(Qt.UserRole) == start_id:
                return row
        return -1

    # ------------------------------------------------------------------
    # Observer slot
    # ------------------------------------------------------------------

    def _on_runner_state_changed(self, runner: Runner):
        row = self._find_row(runner.start_id)
        if row == -1:
            return
        item = self._table.item(row, 1)
        item.setText(_STATUS_LABELS[runner.current_status])
        self._color_status_item(item, runner.current_status)

    # ------------------------------------------------------------------
    # Control actions
    # ------------------------------------------------------------------

    def _load_athletes(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Athletes CSV", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            runners = parse_runner_data(path)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            return

        for runner in runners:
            runner.add_workout(self._workout)
            runner.add_observer(self._timer_view)

        self._runners = runners

        # Create / recreate IntervalTimer now that we have runners
        if self._interval_timer:
            self._interval_timer.stop()
        self._interval_timer = IntervalTimer(self._start_q, self._lap_q, self._runners)
        self._interval_timer.start()

        self._populate_table()

    def _add_to_group_start(self):
        selected = self._table.selectedItems()
        if not selected:
            QMessageBox.information(self, "No Selection", "Select one or more athletes from the table first.")
            return

        rows = set(item.row() for item in selected)
        for row in rows:
            start_id = self._table.item(row, 0).data(Qt.UserRole)
            if start_id not in self._group_start:
                runner = next((r for r in self._runners if r.start_id == start_id), None)
                if runner:
                    self._group_start.add(start_id)
                    name = f"{runner.name} {runner.lname}"
                    item = QListWidgetItem(name)
                    item.setData(Qt.UserRole, start_id)
                    self._group_list.addItem(item)

    def _start_group(self):
        if not self._group_start:
            QMessageBox.information(self, "Empty Group", "Add athletes to the group start list first.")
            return
        ids = list(self._group_start)
        self._manual_start.start(ids)
        self._group_start.clear()
        self._group_list.clear()

    def _show_performance(self):
        if not self._runners:
            QMessageBox.information(self, "No Athletes", "Load athletes first.")
            return
        lines = []
        for runner in self._runners:
            perf = calculate_performance(runner)
            completed = len(perf.interval_durations)
            avg = perf.average_pace
            lines.append(
                f"{runner.name} {runner.lname}: "
                f"{completed} interval(s), avg pace {avg} s/mile"
            )
        QMessageBox.information(self, "Performance", "\n".join(lines) if lines else "No data yet.")

    def _finish_workout(self):
        reply = QMessageBox.question(
            self, "Finish Workout",
            "Are you sure you want to finish the workout?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._group_start.clear()
            self._group_list.clear()

    def _generate_reports(self):
        if not self._runners:
            QMessageBox.information(self, "No Athletes", "Load athletes first.")
            return
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not directory:
            return
        errors = []
        for runner in self._runners:
            try:
                filename = f"{directory}/runner_{runner.start_id}.pdf"
                generate_runner_report(runner, filename)
            except Exception as e:
                errors.append(f"{runner.name}: {e}")
        if errors:
            QMessageBox.warning(self, "Some Reports Failed", "\n".join(errors))
        else:
            QMessageBox.information(self, "Reports Generated", f"Reports saved to:\n{directory}")

    # ------------------------------------------------------------------
    # Close — confirm, then stop everything and quit
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Close Application",
            "Are you sure you want to close? This will end the session.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.No:
            event.ignore()
            return

        if self._interval_timer:
            self._interval_timer.stop()
        if self._nfc_reader:
            try:
                self._nfc_reader.stop()
            except Exception:
                pass
        if self._rfid_reader:
            try:
                self._rfid_reader.stop()
            except Exception:
                pass

        self._runners_screen.close()
        event.accept()
