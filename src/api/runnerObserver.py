from datetime import datetime
from entity.runner import Runner
from entity.RunnerState import RunnerState
# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------
class RunnerObserver:
    def __init__(self):
        self.running: list[Runner] = []
        self.resting: list[Runner] = []
        self._rest_start: dict = {}   # id(runner) -> epoch float when resting began

    def update(self, runner):
        st = runner.get_status()
        if st == RunnerState.RUNNING:
            if runner not in self.running:
                self.running.append(runner)
            if runner in self.resting:
                self.resting.remove(runner)
                self._rest_start.pop(id(runner), None)
        elif st == RunnerState.RESTING:
            if runner in self.running:
                self.running.remove(runner)
            if runner not in self.resting:
                self.resting.append(runner)
                self._rest_start[id(runner)] = datetime.now().timestamp()
        else:
            if runner in self.running:
                self.running.remove(runner)
            if runner in self.resting:
                self.resting.remove(runner)
                self._rest_start.pop(id(runner), None)

    def rest_elapsed(self, runner) -> float:
        """Seconds since this runner started resting (0.0 if unknown)."""
        start = self._rest_start.get(id(runner))
        if start is None:
            return 0.0
        return datetime.now().timestamp() - start