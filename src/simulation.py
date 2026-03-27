import sys
import csv
from parser.runner_parser import parse_runner_data
from entity.workout import Workout
from entity.event import Event
from queue import Queue

from datetime import datetime
from interactors.interval_timer import IntervalTimer

def read_command_line_arguments():
    """
    Reads command line arguments for roster and commands file paths.
    
    Returns:
        tuple: (roster_file, commands_file) paths
        
    Raises:
        SystemExit: If incorrect number of arguments provided
    """
    if len(sys.argv) != 3:
        print("Usage: python simulation.py <roster_file.csv> <commands_file.csv>")
        sys.exit(1)
    
    roster_file = sys.argv[1]
    commands_file = sys.argv[2]
    
    return roster_file, commands_file


def print_runner_intervals(runners):
    """
    Prints runner interval and rest duration data in CSV format.
    
    Args:
        runners: List of runner objects with get_intervals() method
    """
    print("first_name,last_name,interval1_duration,rest1_duration,interval2_duration,rest2_duration")
    
    for runner in runners:
        intervals = runner.get_intervals()
        first_name = runner.name
        last_name = runner.lname
        
        row = [first_name, last_name]
        
        for i in range(len(intervals)):
            interval = intervals[i]
            duration = (interval.end_time - interval.start_time) / 1000
            row.append(str(int(duration)))
            
            if i < len(intervals) - 1:
                rest_duration = (intervals[i + 1].start_time - interval.end_time) / 1000
                row.append(str(int(rest_duration)))
        print(",".join(row))

if __name__ == "__main__":
    roster_csv, commands_csv = read_command_line_arguments()
    athletes = parse_runner_data(roster_csv)
    workout = Workout(datetime.now())
    workout.interval_distance = 400
    workout.laps_per_interval = 1
    for a in athletes:
        a.add_workout(workout)
    
    
    start_q = Queue()
    lap_q = Queue()
    intervalTimer = IntervalTimer(start_q, lap_q, athletes)
    intervalTimer.start()

    with open(commands_csv, 'r') as f:
        reader = csv.reader(f)
        current_group = []

        for row in reader:
            row = [item.strip() for item in row]
            command = row[0]
            
            if command == 'GROUP':
                current_group = row[1:]
            
            elif command == 'START':
                timestamp = int(row[1])
                for nfc_tag in current_group:
                    event = Event(nfc_tag, timestamp)
                    start_q.put(event)
                current_group = []
            
            elif command == 'NFC':
                nfc_tag = row[1]
                timestamp = int(row[2])
                event = Event(nfc_tag, timestamp)
                start_q.put(event)
            
            elif command == 'RFID':
                rfid_tag = row[1]
                timestamp = int(row[2])
                event = Event(rfid_tag, timestamp)
                lap_q.put(event)
    intervalTimer.stop()
    print_runner_intervals(athletes)