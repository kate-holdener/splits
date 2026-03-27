from entity.runner import Runner

def runner_from_dict(runner_dict, fname: str, lname: str, start_id: str, lap_id: str)->Runner:
    """Deserialize a dictionary into a Runner object."""
    runner = Runner()
    print(runner_dict)
    runner.name = runner_dict[fname]
    runner.lname = runner_dict[lname]
    runner.start_id = runner_dict[start_id]
    runner.lap_id = runner_dict[lap_id]
    return runner
