from entity.RunnerState import RunnerState
from entity.interval import Interval
from entity.workout import Workout

TIME_DELTA = 1

class Runner:
    """
    Represents a runner participating in an interval training session.

    This class manages the state, workout progress, and intervals of a specific runner.
    It acts as a Subject in the Observer pattern, notifying registered observers 
    when the runner's state changes (e.g., starting an interval, finishing an interval).
    """
    def __init__(self):
        self.name = None
        self.lname = None
        self.start_id = None
        self.lap_id = None
        self.current_status = RunnerState.INACTIVE
        self.intervals = []
        self.lap_count = 0
        self.last_seen_timestamp = 0
        self.observers = []
        self.current_workout = None

    def add_workout(self, workout: Workout):
        """
        Assigns a new workout to the runner as their current active workout.

        Args:
            workout (Workout): The workout object to be assigned to the runner.
        """
        self.current_workout = workout

    def get_status(self) -> RunnerState:
        """
        Retrieves the current status of the runner.

        Returns:
            RunnerState: The current status of the runner (e.g., 'running', 'resting', 'stopped').
        """
        return self.current_status
    
    def get_intervals(self) -> list[Interval]:
        """
        Retrieves the list of training intervals associated with the runner.

        Returns:
            list[Interval]: A list of Interval objects representing the runner's training segments.
        """
        return self.intervals
    
    def add_observer(self, observer):
        if observer not in self.observers:
            self.observers.append(observer)

    def notify_observers(self):
        for observer in self.observers:
            observer.update(self)

    def start_interval(self, timestamp):
        """
        Begins a new workout interval for the runner.

        This method initializes a new Interval object, sets its distance based on the 
        current workout configuration, and records the start time. It updates the 
        runner's status to RUNNING, resets the lap count, and notifies any observers 
        of the state change.

        Args:
            timestamp (int): The time at which the interval is starting (milliseconds since epoch UTC).

        Raises:
            ValueError: If the runner is already in the RUNNING state.
        """
        if self.current_status == RunnerState.RUNNING:
            raise ValueError
        interval = Interval()
        interval.distance = self.current_workout.interval_distance
        interval.start_time = timestamp
        self.intervals.append(interval)
        self.last_seen_timestamp = timestamp
        self.current_status = RunnerState.RUNNING
        self.notify_observers()
        self.lap_count = 0
        #print(f"Runner {self.name} started interval at {timestamp}")

    def add_lap(self, timestamp):
        """
        Records a lap for the runner based on a detected timestamp.

        This method handles debouncing of detection events to prevent duplicate laps caused
        by multiple system reads within a specific time threshold (`TIME_DELTA`). If the timestamp
        is valid and the runner is currently in a `RUNNING` state, it increments the lap count.

        If the lap count reaches the target number of laps for the current interval, the interval
        is marked as complete, the runner's state transitions to `RESTING`, and observers are notified.

        Args:
            timestamp (int): The time at which the lap was detected (milliseconds since epoch UTC).
        """
        # a runner can be detected by a system multiple times
        # we want to ignore events that are within a TIME_DELTA of
        # each other
        print(f"Runner {self.name} lap detected at {timestamp}")
        if abs(timestamp - self.last_seen_timestamp) <= TIME_DELTA:
            self.last_seen_timestamp = timestamp
            return
        if self.current_status == RunnerState.RUNNING and timestamp > self.last_seen_timestamp:
            self.lap_count+=1
            if self.lap_count == self.current_workout.laps_per_interval:
                self.intervals[len(self.intervals) - 1].end_time = timestamp
                self.current_status = RunnerState.RESTING
                self.notify_observers()
                #print(f"Runner {self.name} ended interval at {timestamp}")
            self.last_seen_timestamp = timestamp