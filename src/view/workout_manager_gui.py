from PySide6.QtWidgets import (QApplication)

import sys
from view.runner_workout_gui import RunnerWorkoutGUI
from entity.workout import Workout
from datetime import datetime as timedatetime
class WorkoutManagerGUI:
    def __init__(self, runners, controllers):
        self.qapplication = QApplication(sys.argv)
        workout = Workout(timedatetime.now())
        workout.laps_per_interval = 1
        workout.interval_distance = 400
        self.window = RunnerWorkoutGUI(workout, runners, controllers)
        self.window.show()
    def run(self):
        self.qapplication.exec()