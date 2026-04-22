from typing import Optional
from datetime import datetime

from entity.workout import Workout
from persistence.workout_persistence import (
    list_workouts as _list_workouts,
    save_workout as _save_workout,
)


class WorkoutManager:
    """Owns workout configuration state. No knowledge of athletes, scanners, or timing."""

    def __init__(self):
        self.workout: Optional[Workout] = None
        self.workout_configured = False
        self.current_workout_config: Optional[dict] = None

    def _set_workout(self, distance: int, laps: int, rest: int) -> Workout:
        """Create and configure the Workout object. Returns it for use by the coordinator."""
        self.workout = Workout(datetime.now())
        self.workout.configure(distance, laps, rest)
        self.workout_configured = True
        self.current_workout_config = {"distance": distance, "laps": laps, "rest": rest}
        return self.workout

    def list_workouts(self):
        """Return all saved workout configurations."""
        try:
            return {"ok": True, "workouts": _list_workouts()}
        except Exception as e:
            return {"ok": False, "msg": str(e), "workouts": []}

    def save_workout_entry(self, distance: int, laps: int, rest: int) -> dict:
        """Persist a workout configuration and return the saved entry."""
        return _save_workout(distance, laps, rest)

    def get_all_workouts(self):
        return _list_workouts()
