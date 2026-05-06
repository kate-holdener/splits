from queue import Queue
from typing import Optional

from controller.start_controller import ManualStartController
from api.runnerObserver import RunnerObserver
from entity.runner import Runner
from entity.workout import Workout
from persistence.session_persistence import (
    WorkoutSessionPersistence,
    load_active_session,
    discard_active_session,
)
from interactors.interval_timer import SplitsTimer

class WorkoutSession:
    """Owns the live workout runtime: timer, event queues, RunnerObserver, and session persistence."""

    def __init__(self):
        self.start_event_q = Queue()
        self.lap_event_q = Queue()
        self.manual_start_controller = ManualStartController(self.start_event_q)
        self.runner_observer = RunnerObserver()

        self.timer = None
        self.session_persistence: Optional[WorkoutSessionPersistence] = None
        self.pending_recovery: Optional[dict] = None
        self.workout_active = False
        self.athletes: list[Runner] = []

    def create_workout_session(self, workout: Workout, athletes: list[Runner]):
        self.athletes = athletes
        for a in self.athletes:
            a.add_observer(self.runner_observer)
            a.add_workout(workout)
        
    def resume_workout_session(self, athletes: list[Runner]):
        self.athletes = athletes
        for a in self.athletes:
            a.add_observer(self.runner_observer)
        for a in self.athletes:
            self.runner_observer.update(a)
        self.workout_active = True

    def group_start(self, tag_ids: list[str]) -> dict:
        self.manual_start_controller.start(tag_ids)
        self.workout_active = True

    # ------------------------------------------------------------------
    # Timer management (called by AppApi coordinator)
    # ------------------------------------------------------------------
    def _stop_timer(self):
        """Stop the interval timer if it is running."""
        if self.timer:
            self.timer.stop()
            self.timer = None

    def _start_timer(self, athletes):
        """Start a new SplitsTimer for the given athlete list."""
        self.timer = SplitsTimer(self.start_event_q, self.lap_event_q, athletes)
        self.timer.start()


    def clear(self) -> None:
        """Reset all live workout state."""
        self._stop_timer()
        self.athletes = []
        self.workout_active = False
        self.session_persistence = None

    # ------------------------------------------------------------------
    # Session persistence wiring (called by AppApi coordinator)
    # ------------------------------------------------------------------
    def _wire_session_persistence(self, session_id: str, roster_id: str) -> None:
        """Create a WorkoutSessionPersistence observer and register it with all runners."""
        self.session_persistence = WorkoutSessionPersistence(
            session_id=session_id,
            roster_id=roster_id,
            athletes=self.athletes,
        )
        for a in self.athletes:
            a.add_observer(self.session_persistence)

    # ------------------------------------------------------------------
    # Live workout state
    # ------------------------------------------------------------------
    def get_resting(self):
        """Return the current resting list with timing data."""
        athletes = []
        for r in self.runner_observer.resting:
            rest_duration = r.get_workout().get_rest_time()
            d = r.to_dict()
            rest_elapsed = self.runner_observer.rest_elapsed(r)
            d['rest_elapsed'] = round(rest_elapsed, 1)
            d['rest_duration'] = rest_duration
            d['rest_remaining_seconds'] = max(0, round(rest_duration - rest_elapsed))
            athletes.append(d)
        return {"ok": True, "athletes": athletes}

    def finish_workout(self):
        """Clear observer state, finalize persistence, and return the completed session ID."""
        self.runner_observer.running.clear()
        self.runner_observer.resting.clear()
        self.workout_active = False
        last_id = None
        self._stop_timer()
        if self.session_persistence:
            last_id = self.session_persistence._session_id
            self.session_persistence.finish_session()
            self.session_persistence = None
        return last_id

    def shutdown(self):
        """Stop the timer and persist current session state if a workout is active."""
        if self.timer:
            self.timer.stop()
        if self.session_persistence and self.workout_active:
            try:
                self.session_persistence._persist()
            except Exception:
                pass
        return {"ok": True}

    # ------------------------------------------------------------------
    # Session recovery
    # ------------------------------------------------------------------
    def check_for_recovery(self):
        """Check for an unfinished session from a previous run."""
        session_dict = load_active_session()
        if session_dict:
            self.pending_recovery = session_dict

    def get_pending_recovery(self) -> dict:
        """Return recovery info for the GUI to display a resume dialog."""
        if not self.pending_recovery:
            return {"hasPendingRecovery": False}
        s = self.pending_recovery
        runners = s.get("runners", [])
        first_workout = runners[0].get("workout") if runners else None
        return {
            "hasPendingRecovery": True,
            "started_at":    s.get("started_at"),
            "saved_at":      s.get("saved_at"),
            "athlete_count": len(runners),
            "workout":       first_workout,
        }

    def discard_recovery(self) -> dict:
        """Delete the active session file without restoring it."""
        discard_active_session()
        self.pending_recovery = None
        return {"ok": True}
