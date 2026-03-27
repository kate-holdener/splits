import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from view.application_gui import ApplicationGUI


def main():
    ApplicationGUI().run()


if __name__ == "__main__":
    main()
