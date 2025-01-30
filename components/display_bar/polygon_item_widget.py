from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QScrollArea, QListWidget, QListWidgetItem, QSlider, QLineEdit, QSizePolicy , QHBoxLayout, QComboBox  # fmt: skip
from PyQt6.QtCore import Qt
from utils.polygon import Polygon


class PolygonItemWidget(QWidget):
    """An editable polygon entry to be placed in a list box"""

    def __init__(self, polygon_item: Polygon, parent=None):
        super().__init__(parent)
        self.polygon_item = polygon_item

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.polygon_label = QLabel(self.polygon_item.get_display_name())
        self.polygon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.polygon_label)
        self.polygon_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.line_edit = QLineEdit(self)
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setVisible(False)
        self.layout.addWidget(self.line_edit)

        self.setLayout(self.layout)

        self.polygon_label.mouseDoubleClickEvent = self._start_editing_listener
        self.line_edit.editingFinished.connect(self._finish_editing)

    def _start_editing_listener(self, event):
        self.polygon_label.setVisible(False)
        self.line_edit.setText(self.polygon_label.text())
        self.line_edit.setVisible(True)
        self.line_edit.setFocus()

    def _finish_editing(self):
        new_name = self.line_edit.text()
        self.polygon_item.set_display_name(new_name)
        self.polygon_label.setText(new_name)
        self.line_edit.setVisible(False)
        self.polygon_label.setVisible(True)
