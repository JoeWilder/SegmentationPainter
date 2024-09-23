from PyQt6.QtWidgets import QToolBar
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPoint, QEvent, QObject, QBuffer, pyqtBoundSignal

import utils.gui_utils as utils


class ToolBar(QToolBar):
    tool_switch_event = pyqtSignal()
    palette_event = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_tool_bar()

    def _create_tool_bar(self):
        tool_group = QActionGroup(self)
        tool_group.setExclusive(True)

        self.brush_action = QAction(utils.createIcon("brush.png"), "Paint masks", self)
        self.brush_action.setCheckable(True)
        self.brush_action.setChecked(True)
        self.brush_action.triggered.connect(lambda: self.tool_switch_event.emit())

        self.addAction(self.brush_action)
        tool_group.addAction(self.brush_action)

        self.addSeparator()

        self.eraser_action = QAction(utils.createIcon("eraser.png"), "Erase masks", self)
        self.eraser_action.setCheckable(True)
        self.eraser_action.triggered.connect(lambda: self.tool_switch_event.emit())
        self.addAction(self.eraser_action)
        tool_group.addAction(self.eraser_action)

        self.addSeparator()

        palette_action = QAction(utils.createIcon("palette.png"), "Change color", self)
        palette_action.triggered.connect(lambda: self.palette_event.emit())
        self.addAction(palette_action)
        self.setMovable(False)

    def get_actions(self) -> list[QAction]:
        return [self.brush_action, self.eraser_action]
