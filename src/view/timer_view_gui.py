from PySide6.QtCore import QObject, Signal


class TimerViewGUI(QObject):
    """
    Observer that bridges the Runner state machine (background thread) to the
    Qt main thread via a signal.  Both CoachScreen and RunnersScreen connect
    to runner_state_changed to receive live updates.

    Implements the Observer protocol via duck typing (no explicit inheritance
    needed because Observer is a typing.Protocol).
    """
    runner_state_changed = Signal(object)  # carries the Runner instance

    def __init__(self, parent=None):
        super().__init__(parent)

    def update(self, runner):
        """Called by runner.notify_observers() — may be on any thread."""
        self.runner_state_changed.emit(runner)
