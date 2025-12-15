from entity.RunnerState import RunnerState
from entity.interval import Interval

TIME_DELTA = 50

class Runner:
    def __init__(self):
        self.name = None
        self.start_id = None
        self.lap_id = None
        self.current_status = RunnerState.INACTIVE
        self.intervals = []
        self.lap_count = 0
        self.laps_per_interval = 1
        self.last_seen_timestamp = 0
        self.observers = []

    def add_observer(self, observer):
        self.observers.append(observer)

    def notify_observers(self):
        for observer in self.observers:
            observer.update(self)

    def start_interval(self, timestamp):
        if self.current_status == RunnerState.RUNNING:
            raise ValueError
        interval = Interval()
        interval.start_time = timestamp
        self.intervals.append(interval)
        self.last_seen_timestamp = timestamp
        self.current_status = RunnerState.RUNNING
        self.notify_observers()
        self.lap_count = 0
        #print(f"Runner {self.name} started interval at {timestamp}")

    def add_lap(self, timestamp):
        # a runner can be detected by a system multiple times
        # we want to ignore events that are within a TIME_DELTA of
        # each other
        if abs(timestamp - self.last_seen_timestamp) < TIME_DELTA:
            self.last_seen_timestamp = timestamp
            return
        if self.current_status == RunnerState.RUNNING:
            self.lap_count+=1
            if self.lap_count == self.laps_per_interval:
                self.intervals[len(self.intervals) - 1].end_time = timestamp
                self.current_status = RunnerState.RESTING
                self.notify_observers()
                #print(f"Runner {self.name} ended interval at {timestamp}")
            self.last_seen_timestamp = timestamp