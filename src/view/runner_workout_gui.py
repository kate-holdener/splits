from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QListWidget, QPushButton, QLabel,
                               QListWidgetItem, QMessageBox)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from view.timer_view_gui import TimerViewGUI
class RunnerWorkoutGUI(QWidget):
    def __init__(self, workout, runners, controllers):
        """
        Initialize the GUI with a list of runners and a controller.
        
        Args:
            runners: List of runner dictionaries with 'id' and 'name' keys
            controller: Controller object with a start_workout method
        """
        super().__init__()
        self.workout = workout
        self.runners = runners
        self.controllers= controllers
        self.workout_runners = set()  # Store IDs of runners in workout
        self.started_runners = set()  # Store IDs of runners that started
        self.selected_runners = set()  # Store IDs of selected runners for adding
        self.timer = TimerViewGUI()
        self.setWindowTitle("Runner Workout Manager")
        self.setGeometry(100, 100, 800, 400)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Central widget and main layout
        # central_widget = QWidget()
        # self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        
        # Left panel - All Runners
        left_panel = QVBoxLayout()
        left_label = QLabel("All Runners")
        left_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_panel.addWidget(left_label)
        
        self.runners_list = QListWidget()
        self.runners_list.setSelectionMode(QListWidget.NoSelection)
        self.runners_list.itemClicked.connect(self.toggle_runner_selection)
        self.populate_runners_list()
        left_panel.addWidget(self.runners_list)
        
        add_button = QPushButton("Add Selected to Workout →")
        add_button.clicked.connect(self.add_to_workout)
        left_panel.addWidget(add_button)
        
        # Right panel - Workout
        right_panel = QVBoxLayout()
        right_label = QLabel("Workout Runners")
        right_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_panel.addWidget(right_label)
        
        self.workout_list = QListWidget()
        self.workout_list.setSelectionMode(QListWidget.NoSelection)
        self.workout_list.itemClicked.connect(self.toggle_workout_selection)
        right_panel.addWidget(self.workout_list)
        
        remove_button = QPushButton("← Remove Selected from Workout")
        remove_button.clicked.connect(self.remove_from_workout)
        right_panel.addWidget(remove_button)
        
        self.start_button = QPushButton("Start Workout")
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.start_button.clicked.connect(self.start_workout)
        right_panel.addWidget(self.start_button)
        
        # Third panel - Started Runners
        started_panel = QVBoxLayout()
        started_label = QLabel("Started Runners")
        started_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        started_panel.addWidget(started_label)
        
        self.started_list = QListWidget()
        self.started_list.setSelectionMode(QListWidget.NoSelection)
        self.started_list.itemClicked.connect(self.toggle_started_selection)
        started_panel.addWidget(self.started_list)
        
        move_back_button = QPushButton("← Move Back to Workout")
        move_back_button.clicked.connect(self.move_back_to_workout)
        started_panel.addWidget(move_back_button)
        
        self.finish_button = QPushButton("Finish Workout")
        self.finish_button.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; padding: 10px;")
        self.finish_button.clicked.connect(self.finish_workout)
        started_panel.addWidget(self.finish_button)
        
        # Add panels to main layout
        main_layout.addLayout(left_panel)
        main_layout.addLayout(right_panel)
        main_layout.addLayout(started_panel)
        self.setLayout(main_layout)
        
        # Update button states initially
        self.update_button_states()
        
    def populate_runners_list(self):
        """Populate the runners list with all available runners."""
        self.runners_list.clear()
        for runner in self.runners:
            if runner.start_id not in self.workout_runners and runner.start_id not in self.started_runners:
                item = QListWidgetItem(runner.name)
                item.setData(Qt.UserRole, runner.start_id)
                self.runners_list.addItem(item)
    
    def populate_workout_list(self):
        """Populate the workout list with selected runners."""
        self.workout_list.clear()
        for runner in self.runners:
            if runner.start_id in self.workout_runners and runner.start_id not in self.started_runners:
                item = QListWidgetItem(runner.name)
                item.setData(Qt.UserRole, runner.start_id)
                self.workout_list.addItem(item)
                runner.add_workout(self.workout)
                runner.add_observer(self.timer)
    
    def populate_started_list(self):
        """Populate the started list with runners that have started."""
        self.started_list.clear()
        for runner in self.runners:
            if runner.start_id in self.started_runners:
                item = QListWidgetItem(runner.name)
                item.setData(Qt.UserRole, runner.start_id)
                self.started_list.addItem(item)
    
    def update_button_states(self):
        """Enable or disable buttons based on list contents."""
        self.start_button.setEnabled(len(self.workout_runners) > 0)
        self.finish_button.setEnabled(len(self.started_runners) > 0)
    
    def toggle_runner_selection(self, item):
        """Toggle selection state of a runner in the available runners list."""
        runner_id = item.data(Qt.UserRole)
        
        if runner_id in self.selected_runners:
            # Unselect
            self.selected_runners.remove(runner_id)
            item.setBackground(QColor(255, 255, 255))  # White background
        else:
            # Select
            self.selected_runners.add(runner_id)
            item.setBackground(QColor(173, 216, 230))  # Light blue background
    
    def toggle_workout_selection(self, item):
        """Toggle selection state of a runner in the workout list."""
        runner_id = item.data(Qt.UserRole)
        
        if runner_id in self.selected_runners:
            # Unselect
            self.selected_runners.remove(runner_id)
            item.setBackground(QColor(255, 255, 255))  # White background
        else:
            # Select
            self.selected_runners.add(runner_id)
            item.setBackground(QColor(173, 216, 230))  # Light blue background
    
    def toggle_started_selection(self, item):
        """Toggle selection state of a runner in the started list."""
        runner_id = item.data(Qt.UserRole)
        
        if runner_id in self.selected_runners:
            # Unselect
            self.selected_runners.remove(runner_id)
            item.setBackground(QColor(255, 255, 255))  # White background
        else:
            # Select
            self.selected_runners.add(runner_id)
            item.setBackground(QColor(173, 216, 230))  # Light blue background
    
    def add_to_workout(self):
        """Add selected runners to the workout."""
        if not self.selected_runners:
            return
        
        # Add all selected runners to workout
        for runner_id in list(self.selected_runners):
            if runner_id not in self.workout_runners:
                self.workout_runners.add(runner_id)
        
        # Clear selection
        self.selected_runners.clear()
        
        # Refresh both lists
        self.populate_runners_list()
        self.populate_workout_list()
        self.update_button_states()
    
    def remove_from_workout(self):
        """Remove selected runners from the workout."""
        if not self.selected_runners:
            return
        
        # Remove all selected runners from workout
        for runner_id in list(self.selected_runners):
            self.workout_runners.discard(runner_id)
        
        # Clear selection
        self.selected_runners.clear()
        
        # Refresh both lists
        self.populate_runners_list()
        self.populate_workout_list()
        self.update_button_states()
    
    def move_back_to_workout(self):
        """Move selected runners from started back to workout."""
        if not self.selected_runners:
            return
        
        # Move all selected runners from started to workout
        for runner_id in list(self.selected_runners):
            if runner_id in self.started_runners:
                self.started_runners.remove(runner_id)
                self.workout_runners.add(runner_id)
        
        # Clear selection
        self.selected_runners.clear()
        
        # Refresh all lists
        self.populate_runners_list()
        self.populate_workout_list()
        self.populate_started_list()
        self.update_button_states()
    
    def start_workout(self):
        """Start the workout with all selected runners."""
        if not self.workout_runners:
            print("No runners selected for workout")
            return
        
        runner_ids = list(self.workout_runners)
        print(f"Starting workout with runner IDs: {runner_ids}")
        
        # Move runners from workout to started
        for runner_id in runner_ids:
            self.started_runners.add(runner_id)
            self.workout_runners.discard(runner_id)
    
        
        # Refresh all lists
        self.populate_runners_list()
        self.populate_workout_list()
        self.populate_started_list()
        self.update_button_states()
        # Pass the runner IDs to the controller
        for controller in self.controllers:
            controller.start(runner_ids)
    
    def finish_workout(self):
        """Finish the workout and print runner IDs from started list."""
        if not self.started_runners:
            print("No runners have started the workout")
            return
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            'Confirm Finish Workout',
            f'Are you sure you want to finish the workout for {len(self.started_runners)} runner(s)?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            runner_ids = list(self.started_runners)
            print(f"Finishing workout with runner IDs: {runner_ids}")
            
            # Move runners from started back to all runners
            self.started_runners.clear()
            
            # Refresh all lists
            self.populate_runners_list()
            self.populate_workout_list()
            self.populate_started_list()
            self.update_button_states()
