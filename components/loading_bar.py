from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel, QGraphicsOpacityEffect  # fmt: skip
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve


class LoadingBar(QWidget):
    """A window with a loading bar"""

    def __init__(self, text=None):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(
            """LoadingBar{background-color: rgba(235, 235, 235, 150); border-radius: 15px; padding: 100px;}"""
        )

        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""QLabel{font-size: 20px; color: #333333;}""")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #8f8f91;
                border-radius: 5px;
                text-align: center;
                margin-top: 25px;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
                width: 20px;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        self.hide()

    def start(self):
        self.show()
        self.animation = QPropertyAnimation(self, b"size")
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(500)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.opacity_animation.start()

    def stop(self):
        self.hide()
