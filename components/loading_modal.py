from PyQt6 import QtCore, QtWidgets, QtGui
from components.loading_spinner import WaitingSpinner


class LoginPopup(QtWidgets.QWidget):
    def __init__(self, parent, text=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground)
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            """
            LoginPopup {
                background: rgba(0, 0, 0, 200);
            }
            QWidget#container {
                border-radius: 4px;
                background: rgba(235, 235, 235, 200)
            }
            QLabel {
                padding: 0px;
            }
        """
        )

        fullLayout = QtWidgets.QVBoxLayout(self)

        self.container = QtWidgets.QWidget(objectName="container")
        fullLayout.addWidget(
            self.container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        component_container = QtWidgets.QWidget()

        self.container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        layout.addWidget(
            component_container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        base_layout = QtWidgets.QVBoxLayout(component_container)

        self.text = text

        self.title = QtWidgets.QLabel(text, objectName="title")
        self.title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        base_layout.addWidget(self.title)

        self.spinner = WaitingSpinner(
            parent,
            roundness=100.0,
            fade=80.0,
            radius=30,
            lines=70,
            line_length=18,
            line_width=7,
            speed=0.57,
            color=QtGui.QColor("#05B8CC"),
        )

        spinner_container = QtWidgets.QWidget()
        spinner_layout = QtWidgets.QVBoxLayout(spinner_container)
        spinner_layout.addWidget(
            self.spinner, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        base_layout.addWidget(
            spinner_container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.spinner.start()

        parent.installEventFilter(self)

        self.loop = QtCore.QEventLoop(self)

    def resizeEvent(self, event):
        self.container.setMinimumSize(self.width() // 2, self.height() // 2)
        self.adjustLabelFontSize()

    def adjustLabelFontSize(self):
        font = self.title.font()
        font.setPointSize(self.height() // 20)
        self.title.setFont(font)

        size = min(self.container.width(), self.container.height()) // 4
        self.spinner.setMaximumSize(size, size)

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
