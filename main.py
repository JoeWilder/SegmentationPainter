import sys
from PyQt6.QtWidgets import QApplication

from main_page import MainPage

if __name__ == "__main__":
    app = QApplication([])
    window = MainPage()
    window.show()
    sys.exit(app.exec())
