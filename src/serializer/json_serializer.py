def runner_to_json(runner):
    """Serialize a Runner object to a JSON-compatible dictionary."""
    return {
        "name": runner.name,
        "lname": getattr(runner, 'lname', ''),  # Include last name if available
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
            
            # Initialize empty intervals list (we don't persist workout state)
            runner.intervals = []
            
            runners.append(runner)
            
        except Exception as e:
            print(f"Warning: Failed to create runner from data at index {i}: {e}")
            continue
    
    return runners