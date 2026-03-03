
from datetime import datetime
class Workout:
    def __init__(self, date_and_time: datetime):
        self.date_and_time = date_and_time
        self.interval_distance = 0
        self.laps_per_interval = 0 # how many times a runner must cross the lap sensor to complete an interval
    