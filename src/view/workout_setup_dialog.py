"""
WorkoutSetupDialog
==================
Two-page setup wizard:
  Page 0 — Configure workout parameters (distance, laps, rest time)
  Page 1 — Auto-connect RFID and NFC scanners; retry on failure
"""

import threading
from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QDialog, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QLineEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QTimer, Slot
from PySide6.QtGui import QFont

from entity.workout import Workout
from controller.start_controller import ManualStartController
from queue import Queue

DEFAULT_SCANNER_ADDRESS = "169.254.1.1"


class WorkoutSetupDialog(QDialog):
    """
    Exposes on accept:
        workout               — configured Workout object
        start_event_q         — Queue for NFC start events
        lap_event_q           — Queue for RFID lap events
        manual_start_controller
        nfc_reader
        rfid_reader
    IntervalTimer is NOT created here; CoachScreen creates it after loading
    athletes (matching the cli/cli.py flow).
    """

    # Signals used to safely marshal connection results to the main thread.
    # Called from background threads → Qt queues delivery to main thread.
    _rfid_result = Signal(bool, str)
    _nfc_result = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workout Setup")
        self.setMinimumWidth(480)
        self.setModal(True)

        # Outputs
        self.workout: Workout | None = None
        self.start_event_q = Queue()
        self.lap_event_q = Queue()
        self.manual_start_controller = ManualStartController(self.start_event_q)
        self.nfc_reader = None
        self.rfid_reader = None

        self._rfid_connected = False
        self._nfc_connected = False

        # Wire cross-thread signals to main-thread slots
        self._rfid_result.connect(self._set_rfid_connected)
        self._nfc_result.connect(self._set_nfc_connected)

        self._stack = QStackedWidget()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._stack)

        self._stack.addWidget(self._build_config_page())
        self._stack.addWidget(self._build_scanner_page())

    # ------------------------------------------------------------------
    # Page 0 — Configure
    # ------------------------------------------------------------------

    def _build_config_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Configure Workout")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Distance
        dist_row = QHBoxLayout()
        dist_row.addWidget(QLabel("Interval distance (meters):"))
        self._distance_spin = QDoubleSpinBox()
        self._distance_spin.setRange(50, 10000)
        self._distance_spin.setValue(400)
        self._distance_spin.setSingleStep(50)
        self._distance_spin.setSuffix(" m")
        dist_row.addWidget(self._distance_spin)
        layout.addLayout(dist_row)

        # Laps
        laps_row = QHBoxLayout()
        laps_row.addWidget(QLabel("Laps per interval:"))
        self._laps_spin = QSpinBox()
        self._laps_spin.setRange(1, 100)
        self._laps_spin.setValue(1)
        laps_row.addWidget(self._laps_spin)
        layout.addLayout(laps_row)

        # Rest time
        rest_row = QHBoxLayout()
        rest_row.addWidget(QLabel("Rest time (seconds):"))
        self._rest_spin = QSpinBox()
        self._rest_spin.setRange(0, 3600)
        self._rest_spin.setValue(60)
        self._rest_spin.setSuffix(" s")
        rest_row.addWidget(self._rest_spin)
        layout.addLayout(rest_row)

        layout.addStretch()

        next_btn = QPushButton("Next →")
        next_btn.setStyleSheet("background:#4CAF50;color:white;font-weight:bold;padding:10px;")
        next_btn.clicked.connect(self._go_to_scanner_page)
        layout.addWidget(next_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background:#f44336;color:white;padding:8px;")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        return page

    def _go_to_scanner_page(self):
        self.workout = Workout(int(datetime.now(timezone.utc).timestamp()))
        self.workout.configure(
            int(self._distance_spin.value()),
            self._laps_spin.value(),
            self._rest_spin.value(),
        )
        self._stack.setCurrentIndex(1)
        QTimer.singleShot(100, self._attempt_connections)

    # ------------------------------------------------------------------
    # Page 1 — Connect scanners
    # ------------------------------------------------------------------

    def _build_scanner_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Connect Scanners")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # RFID row
        rfid_group = QVBoxLayout()
        rfid_header = QHBoxLayout()
        rfid_header.addWidget(QLabel("RFID Scanner"))
        self._rfid_status = QLabel("Connecting…")
        self._rfid_status.setStyleSheet("color: #888;")
        rfid_header.addStretch()
        rfid_header.addWidget(self._rfid_status)
        rfid_group.addLayout(rfid_header)

        rfid_retry_row = QHBoxLayout()
        rfid_retry_row.addWidget(QLabel("IP Address:"))
        self._rfid_ip_edit = QLineEdit(DEFAULT_SCANNER_ADDRESS)
        rfid_retry_row.addWidget(self._rfid_ip_edit)
        self._rfid_retry_btn = QPushButton("Retry")
        self._rfid_retry_btn.clicked.connect(self._retry_rfid)
        self._rfid_retry_btn.setVisible(False)
        rfid_retry_row.addWidget(self._rfid_retry_btn)
        rfid_group.addLayout(rfid_retry_row)
        layout.addLayout(rfid_group)

        # NFC row
        nfc_group = QVBoxLayout()
        nfc_header = QHBoxLayout()
        nfc_header.addWidget(QLabel("NFC Scanner"))
        self._nfc_status = QLabel("Connecting…")
        self._nfc_status.setStyleSheet("color: #888;")
        nfc_header.addStretch()
        nfc_header.addWidget(self._nfc_status)
        nfc_group.addLayout(nfc_header)

        self._nfc_retry_btn = QPushButton("Retry")
        self._nfc_retry_btn.clicked.connect(self._retry_nfc)
        self._nfc_retry_btn.setVisible(False)
        nfc_group.addWidget(self._nfc_retry_btn)
        layout.addLayout(nfc_group)

        layout.addStretch()

        self._start_btn = QPushButton("Start Workout")
        self._start_btn.setStyleSheet("background:#4CAF50;color:white;font-weight:bold;padding:12px;")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self.accept)
        layout.addWidget(self._start_btn)

        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("padding:8px;")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        layout.addWidget(back_btn)

        return page

    # ------------------------------------------------------------------
    # Scanner connection logic
    # ------------------------------------------------------------------

    def _attempt_connections(self):
        self._connect_rfid(self._rfid_ip_edit.text().strip())
        self._connect_nfc()

    def _connect_rfid(self, address: str):
        self._rfid_status.setText("Connecting…")
        self._rfid_status.setStyleSheet("color: #888;")
        self._rfid_retry_btn.setVisible(False)

        def task():
            try:
                from readers.sllurp_reader import LLRPReader
                reader = LLRPReader(self.lap_event_q, address)
                reader.start()
                self.rfid_reader = reader
                self._rfid_result.emit(True, "")
            except Exception as e:
                self._rfid_result.emit(False, str(e))

        threading.Thread(target=task, daemon=True).start()

    def _connect_nfc(self):
        self._nfc_status.setText("Connecting…")
        self._nfc_status.setStyleSheet("color: #888;")
        self._nfc_retry_btn.setVisible(False)

        def task():
            try:
                from readers.acr122u_nfc import NFCReader
                reader = NFCReader(self.start_event_q)
                reader.start()
                self.nfc_reader = reader
                self._nfc_result.emit(True, "")
            except Exception as e:
                self._nfc_result.emit(False, str(e))

        threading.Thread(target=task, daemon=True).start()

    # These slots run on the main thread (delivered via Qt's signal/slot queued connection).
    @Slot(bool, str)
    def _set_rfid_connected(self, ok: bool, msg: str = ""):
        self._rfid_connected = ok
        if ok:
            self._rfid_status.setText("✓ Connected")
            self._rfid_status.setStyleSheet("color: #27ae60; font-weight: bold;")
            self._rfid_retry_btn.setVisible(False)
        else:
            self._rfid_status.setText(f"✗ Failed: {msg}")
            self._rfid_status.setStyleSheet("color: #e74c3c;")
            self._rfid_retry_btn.setVisible(True)
        self._update_start_button()

    @Slot(bool, str)
    def _set_nfc_connected(self, ok: bool, msg: str = ""):
        self._nfc_connected = ok
        if ok:
            self._nfc_status.setText("✓ Connected")
            self._nfc_status.setStyleSheet("color: #27ae60; font-weight: bold;")
            self._nfc_retry_btn.setVisible(False)
        else:
            self._nfc_status.setText(f"✗ Failed: {msg}")
            self._nfc_status.setStyleSheet("color: #e74c3c;")
            self._nfc_retry_btn.setVisible(True)
        self._update_start_button()

    def _retry_rfid(self):
        address = self._rfid_ip_edit.text().strip() or DEFAULT_SCANNER_ADDRESS
        self._connect_rfid(address)

    def _retry_nfc(self):
        self._connect_nfc()

    def _update_start_button(self):
        self._start_btn.setEnabled(self._rfid_connected and self._nfc_connected)
