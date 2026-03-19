from entity.runner import Runner
from entity.performance import Performance

def calculate_performance(runner: Runner) -> Performance:
    """
    Populate a Performance object from a Runner's interval data.
    
    Args:
        runner: A Runner object containing a list of Interval objects.
        
    Returns:
        Performance: A populated Performance dataclass.
        
    Notes:
        - Interval duration is end_time - start_time for completed intervals.
        - Rest duration is the time between the end of one completed interval
          and the start of the next completed interval.
        - Average pace is calculated as seconds per mile based on completed intervals.
    """
    performance = Performance()
    
    intervals = runner.get_intervals()
    completed_intervals = []
    
    for interval in intervals:
        if interval.incomplete:
            performance.incomplete_intervals += 1
        else:
            completed_intervals.append(interval)
            duration = interval.get_end_time() - interval.get_start_time()
            performance.interval_durations.append(duration)
    
    # Calculate rest durations between consecutive completed intervals
    for i in range(len(completed_intervals) - 1):
        current_end = completed_intervals[i].get_end_time()
        next_start = completed_intervals[i + 1].get_start_time()
        rest_duration = next_start - current_end
        performance.rest_durations.append(rest_duration)
    
    # Calculate average pace (seconds per mile)
    if completed_intervals:
        total_duration = sum(performance.interval_durations)
        total_distance = sum(iv.get_distance() for iv in completed_intervals)
        
        if total_distance > 0:
            # Convert to seconds per mile (1 mile = 1609.34 meters)
            meters_per_mile = 1600
            performance.average_pace = int(total_duration * meters_per_mile / total_distance)
    
    return performance
