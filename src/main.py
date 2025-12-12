from interactors.interval_timer import IntervalTimer
from entity.runner import Runner
from entity.event import Event
from queue import Queue
from time import sleep
import random

def main():
    start_time_queue = Queue()
    lap_time_queue = Queue()
    runners = []  # Initialize with actual runner objects
    for i in range(10):
        runner = Runner()
        runner.name = f"Runner_{i+1}"
        runner.start_id = i
        runner.lap_id = i + 100
        runners.append(runner)

    start_time = 100
    for i in range(len(runners)):
        event = Event()
        event.timestamp = start_time
        event.id = i
        start_time_queue.put(event)

    for i in range(len(runners)):
        event = Event()
        event.timestamp = start_time + random.randint(10, 300)
        event.id = i + 100
        lap_time_queue.put(event)

    interval_timer = IntervalTimer(start_time_queue, lap_time_queue, runners)
    interval_timer.start()
    interval_timer.stop()

if __name__ == "__main__":
    main()