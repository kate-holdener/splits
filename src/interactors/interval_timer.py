import threading
from queue import Queue
from queue import Empty

class IntervalTimer:
    def __init__(self, start_time_queue, lap_time_queue, runners):
        self.start_queue = start_time_queue
        self.lap_queue = lap_time_queue
        self.runners_by_start_id = {}
        self.runners_by_lap_id = {}
        for runner in runners:
            self.runners_by_start_id[runner.start_id] = runner
            self.runners_by_lap_id[runner.lap_id] = runner
        self.thread = None
        self.running = False
        self.observers = []

    def _run(self):
        while(self.running or not self.lap_queue.empty() or not self.start_queue.empty()):
            start_q_size = self.start_queue.qsize()
            for i in range(0, start_q_size):
                try:
                    start_event = self.start_queue.get_nowait()
                    self._process_start_event(start_event)
                except Empty:
                    pass
                
            lap_q_size = self.lap_queue.qsize()
            for i in range(0, lap_q_size):
                try:
                    lap_event = self.lap_queue.get_nowait()
                    self._process_lap_event(lap_event)
                except Queue.Empty:
                    pass


    def _process_start_event(self, start_event):
        if start_event.id in self.runners_by_start_id:
            self.runners_by_start_id[start_event.id].start_interval(start_event.timestamp)

    def _process_lap_event(self, lap_event):
        if lap_event.id in self.runners_by_lap_id:
            self.runners_by_lap_id[lap_event.id].add_lap(lap_event.timestamp)

    def start(self):
        """Start the reader thread."""
        if self.thread is not None and self.thread.is_alive():
            print("Reader is already running")
            return
    
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the reader thread."""
        self.running = False
        if self.thread is not None:
            self.thread.join()       
