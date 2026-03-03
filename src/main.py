from interactors.interval_timer import IntervalTimer
from entity.runner import Runner
from entity.event import Event
from view.timer_view import TimerView
from parser.runner_parser import parse_runner_data
from controller.start_controller import ManualStartController
from queue import Queue
from time import sleep
import random
import argparse


def update_lap_times(elapsed_time, runner_laps, lap_time_queue):
    for runner, lap_time in runner_laps:
        if lap_time == elapsed_time:
            event = Event()
            event.timestamp = elapsed_time
            event.id = runner.lap_id
            lap_time_queue.put(event)

def main(runner_file):
    start_time_queue = Queue()
    lap_time_queue = Queue()
    manual_start_controller = ManualStartController(start_time_queue)

    runners = parse_runner_data(runner_file)

    print(runners)

    start_time = 100
    start_ids = []
    for runner in runners:
        start_ids.append(runner.start_id)
    manual_start_controller.start_runners(start_ids, start_time)

    timer_view = TimerView()
    for runner in runners:
        runner.add_observer(timer_view)

    interval_timer = IntervalTimer(start_time_queue, lap_time_queue, runners)
    interval_timer.start()

    lap_times = []
    runner_laps = []
    # Generate random lap times for each runner
    for i in range(len(runners)):
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

    parser = argparse.ArgumentParser(description="Interval training runner")
    parser.add_argument("runner_file", help="Path to runner data file")
    args = parser.parse_args()

    # If main accepts a parameter, pass the filename; otherwise set env var and call main()
    main(args.runner_file)
