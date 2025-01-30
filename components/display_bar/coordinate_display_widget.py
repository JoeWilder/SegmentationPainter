from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QScrollArea, QListWidget, QListWidgetItem, QSlider, QLineEdit, QSizePolicy , QHBoxLayout, QComboBox  # fmt: skip
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QTransform
from utils.polygon import Polygon
from utils.slider_strength import SliderStrength


class CoordinateDisplayWidget(QWidget):
    """Small window to display current mouse coordinates"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("CoordinateDisplayWidget {border: 2px solid rgb(225, 225, 225); border-radius: 15px;}")

        self.coordinate_label = QLabel("x: - y: -")
        self.coordinate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setMinimumSize(150, 75)

        layout.addWidget(self.coordinate_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def update_coordinates(self, x, y):
        self.x = x
        self.y = y
        self.coordinate_label.setText(f"x: {x} y: {y}")

    def get_coordinates(self):
        return QPoint(self.x, self.y)
