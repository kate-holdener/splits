from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QMessageBox,
                               QDialog, QSpinBox, QDoubleSpinBox)
from PySide6.QtCore import Qt

from view.workout_config_gui import WorkoutConfigDialog
from view.runner_workout_gui import RunnerWorkoutGUI

class MainMenuGUI(QMainWindow):
    def __init__(self, runners, controllers):
        """
        Initialize the main menu GUI.
        Provides options to create new workout or generate reports.
        """
        super().__init__()
        self.runners = runners
        self.controllers = controllers
        self.runner_workout_gui = None
        self.setWindowTitle("Runner Workout Manager - Main Menu")
        self.setGeometry(150, 150, 500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title_label = QLabel("Runner Workout Manager")
        title_label.setStyleSheet("font-weight: bold; font-size: 24px; color: #2c3e50;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Manage your training sessions and track progress")
        subtitle_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)
        
        # Add some spacing
        main_layout.addSpacing(30)
        
        # Create New Workout button
        new_workout_button = QPushButton("Create New Workout")
        new_workout_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        new_workout_button.clicked.connect(self.create_new_workout)
        main_layout.addWidget(new_workout_button)
        
        # Generate Reports button
        reports_button = QPushButton("Generate Workout Reports")
        reports_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #0a6dbd;
            }
        """)
        reports_button.clicked.connect(self.generate_reports)
        main_layout.addWidget(reports_button)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
        
        # Exit button at the bottom
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c41408;
            }
        """)
        exit_button.clicked.connect(self.close)
        main_layout.addWidget(exit_button)
        
    def create_new_workout(self):
        """Handle create new workout button click."""
        print("Creating new workout...")
        
        # Show configuration dialog
        config_dialog = WorkoutConfigDialog(self)
        result = config_dialog.exec()
        
        if result == QDialog.Accepted:
            workout = config_dialog.get_configuration()            
            # Here you would proceed to open the RunnerWorkoutGUI
            self.runner_workout_gui = RunnerWorkoutGUI(workout, self.runners, self.controllers)  # Pass actual runners and controllers
            self.runner_workout_gui.show()
            self.hide()  # Hide main menu while workout is active
        else:
            print("Workout creation cancelled")
    
    def generate_reports(self):
        """Handle generate reports button click."""
        print("Generating workout reports...")
        
        # Show info message (placeholder for actual report generation)
        QMessageBox.information(
            self,
            'Generate Reports',
            'Report generation feature will display:\n\n'
            '• Workout history\n'
            '• Runner performance statistics\n'
            '• Progress tracking\n'
            '• Completion rates\n\n'
            'This feature is ready to be implemented.',
            QMessageBox.Ok
        )
        
        # TODO: Open report generation window/dialog here
        # self.report_window = ReportGeneratorGUI()
        # self.report_window.show()



# Example usage
if __name__ == '__main__':
    import sys
    
    app = QApplication(sys.argv)
    
    # Show main menu
    main_menu = MainMenuGUI()
    main_menu.show()
    
    sys.exit(app.exec())