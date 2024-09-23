from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QScrollArea, QListWidget, QListWidgetItem, QSlider, QLineEdit, QSizePolicy , QHBoxLayout  # fmt: skip
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QTransform
from utils.mask import MaskItem
from utils.slider_action import SliderAction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from components.image_canvas import ImageCanvas


class DisplayBar(QWidget):
    def __init__(self, image_display):
        super().__init__()
        self.image_display = image_display
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        self.right_drawer = RightDrawer(self.image_display)
        layout.addWidget(self.right_drawer)
        layout.addStretch()
        self.windowtest = CoordinateDisplayWindow(self)
        layout.addWidget(self.windowtest)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def getRightDrawer(self):
        return self.right_drawer

    def getCoordinateDisplayWindow(self):
        return self.windowtest

    def close(self):
        self.hide()
        self.right_drawer.mask_list.clear()
        self.right_drawer.image_label.clear()
        self.right_drawer.selected_widget = None

    def getAnnotationLabel(self):
        return self.right_drawer.text_box.text()


class MaskItemWidget(QWidget):
    def __init__(self, mask_item: MaskItem, parent=None):
        super().__init__(parent)
        self.mask_item = mask_item

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(self.mask_item.get_display_name())
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        self.label.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.line_edit = QLineEdit(self)
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setVisible(False)
        self.layout.addWidget(self.line_edit)

        self.setLayout(self.layout)

        self.label.mouseDoubleClickEvent = self.startEditing
        self.line_edit.editingFinished.connect(self.finishEditing)

    def startEditing(self, event):
        self.label.setVisible(False)
        self.line_edit.setText(self.label.text())
        self.line_edit.setVisible(True)
        self.line_edit.setFocus()

    def finishEditing(self):
        new_name = self.line_edit.text()
        self.mask_item.set_display_name(new_name)
        self.label.setText(new_name)
        self.line_edit.setVisible(False)
        self.label.setVisible(True)


class RightDrawer(QWidget):
    save_signal = pyqtSignal()
    mask_level_change_signal = pyqtSignal(SliderAction)

    def __init__(self, image_canvas):
        self.image_canvas: ImageCanvas = image_canvas
        super().__init__()
        self.mask_action = SliderAction.AUTO
        self.selected_widget = None
        self.lastMaskManager = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("RightDrawer {border: 2px solid rgb(225, 225, 225); border-radius: 15px;}")

        self.image_label = QLabel()
        self.image_label.setMinimumHeight(100)
        layout.addWidget(self.image_label)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.label1 = QLabel("Current Mask")
        self.label1.setObjectName("myLabel1")
        self.label1.setStyleSheet(
            """
            #myLabel1 {
                font-size: 16px;
                font-weight: bold;
            }
        """
        )
        self.label1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumWidth(200)
        layout.addWidget(scroll_area, alignment=Qt.AlignmentFlag.AlignRight)

        self.mask_list = QListWidget()

        self.mask_list.itemPressed.connect(self.itemClickedEvent)

        scroll_area.setWidget(self.mask_list)

        text_layout = QVBoxLayout()
        text_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.text_box_label = QLabel("Annotation Label")
        self.text_box_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_box_label.setObjectName("myLabel3")
        self.text_box_label.setStyleSheet(
            """
            #myLabel3 {
                margin-top: 20px;
                font-size: 16px;
                font-weight: bold;
            }
        """
        )
        text_layout.addWidget(self.text_box_label)

        self.text_box = QLineEdit(self)
        self.text_box.setPlaceholderText("Enter label here...")
        self.text_box.setMaximumWidth(300)
        self.text_box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        text_layout.addWidget(self.text_box)

        layout.addLayout(text_layout)

        self.label2 = QLabel("Mask Level")
        self.label2.setObjectName("myLabel2")
        self.label2.setStyleSheet(
            """
            #myLabel2 {
                margin-top: 40px;
                font-size: 16px;
                font-weight: bold;
            }
        """
        )
        self.label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label2)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(3)
        self.slider.setTickInterval(1)
        self.slider.setTracking(False)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.valueChanged.connect(self.sliderValueChanged)

        self.slider.setMinimumWidth(150)

        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignCenter)

        self.label3 = QLabel("Best Mask")
        self.label3.setObjectName("myLabel3")
        self.label3.setStyleSheet(
            """
            #myLabel3 {
                color: gray;
            }
        """
        )
        self.label3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label3)

        button = QPushButton("Export Image")
        button.setMinimumSize(75, 35)
        button.clicked.connect(self.saveFile)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(button)

        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        button.setStyleSheet(
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

    def sliderValueChanged(self, index):
        action = SliderAction.fromValue(index)
        self.mask_level = action
        self.mask_level_change_signal.emit(action)
        self.label3.setText(self.getTextFromSliderIndex(index))

    def getTextFromSliderIndex(self, index):
        texts = ["Best Mask", "Weakest", "Medium", "Strongest"]
        return texts[index]

    def itemClickedEvent(self, item: QListWidgetItem):
        listWidget: MaskItemWidget = self.mask_list.itemWidget(item)
        mask = listWidget.mask_item

        if self.selected_widget != None:
            self.selected_widget.set_selected(False)

        self.displayPolygonImage(mask)
        mask.set_selected(True)

        self.image_canvas.current_mask_manager = mask.get_mask_manager()
        self.selected_widget = mask

    def addMask(self, mask: MaskItem):
        self.displayPolygonImage(mask)
        widget = MaskItemWidget(mask)
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.mask_list.addItem(item)
        self.mask_list.setItemWidget(item, widget)
        self.mask_list.setCurrentItem(item)

    def updateMask(self, mask):
        self.displayPolygonImage(mask)
        items = self.mask_list.selectedItems()
        if len(items) == 0:
            return
        item = items[0]
        self.mask_list.setItemWidget(item, MaskItemWidget(mask))

    def removeMask(self, mask: MaskItem):
        for index in range(self.mask_list.count()):
            item = self.mask_list.item(index)
            widget = self.mask_list.itemWidget(item)
            if isinstance(widget, MaskItemWidget) and mask.get_name() == widget.mask_item.get_name():
                self.mask_list.takeItem(index)
                self.clearPolygonImage()
                return

    def displayPolygonImage(self, polygon_item: MaskItem):
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

        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def clearPolygonImage(self):
        self.image_label.clear()

    def saveFile(self):
        self.save_signal.emit()

    def moveToMask(self, mask: MaskItem):
        self.displayPolygonImage(mask)
        for index in range(self.mask_list.count()):
            item = self.mask_list.item(index)
            widget: MaskItemWidget = self.mask_list.itemWidget(item)
            if mask.get_name() == widget.mask_item.get_name():
                self.mask_list.setCurrentItem(item)
                return


class CoordinateDisplayWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("CoordinateDisplayWindow {border: 2px solid rgb(225, 225, 225); border-radius: 15px;}")

        self.label1 = QLabel("x: - y: -")
        self.label1.setObjectName("label1")
        self.label1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setMinimumSize(150, 75)

        layout.addWidget(self.label1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def updateCoordinates(self, x, y):
        self.x = x
        self.y = y
        self.label1.setText(f"x: {x} y: {y}")

    def getCoordinates(self):

        return QPoint(self.x, self.y)
