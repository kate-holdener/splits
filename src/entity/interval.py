class Interval:
    """
    Interval class represents a segment of a workout, defined by its distance, start time, and end time.
    """
    def __init__(self):
        """Initializes a new Interval instance with default zero values."""
        self.distance = 0
        self.start_time = 0
        self.end_time = 0
        self.incomplete = True
        
    def get_distance(self)->int:
        """Returns the distance covered in this interval."""
        return self.distance
    
    def get_start_time(self)->int:
        """Returns the start time of this interval."""            
        return self.start_time
    
    def get_end_time(self)->int:
        """Returns the end time of this interval."""
        return self.end_time
    
    def start(self, timestamp):
        self.start_time = timestamp

    def finish(self, timestamp):
        self.end_time = timestamp
        self.incomplete = False