from dataclasses import dataclass, field
from typing import List



@dataclass
class Performance:
    """Represents an athlete's workout performance."""
    interval_durations: List[int] = field(default_factory=list)
    rest_durations: List[int] = field(default_factory=list)
    incomplete_intervals: int = 0
    average_pace: int = 0  # seconds per mile
