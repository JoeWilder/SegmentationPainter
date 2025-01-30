from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDragLeaveEvent, QDropEvent
import utils.gui_utils


class ChooseImageDialog(QWidget):
    """A window that prompts the user to select an image"""

    image_chosen = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self.common_style = """
            ChooseImageDialog {
                border: 3px dotted gray;
                border-style: dashed;
                border-radius: 10px;
            }
            QLabel {
                font-size: 24px;
                color: #333;
            }
            QLabel#label1 {
                font-size: 32px;
            }
            QPushButton {
                font-size: 24px;
                border: 2px solid #007BFF;
                border-radius: 15px;
                padding: 10px 20px;
                color: #007BFF;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #fafafa;
            }
        """

        self.setStyleSheet(self.common_style)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(self)
        pixmap = QPixmap("./assets/icons/upload_file.png")
        icon_label.setPixmap(pixmap.scaledToWidth(100))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label1 = QLabel("Drag Image/GeoTIFF Here")
        label1.setObjectName("label1")
        label1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label2 = QLabel("or")
        label2.setObjectName("label2")
        label2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button = QPushButton("Browse Files")
        button.clicked.connect(self.selectImage)

        layout.addWidget(icon_label)
        layout.addWidget(label1)
        layout.addWidget(label2)
        layout.addWidget(button)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(self.common_style + "ChooseImageDialog { background-color: #dbdbdb; }")
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.setStyleSheet(self.common_style)
        event.accept()

    def dropEvent(self, event: QDropEvent):
        chosenFiles = event.mimeData().urls()
        if len(chosenFiles) > 1:
            self.setStyleSheet(self.common_style)
            return
        path = chosenFiles[0].toLocalFile()
        if path == "":
            event.ignore()
        self.setStyleSheet(self.common_style)
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
            self.image_chosen.emit(path)
            event.accept()
        else:
            event.ignore()

    def selectImage(self):
        path = utils.gui_utils.get_file_path()
        if path == "":
            return
        self.image_chosen.emit(path)
