from interactors.interval_timer import IntervalTimer
from entity.runner import Runner
from entity.event import Event
from view.timer_view import TimerView

from queue import Queue
from time import sleep
import random

def update_lap_times(elapsed_time, runner_laps, lap_time_queue):
    for runner, lap_time in runner_laps:
        if lap_time == elapsed_time:
            event = Event()
            event.timestamp = elapsed_time
            event.id = runner.lap_id
            lap_time_queue.put(event)
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

    timer_view = TimerView()
    for runner in runners:
        runner.add_observer(timer_view)

    interval_timer = IntervalTimer(start_time_queue, lap_time_queue, runners)
    interval_timer.start()

    lap_times = []
    runner_laps = []
    for i in range(len(runners)):
        event = Event()
        seconds_per_lap = random.randint(5, 30)
        lap_times.append(seconds_per_lap)
        runner_laps.append((runners[i], seconds_per_lap))
    #sort lap times from smallest to largest
    lap_times.sort()
    total_time = 0
    for lap in lap_times:
        wait_time = lap - total_time
        total_time += wait_time
        sleep(wait_time)
        update_lap_times(total_time, runner_laps, lap_time_queue)
    interval_timer.stop()
    sleep(10)

if __name__ == "__main__":
    main()