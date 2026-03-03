from parser.runner_parser import parse_runner_data

def test_parse_runner_data():
    input_data='test_data/runners.csv'
    runners = parse_runner_data(input_data)
    assert(len(runners) == 3)