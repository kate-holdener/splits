from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
                               QMessageBox)
from PySide6.QtCore import Qt

from entity.workout import Workout
from datetime import datetime, timezone

class WorkoutConfigDialog(QDialog):
    def __init__(self, parent=None):
        """
        Initialize the workout configuration dialog.
        User selects interval distance and number of laps before starting workout.
        """
        super().__init__(parent)
        self.interval_distance = None
        self.num_laps = None
        self.workout = None
        
        self.setWindowTitle("Workout Configuration")
        self.setGeometry(200, 200, 400, 250)
        self.setModal(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        
        # Title label
        title_label = QLabel("Configure Workout Parameters")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Interval Distance section
        distance_layout = QHBoxLayout()
        distance_label = QLabel("Interval Distance (meters):")
        distance_label.setStyleSheet("font-size: 12px;")
        distance_layout.addWidget(distance_label)
        
        self.distance_spinbox = QDoubleSpinBox()
        self.distance_spinbox.setMinimum(50.0)
        self.distance_spinbox.setMaximum(10000.0)
        self.distance_spinbox.setValue(400.0)
        self.distance_spinbox.setSingleStep(50.0)
        self.distance_spinbox.setDecimals(1)
        self.distance_spinbox.setSuffix(" m")
        self.distance_spinbox.setStyleSheet("font-size: 12px; padding: 5px;")
        distance_layout.addWidget(self.distance_spinbox)
        
        main_layout.addLayout(distance_layout)
        
        # Number of Laps section
        laps_layout = QHBoxLayout()
        laps_label = QLabel("Number of Laps:")
        laps_label.setStyleSheet("font-size: 12px;")
        laps_layout.addWidget(laps_label)
        
        self.laps_spinbox = QSpinBox()
        self.laps_spinbox.setMinimum(1)
        self.laps_spinbox.setMaximum(100)
        self.laps_spinbox.setValue(4)
        self.laps_spinbox.setSingleStep(1)
        self.laps_spinbox.setStyleSheet("font-size: 12px; padding: 5px;")
        laps_layout.addWidget(self.laps_spinbox)
        
        main_layout.addLayout(laps_layout)
        
        # Summary label
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 11px; color: #666; font-style: italic;")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.update_summary()
        main_layout.addWidget(self.summary_label)
        
        # Connect signals to update summary
        self.distance_spinbox.valueChanged.connect(self.update_summary)
        self.laps_spinbox.valueChanged.connect(self.update_summary)
        
        # Add spacer
        main_layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        confirm_button = QPushButton("Confirm")
        confirm_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        confirm_button.clicked.connect(self.confirm_settings)
        button_layout.addWidget(confirm_button)
        
        main_layout.addLayout(button_layout)
        
    def update_summary(self):
        """Update the summary label with current configuration."""
        distance = self.distance_spinbox.value()
        laps = self.laps_spinbox.value()
        total_distance = distance * laps
        
        self.summary_label.setText(
            f"{distance:.1f} meter intervals ({laps} laps each)"
        )
        
    def confirm_settings(self):
        """Confirm the settings and close dialog."""
        self.interval_distance = self.distance_spinbox.value()
        self.num_laps = self.laps_spinbox.value()
        self.workout = Workout(int(datetime.now(timezone.utc).timestamp()))
        self.workout.interval_distance = self.interval_distance
        self.workout.laps_per_interval = self.num_laps
        self.accept()
    
    def get_configuration(self):
        """
        Return the configured workout parameters.
        
        Returns:
            tuple: (interval_distance, num_laps) or (None, None) if cancelled
        """
        return self.workout