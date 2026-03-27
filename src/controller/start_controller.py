from interactors.interval_timer import IntervalTimer
from entity.event import Event
from queue import Queue
from datetime import datetime
from datetime import timezone
from utils.normalized_timestamp import get_timestamp_now
class ManualStartController:
    def __init__(self, start_event_queue: Queue):
        self.start_event_queue = start_event_queue
        self.start_time = 0

    def start(self, runner_start_ids):
        timestamp = get_timestamp_now() #int(datetime.now(timezone.utc).timestamp())
        self.start_time = timestamp
        for start_id in runner_start_ids:
            event = Event(start_id, timestamp)
            self.start_event_queue.put(event)