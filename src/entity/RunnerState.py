from enum import Enum, IntEnum, auto


# Basic enumeration
class RunnerState(Enum):
    INACTIVE = 0
    RUNNING = 1
    RESTING = 2
    FINISHED = 3
