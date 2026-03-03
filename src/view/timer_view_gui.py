from boundary.observer import Observer
from entity.RunnerState import RunnerState
from view.runner_view import RestingRunner
from view.resting_runners_window import RestingRunnersWindow

class TimerViewGUI(Observer):
    def __init__(self):
        self.runners_window = RestingRunnersWindow()
        self.runners_window.show()

    def update(self, runner):
        if runner.current_status == RunnerState.RESTING:
            self.runners_window.add_resting_runner(RestingRunner(runner, 30))
        elif runner.current_status == RunnerState.RUNNING:
            self.runners_window.remove_resting_runner(runner)