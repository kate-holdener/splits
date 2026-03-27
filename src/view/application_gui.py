import sys
from PySide6.QtWidgets import QApplication
from view.landing_screen import LandingScreen


class ApplicationGUI:
    def __init__(self):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._landing = LandingScreen()
        self._landing.show()

    def run(self):
        sys.exit(self._app.exec())
