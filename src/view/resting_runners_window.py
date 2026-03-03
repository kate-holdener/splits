from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtCore import QTimer
from threading import Lock

UPDATE_SECONDS = 1  # Update every second

class RestingRunnersWindow(QWidget):
    def __init__(self):
        self.resting_runners = []
        # obtain the lock before accessing resting_runners
        self._lock = Lock()

        super().__init__()
        self.setWindowTitle("Resting Runners")
        
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        
        layout = QVBoxLayout()
        layout.addWidget(self.text_display)
        self.setLayout(layout)
        
        # Single timer updates the display every second
        # It will show each runner's individual countdown
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(UPDATE_SECONDS * 1000)  # Update every second
        
        self.update_display()
    
    def update_display(self):
        text = "Resting Runners:\n\n"
        
        # Each runner calculates their own remaining time
        self._lock.acquire()
        for runner in self.resting_runners:
            runner.rest_seconds -= UPDATE_SECONDS
            if runner.rest_seconds > 0:
                text += f"{runner.get_name()}: {runner.rest_seconds}s remaining\n"
            else:
                text += f"{runner.get_name()}: Ready to start!\n"
        self._lock.release()
        self.text_display.setText(text)

    def add_resting_runner(self, runner):
        with self._lock:
            self.resting_runners.append(runner)

    def remove_resting_runner(self, runner):
        with self._lock:
            for resting_runner in self.resting_runners:
                if resting_runner.runner == runner:
                    self.resting_runners.remove(resting_runner)
                    break
