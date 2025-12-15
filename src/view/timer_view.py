from boundary.observer import Observer
from view.runner_view import RunnerDisplayThread
from view.runner_view import RestingRunner
from entity.RunnerState import RunnerState

class TimerView(Observer):
    def __init__(self):
        self.runner_display_thread = RunnerDisplayThread()
        self.runner_display_thread.start()

    def update(self, runner):
        if runner.current_status == RunnerState.RESTING:
            self.runner_display_thread.add_resting_runner(RestingRunner(runner, 30))
        elif runner.current_status == RunnerState.RUNNING:
            self.runner_display_thread.remove_resting_runner(runner)
