import threading
from queue import Queue
from entity.runner import Runner
from entity.event import Event
import random
from time import sleep

def find_runner_by_start_id(runners, start_id):
    for runner in runners:
        if runner.start_id == start_id:
            return runner
    return None 



def update_lap_times(elapsed_time, runner_laps, lap_time_queue):
    for runner, lap_time in runner_laps:
        if lap_time == elapsed_time:
            event = Event()
            event.timestamp = elapsed_time
            event.id = runner.lap_id
            lap_time_queue.put(event)
            print(event)

class LapTimeController:
    def __init__(self, lap_time_queue: Queue, runners: list[Runner]):
        self.lap_time_queue = lap_time_queue
        self.runners = runners
        self.thread = None
        self.running = False
        self.runner_start_ids = []

    def start(self, runner_start_ids):
        self.runner_start_ids.extend(runner_start_ids)
        print(self.runner_start_ids)
        """Start the reader thread."""
        if self.thread is not None and self.thread.is_alive():
            print("Reader is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        print('generating lap times')
        while self.running:
            lap_times = []
            runner_laps = []
            # Generate random lap times for each runner
            for id in self.runner_start_ids:
                seconds_per_lap = random.randint(5, 30)
                lap_times.append(seconds_per_lap)
                runner = find_runner_by_start_id(self.runners, id)
                if runner:
                    runner_laps.append((runner, seconds_per_lap))

            #sort lap times from smallest to largest
            lap_times.sort()
            total_time = 0
            for lap in lap_times:
                wait_time = lap - total_time
                total_time += wait_time
                sleep(wait_time)
                print(total_time)
                update_lap_times(total_time, runner_laps, self.lap_time_queue)