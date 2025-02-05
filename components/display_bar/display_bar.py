from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

from components.display_bar.display_bar_toolbox import DisplayBarToolbox
from components.display_bar.coordinate_display_widget import CoordinateDisplayWidget


class DisplayBar(QWidget):
    """Combines all display bar functionality into a single manager class"""

    def __init__(self, image_display):
        super().__init__()
        self.image_display = image_display
        self.display_bar_toolbox = DisplayBarToolbox(self.image_display)
        self.coordinate_display_widget = CoordinateDisplayWidget(self)

        layout = QVBoxLayout(self)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.display_bar_toolbox)
        layout.addStretch()
        layout.addWidget(self.coordinate_display_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def get_toolbox(self):
        return self.display_bar_toolbox

    def get_coordinate_display_widget(self):
        return self.coordinate_display_widget

    def get_annotation_label(self):
        return self.display_bar_toolbox.annotation_dropdown.currentText()

    def close(self):
        self.hide()
        self.display_bar_toolbox.polygon_list.clear()
        self.display_bar_toolbox.polygon_image_label.clear()
        self.display_bar_toolbox.selected_polygon = None
