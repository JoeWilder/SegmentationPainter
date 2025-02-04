from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QScrollArea, QListWidget, QListWidgetItem, QSlider, QLineEdit, QSizePolicy , QHBoxLayout, QComboBox  # fmt: skip
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QTransform
from utils.polygon import Polygon
from utils.slider_strength import SliderStrength
from typing import TYPE_CHECKING
import os

from components.display_bar.polygon_item_widget import PolygonItemWidget

if TYPE_CHECKING:
    from components.image_canvas import ImageCanvas


class DisplayBarToolbox(QWidget):
    """The main functionality of the display bar, including the polygon list box, model strength slider, and polygon image display"""

    export_image_event = pyqtSignal()
    strength_slider_change_event = pyqtSignal(SliderStrength)

    def __init__(self, image_canvas):
        super().__init__()
        self.image_canvas: ImageCanvas = image_canvas

        self.model_strength = SliderStrength.AUTO
        self.selected_polygon = None
        self.last_mask_manager = None

        self.polygon_image_label = QLabel()
        self.polygon_image_label.setMinimumHeight(100)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("DisplayBarToolbox {border: 2px solid rgb(225, 225, 225); border-radius: 15px;}")

        layout.addWidget(self.polygon_image_label)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.current_polygon_label = QLabel("Current Polygon")
        self.current_polygon_label.setObjectName("CurrentPolygonLabel")
        self.current_polygon_label.setStyleSheet(
            """
            #CurrentPolygonLabel {
                font-size: 16px;
                font-weight: bold;
            }
            """
        )
        self.current_polygon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.current_polygon_label)

        self.current_group_id_label = QLabel("Current Group ID: None")
        self.current_group_id_label.setObjectName("CurrentGroupID")
        self.current_group_id_label.setStyleSheet(
            """
            #CurrentGroupID {
                color: gray;
            }
            """
        )
        self.current_group_id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.current_group_id_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumWidth(200)
        layout.addWidget(scroll_area, alignment=Qt.AlignmentFlag.AlignRight)

        self.polygon_list = QListWidget()

        self.polygon_list.itemPressed.connect(self._list_item_clicked_listener)

        scroll_area.setWidget(self.polygon_list)

        text_layout = QVBoxLayout()
        text_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.annotation_dropdown_label = QLabel("Polygon Label")
        self.annotation_dropdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.annotation_dropdown_label.setMaximumWidth(300)
        self.annotation_dropdown_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.annotation_dropdown_label.setObjectName("PolygonLabel")
        self.annotation_dropdown_label.setStyleSheet(
            """
            #PolygonLabel {
                margin-top: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            """
        )

        text_layout.addWidget(self.annotation_dropdown_label)

        self.annotation_dropdown = QComboBox()

        if os.path.exists("./labels.txt"):
            with open("./labels.txt", "r") as f:
                lines = f.readlines()
                lines = [line.strip() for line in lines]
                lines.sort()
                self.annotation_dropdown.addItems(lines)
        else:
            self.annotation_dropdown.addItem("coral")

        self.annotation_dropdown.setObjectName("AnnotationDropdown")
        self.annotation_dropdown.setStyleSheet(
            """
            #AnnotationDropdown {
                font-size: 16px;
                font-weight: bold;
            }
            """
        )

        self.annotation_dropdown.setEditable(True)
        self.annotation_dropdown.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.annotation_dropdown.lineEdit().setReadOnly(True)

        text_layout.addWidget(self.annotation_dropdown)

        self.labels_edit_button = QPushButton("Edit Labels")
        # self.labels_edit_button.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labels_edit_button.setMaximumWidth(300)
        self.labels_edit_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.labels_edit_button.setObjectName("LabelsEditLabel")
        self.labels_edit_button.setStyleSheet(
            """
            #LabelsEditLabel {
                color: gray;
                border: 2px solid #007BFF;
                border-radius: 15px;
                padding: 5px 10px;
            }

            #LabelsEditLabel:hover {
                background-color: #fafafa;
            }
            """
        )
        self.labels_edit_button.clicked.connect(self.edit_labels)
        text_layout.addWidget(self.labels_edit_button)

        self.group_dropdown_label = QLabel("Group ID")
        self.group_dropdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_dropdown_label.setMaximumWidth(300)
        self.group_dropdown_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.group_dropdown_label.setObjectName("GroupID")
        self.group_dropdown_label.setStyleSheet(
            """
            #GroupID {
                margin-top: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            """
        )

        text_layout.addWidget(self.group_dropdown_label)

        self.group_dropdown = QComboBox()
        self.group_dropdown.setEditable(True)
        self.group_dropdown.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.group_dropdown.addItem("None")
        self.group_dropdown.setCurrentText("None")

        self.group_dropdown.lineEdit().editingFinished.connect(self.add_new_group)

        self.group_dropdown.setObjectName("GroupDropdown")
        self.group_dropdown.setStyleSheet(
            """
            #GroupDropdown {
                font-size: 16px;
                font-weight: bold;
            }
            """
        )

        text_layout.addWidget(self.group_dropdown)

        layout.addLayout(text_layout)

        self.model_strength_label = QLabel("Model Strength")
        self.model_strength_label.setObjectName("ModelStrengthLabel")
        self.model_strength_label.setStyleSheet(
            """
            #ModelStrengthLabel {
                margin-top: 40px;
                font-size: 16px;
                font-weight: bold;
            }
        """
        )
        self.model_strength_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.model_strength_label)

        self.strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.strength_slider.setMinimum(0)
        self.strength_slider.setMaximum(3)
        self.strength_slider.setTickInterval(1)
        self.strength_slider.setSingleStep(1)  # Ensure step-by-step movement
        self.strength_slider.setPageStep(1)  # Snap when clicking on the track
        self.strength_slider.setTracking(False)  # Only change on release

        self.strength_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.strength_slider.valueChanged.connect(self._strength_slider_changed_listener)

        self.strength_slider.setMinimumWidth(150)

        self.strength_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(self.strength_slider, alignment=Qt.AlignmentFlag.AlignCenter)

        self.strength_slider_labels = ["Best", "Weakest", "Medium", "Strongest"]

        self.current_strength_label = QLabel("Best")
        self.current_strength_label.setObjectName("CurrentStrengthLabel")
        self.current_strength_label.setStyleSheet(
            """
            #CurrentStrengthLabel {
                color: gray;
            }
            """
        )
        self.current_strength_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.current_strength_label)

        export_image_button = QPushButton("Export Image")
        export_image_button.setMinimumSize(75, 35)
        export_image_button.clicked.connect(self.export_image)
        export_image_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(export_image_button)

        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        export_image_button.setStyleSheet(
            """
            QPushButton {
                margin-top: 40px;
                border: 2px solid #007BFF;
                border-radius: 15px;
                padding: 10px 20px;
                color: #007BFF;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fafafa;
            }
            """
        )

    def _strength_slider_changed_listener(self, index):
        """An internal listener for when the strength slider is changed"""
        action = SliderStrength.fromValue(index)
        self.mask_level = action
        self.strength_slider_change_event.emit(action)
        self.current_strength_label.setText(self.get_text_from_slider_index(index))

    def edit_labels(self):
        os.system(f"notepad {os.getcwd()}/labels.txt")

        self.annotation_dropdown.clear()
        if os.path.exists("./labels.txt"):
            with open("./labels.txt", "r") as f:
                lines = f.readlines()
                lines = [line.strip() for line in lines]
                lines.sort()
                self.annotation_dropdown.addItems(lines)
        else:
            self.annotation_dropdown.addItem("coral")

    def add_new_group(self):
        new_group = self.group_dropdown.currentText().strip()

        if new_group and new_group != "None" and new_group not in [self.group_dropdown.itemText(i) for i in range(self.group_dropdown.count())]:
            self.group_dropdown.addItem(new_group)  # Add to dropdown
            self.group_dropdown.setCurrentText(new_group)
            self.current_group_id_label.setText(new_group)

    def get_text_from_slider_index(self, index):
        return self.strength_slider_labels[index]

    def _list_item_clicked_listener(self, item: QListWidgetItem):
        listWidget: PolygonItemWidget = self.polygon_list.itemWidget(item)
        mask = listWidget.polygon_item

        if self.selected_polygon != None:
            self.selected_polygon.set_selected(False)

        self.draw_polygon_image(mask)
        mask.set_selected(True)

        self.image_canvas.current_mask_manager = mask.get_mask_manager()
        self.selected_polygon = mask

    def add_polygon_to_polygon_list(self, mask: Polygon):
        self.draw_polygon_image(mask)
        widget = PolygonItemWidget(mask)
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.polygon_list.addItem(item)
        self.polygon_list.setItemWidget(item, widget)
        self.polygon_list.setCurrentItem(item)
        self.current_group_id_label.setText(f"Current Group ID: {mask.group_id}")

    def update_polygon_list(self, mask):
        self.draw_polygon_image(mask)
        items = self.polygon_list.selectedItems()
        if len(items) == 0:
            return
        item = items[0]
        self.polygon_list.setItemWidget(item, PolygonItemWidget(mask))
        self.current_group_id_label.setText(f"Current Group ID: {mask.group_id}")

    def remove_polygon_from_polygon_list(self, mask: Polygon):
        for index in range(self.polygon_list.count()):
            item = self.polygon_list.item(index)
            widget = self.polygon_list.itemWidget(item)
            if isinstance(widget, PolygonItemWidget) and mask.get_name() == widget.polygon_item.get_name():
                self.polygon_list.takeItem(index)
                self.clear_polygon_image()
                return
        self.current_group_id_label.setText("Current Group ID: None")

    def draw_polygon_image(self, polygon_item: Polygon):
        pixmap_size = 100
        pixmap = QPixmap(pixmap_size, pixmap_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate scaling
        bounding_rect = polygon_item.boundingRect()

        scale_factor = min(pixmap_size / bounding_rect.width(), pixmap_size / bounding_rect.height())
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        transform.translate(-bounding_rect.left(), -bounding_rect.top())

        # Apply transformation and draw polygon
        transformed_polygon = transform.map(polygon_item.polygon())
        painter.setBrush(QBrush(polygon_item.brush().color()))
        painter.setPen(polygon_item.pen())
        painter.drawPolygon(transformed_polygon)

        painter.end()

        self.polygon_image_label.setPixmap(pixmap)
        self.polygon_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def clear_polygon_image(self):
        self.polygon_image_label.clear()

    def export_image(self):
        self.export_image_event.emit()

    def move_selected_list_item(self, mask: Polygon):
        self.draw_polygon_image(mask)
        for index in range(self.polygon_list.count()):
            item = self.polygon_list.item(index)
            widget: PolygonItemWidget = self.polygon_list.itemWidget(item)

            if mask.id == widget.polygon_item.id:
                self.polygon_list.setCurrentItem(item)
                listWidget: PolygonItemWidget = self.polygon_list.itemWidget(item)
                mask = listWidget.polygon_item
                self.current_group_id_label.setText(f"Current Group ID: {mask.group_id}")
                return
