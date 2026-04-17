def runner_to_json(runner):
    """Serialize a Runner object to a JSON-compatible dictionary."""
    return {
        "id": runner.lap_id,  # Use lap_id as unique identifier
        "name": runner.name,
        "first_name": runner.name,  # Add for compatibility
        "last_name": getattr(runner, 'lname', ''),
        "lname": getattr(runner, 'lname', ''),  # Include last name if available
        "start_tag": runner.start_id,  # Use same field names as Runner.to_dict()
        "finish_tag": runner.lap_id,  # Use same field names as Runner.to_dict()
        "start_id": runner.start_id,  # Keep for backward compatibility
        "lap_id": runner.lap_id,      # Keep for backward compatibility
        "archived": getattr(runner, 'archived', False),
        "archived_at": getattr(runner, 'archived_at', None),
        "intervals": [
            {
                "start_time": interval.start_time,
                "end_time": interval.end_time,
                "distance": interval.distance
            } for interval in runner.intervals
        ]
    }


def runner_to_session_json(runner) -> dict:
    """Serialize a Runner to a session snapshot dict (includes live workout state).

    Unlike runner_to_json, this includes current_status, lap_count, the runner's
    assigned workout, and the full interval history with incomplete flags.
    Used exclusively by WorkoutSessionPersistence — not for roster files.
    """
    d = runner_to_json(runner)
    d["current_status"] = runner.current_status.value  # int value of RunnerState enum
    d["lap_count"] = runner.lap_count
    w = runner.current_workout
    d["workout"] = {
        "interval_distance": w.interval_distance,
        "laps_per_interval": w.laps_per_interval,
        "rest_time":         w.rest_time,
        "date_and_time":     w.date_and_time.isoformat(),
    } if w else None
    d["session_intervals"] = [
        {
            "start_time": iv.start_time,
            "end_time":   iv.end_time,
            "distance":   iv.distance,
            "incomplete": iv.incomplete,
        }
        for iv in runner.intervals
    ]
    return d


def runners_from_json(json_data):
    """
    Deserialize a list of JSON dictionaries into Runner objects.
    
    Args:
        json_data: List of dictionaries containing runner data
        
    Returns:
        List of Runner objects
        
    Raises:
        ValueError: If json_data is invalid or required fields are missing
    """
    from entity.runner import Runner
    
    if not isinstance(json_data, list):
        raise ValueError("json_data must be a list of dictionaries")
    
    runners = []
    
    for i, runner_dict in enumerate(json_data):
        if not isinstance(runner_dict, dict):
            print(f"Warning: Skipping invalid runner data at index {i}: not a dictionary")
            continue
        
        # Check required fields
        required_fields = ["name", "start_id", "lap_id"]
        missing_fields = [field for field in required_fields if field not in runner_dict]
        
        if missing_fields:
            print(f"Warning: Skipping runner at index {i}: missing required fields {missing_fields}")
            continue
        
        try:
            # Create new Runner object
            runner = Runner()
            runner.name = str(runner_dict["name"])
            runner.lname = str(runner_dict.get("lname", ""))  # Optional last name
            runner.start_id = str(runner_dict["start_id"])
            runner.lap_id = str(runner_dict["lap_id"])
            runner.archived = runner_dict.get("archived", False)
            runner.archived_at = runner_dict.get("archived_at", None)
            
            # Initialize empty intervals list (we don't persist workout state)
            runner.intervals = []
            
            runners.append(runner)
            
        except Exception as e:
            print(f"Warning: Failed to create runner from data at index {i}: {e}")
            continue
    
    return runners