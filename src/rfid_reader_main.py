from readers.sllurp_reader import LLRPReader
from parser.runner_parser import parse_runner_data
from queue import Queue

import argparse

parser = argparse.ArgumentParser(description="Interval training runner")
parser.add_argument("runner_file", help="Path to runner data file")
args = parser.parse_args()

# If main accepts a parameter, pass the filename; otherwise set env var and call main()

queue = Queue()
runners = parse_runner_data(args.runner_file)
scanner_address = '169.254.1.1'
runner_ids = [runner.lap_id for runner in runners]
reader = LLRPReader(queue, scanner_address, runner_ids)
reader.start()
while True:
    event = queue.get()
    print(f"Read event: ID={event.id}, Timestamp={event.timestamp}")
