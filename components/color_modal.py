from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QColorDialog, QLayout, QToolBar, QSizePolicy, QLabel, QLineEdit, QPushButton, QComboBox
from PyQt6.QtGui import QAction, QActionGroup, QColor
from PyQt6.QtCore import Qt, QEventLoop, pyqtSignal


class ColorModal(QWidget):

    apply_color_signal = pyqtSignal(str, QColor)

    def __init__(self, parent, options=[]):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            """
            ColorModal {
                background: rgba(0, 0, 0, 200);
            }
            QWidget#container {
                border-radius: 4px;
                background: rgba(235, 235, 235, 200);
            }
            QLabel {
                padding: 0px;
            }
            QWidget#test_widget {
                background-color: white;
                border-radius: 15px;
                border: 1px solid #dcdcdc;
                padding: 10px;
            }
            QLabel#title {
                font-size: 16px;
                color: #333333;
            }
            QLineEdit {
                background-color: #eff6f5;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton#apply_button {
                border: 2px solid #007BFF;
                border-radius: 15px;
                padding: 10px 20px;
                color: #007BFF;
                font-weight: bold;
            }
            QPushButton#apply_button:hover {
                background-color: #fafafa;
            }
            QPushButton#cancel_button {
                border: 2px solid;
                border-radius: 15px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton#cancel_button:hover {
                background-color: #fafafa;
            }
            QComboBox {
                background-color: #eff6f5;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
        """
        )

        fullLayout = QVBoxLayout(self)

        self.container = QWidget(objectName="container")
        fullLayout.addWidget(self.container, alignment=Qt.AlignmentFlag.AlignCenter)
        self.container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        component_container = QWidget()

        self.container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(component_container, alignment=Qt.AlignmentFlag.AlignCenter)

        base_layout = QVBoxLayout(component_container)

        self.dialog = QColorDialog(self)
        self.dialog.setWindowTitle("Select Mask Color")
        self.dialog.setOptions(QColorDialog.ColorDialogOption.ShowAlphaChannel | QColorDialog.ColorDialogOption.NoButtons)
        self.dialog.setModal(True)
        self.dialog.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.dialog.setMinimumSize(700, 450)

        base_layout.addWidget(self.dialog)

        test_widget = QWidget(objectName="test_widget")
        test_widget.setFixedHeight(75)
        test_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        base_layout.addWidget(test_widget)
        base_layout.setContentsMargins(10, 10, 10, 10)

        test_layout = QHBoxLayout(test_widget)
        test_layout.setSpacing(10)

        self.title = QLabel("Pick a color...", objectName="title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        test_layout.addWidget(self.title)

        self.combo_box = QComboBox(self)
        self.combo_box.setEditable(True)
        self.combo_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if options:
            self.combo_box.addItems(options)
        test_layout.addWidget(self.combo_box)

        button_layout = QHBoxLayout()

        apply_button = QPushButton("Apply Color", objectName="apply_button")
        apply_button.clicked.connect(self.buttonPressed)
        apply_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        apply_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(apply_button)

        cancel_button = QPushButton("Cancel", objectName="cancel_button")
        cancel_button.clicked.connect(self.cancelPressed)
        cancel_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(cancel_button)

        base_layout.addLayout(button_layout)

        parent.installEventFilter(self)

        self.loop = QEventLoop(self)

        parent.installEventFilter(self)

        self.loop = QEventLoop(self)

    def setSelectedColor(self, selected_color: QColor):
        self.dialog.setCurrentColor(selected_color)

    def buttonPressed(self):
        self.apply_color_signal.emit(self.combo_box.currentText(), self.dialog.currentColor())
        self.stop()

    def cancelPressed(self):
        self.stop()

    def resizeEvent(self, event):
        self.container.setMinimumSize(self.width() // 2, self.height() // 2)
        self.adjustLabelFontSize()

    def adjustLabelFontSize(self):
        size = min(self.container.width(), self.container.height()) // 4

    def showEvent(self, event):
        self.setGeometry(self.parent().rect())
        self.container.setMinimumSize(self.width() // 2, self.height() // 2)
        self.adjustLabelFontSize()

    def eventFilter(self, source, event):
        if event.type() == event.Type.Resize:
            self.setGeometry(source.rect())
            self.container.setMinimumSize(self.width() // 2, self.height() // 2)
            self.adjustLabelFontSize()
        return super().eventFilter(source, event)

    def exec(self):
        self.show()
        self.raise_()
        res = self.loop.exec()
        self.hide()
        return res

    def start(self):
        self.show()

    def stop(self):
        self.hide()
