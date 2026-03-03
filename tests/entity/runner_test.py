import pytest
from datetime import datetime
from entity.runner import Runner
from entity.RunnerState import RunnerState
from entity.workout import Workout

class TestRunner:
    @pytest.fixture(autouse = True)
    def setup(self):
        self.runner = Runner()
        self.runner.name = "Kate"
        self.runner.start_id = "123"
        self.runner.lap_id = "456"
        workout = Workout(datetime.now())
        workout.interval_distance = 400
        workout.laps_per_interval = 1
        self.runner.add_workout(workout)

    def test_start_interval(self):
        self.runner.start_interval(100)
        assert (self.runner.current_status == RunnerState.RUNNING)

    def test_finish_interval(self):
        self.runner.start_interval(100)
        self.runner.add_lap(200)
        assert (self.runner.current_status == RunnerState.RESTING)

    def test_finish_before_start(self):
        self.runner.start_interval(100)
        self.runner.add_lap(50)
        assert (self.runner.current_status == RunnerState.RUNNING)