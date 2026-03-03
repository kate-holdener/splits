from readers.sllurp_reader import LLRPReader
from view.timer_view import TimerView
from view.workout_manager_gui import WorkoutManagerGUI
from view.timer_view_gui import TimerViewGUI
from parser.runner_parser import parse_runner_data
from interactors.interval_timer import IntervalTimer
from controller.start_controller import ManualStartController
from queue import Queue
from report.pdf_report_runner import generate_runner_report
import argparse

def main(runner_file):
    start_time_queue = Queue()
    lap_time_queue = Queue()
    manual_start_controller = ManualStartController(start_time_queue)

    runners = parse_runner_data(runner_file)
    runner_ids = [runner.lap_id for runner in runners]
    scanner_address = '169.254.1.1'
    reader = LLRPReader(lap_time_queue, scanner_address, runner_ids)
    reader.start()

    interval_timer = IntervalTimer(start_time_queue, lap_time_queue, runners)
    interval_timer.start()

    controllers = [manual_start_controller]
    gui = WorkoutManagerGUI(runners, controllers)

    timer_view = TimerViewGUI()
    for runner in runners:
        runner.add_observer(timer_view)    

    gui.run()

    for runner in runners:
        generate_runner_report(runner, "reports/runner_{}.pdf".format(runner.start_id))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interval training runner")
    parser.add_argument("runner_file", help="Path to runner data file")
    args = parser.parse_args()

    # If main accepts a parameter, pass the filename; otherwise set env var and call main()
    main(args.runner_file)
