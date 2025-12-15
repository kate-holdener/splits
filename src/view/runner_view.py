import threading

class RestingRunner:
    def __init__(self, runner, rest_seconds):
        self.runner = runner
        self.rest_seconds = rest_seconds
    def get_name(self):
        return self.runner.name
    
class RunnerDisplayThread:
    def __init__(self):
        self.resting_runners = []
        # obtain the lock before accessing resting_runners
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.thread = None

    def add_resting_runner(self, runner):
        with self._lock:
            self.resting_runners.append(runner)

    def remove_resting_runner(self, runner):
        with self._lock:
            for resting_runner in self.resting_runners:
                if resting_runner.runner == runner:
                    self.resting_runners.remove(resting_runner)
                    break

    def update_rest_time(self, seconds_elapsed=1):
        with self._lock:
            for runner in list(self.resting_runners):
                runner.rest_seconds -= seconds_elapsed


    def show_resting_runners(self):
        with self._lock:
            for runner in self.resting_runners:
                if runner.rest_seconds <= 0:
                    print(f"Runner {runner.get_name()} is ready to start a new interval.")
                else:
                    print(f"Runner: {runner.get_name()}, Rest Time Left: {runner.rest_seconds} seconds")

    def _run(self):
        while not self._stop.is_set():
            # ensure display_status uses _lock if it touches shared state
            self.update_rest_time()
            print("Resting Runners:")
            self.show_resting_runners()
            print("************************")
            self._stop.wait(1)

    def start(self):
        if self.thread and self.thread.is_alive():
            print("Runner display thread is already running")
            return
        self._stop.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop.set()
        if self.thread:
            self.thread.join()