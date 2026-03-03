from interactors.interval_timer import IntervalTimer
from entity.event import Event
from queue import Queue
from datetime import datetime
from datetime import timezone

class ManualStartController:
    def __init__(self, start_event_queue: Queue):
        self.start_event_queue = start_event_queue
        self.start_time = 0

    def start(self, runner_start_ids):
        timestamp = int(datetime.now(timezone.utc).timestamp())
        self.start_time = timestamp
        for start_id in runner_start_ids:
            event = Event()
            event.id = start_id
            event.timestamp = timestamp
            self.start_event_queue.put(event)