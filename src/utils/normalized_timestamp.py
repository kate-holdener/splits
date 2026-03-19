import time
from datetime import datetime
def get_timestamp_now()->int:
    return int(time.time()*1000)

def datetime_from_timestamp(timestamp: int):
    seconds = timestamp/1000.0
    local_time_naive = datetime.fromtimestamp(seconds)
    return local_time_naive