from PySide6.QtWidgets import (QApplication)
from view.main_menu_gui import MainMenuGUI
import sys

class ApplicationGUI():
    def __init__(self, runners, controllers):
        self.qapplication = QApplication(sys.argv)
        self.main_menu = MainMenuGUI(runners, controllers)
        self.main_menu.show()
        self.qapplication.exec()