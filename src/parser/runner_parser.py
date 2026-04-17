import csv
from entity.runner import Runner
from serializer.runner_serializer import runner_from_dict

def parse_runner_data(filename):
    runners = []
    # Open the file in read mode
    with open(filename, mode='r', newline='', encoding='utf-8') as f:
        # Use DictReader to parse the file
        dict_reader = csv.DictReader(f, skipinitialspace=True)
        # Convert the DictReader object to a list
        for row in dict_reader:
            normalized = {k.strip().lower(): v for k, v in row.items()}
            runner = runner_from_dict(normalized, 'first name', 'last name', 'nfc tag', 'rfid tag', 'email')
            runners.append(runner)
    return runners
