def runner_to_json(runner):
    """Serialize a Runner object to a JSON-compatible dictionary."""
    return {
        "name": runner.name,
        "start_id": runner.start_id,
        "lap_id": runner.lap_id,
        "intervals": [
            {
                "start_time": interval.start_time,
                "end_time": interval.end_time,
                "distance": interval.distance
            } for interval in runner.intervals
        ]
    }