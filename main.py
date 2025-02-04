import sys
import ctypes
from PyQt6.QtWidgets import QApplication

from main_page import MainPage

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

if __name__ == "__main__":
    myappid = "ccom.segmentationpainter.segmentationpainter.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)  # set taskbar icon
    app = QApplication([])
    window = MainPage()
    window.show()

    sys.exit(app.exec())
