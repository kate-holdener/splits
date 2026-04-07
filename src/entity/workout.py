
from datetime import datetime
class Workout:
    def __init__(self, date_and_time: datetime):
        self.date_and_time = date_and_time
        self.interval_distance = 0
        self.laps_per_interval = 0 # how many times a runner must cross the lap sensor to complete an interval
        self.rest_time = 0 # seconds of rest between intervals

    def configure(self, distance: int, laps_per_interval: int, rest_time: int = 0):
        self.interval_distance = distance
        self.laps_per_interval = laps_per_interval
        self.rest_time = rest_time
   
    def get_rest_time(self):
        return self.rest_time 
