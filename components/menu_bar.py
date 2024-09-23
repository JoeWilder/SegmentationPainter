from PyQt6.QtWidgets import QMenuBar
from PyQt6.QtGui import QAction, QActionGroup, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPoint, QEvent, QObject, QBuffer, pyqtBoundSignal

from segment_agent import SegmentAgent
from utils.async_worker import AsyncWorker
from utils.checkpoint_downloader import CheckpointDownloader
from utils.mask import MaskItem
from utils.tool_mode import ToolMode
import utils.gui_utils as utils


class MenuBar(QMenuBar):
    select_image_event = pyqtSignal()
    close_canvas_event = pyqtSignal()
    save_project_event = pyqtSignal()
    load_project_event = pyqtSignal()
    export_image_event = pyqtSignal()
    export_json_event = pyqtSignal()
    export_shapefile_event = pyqtSignal()
    undo_clicked_event = pyqtSignal()
    redo_clicked_event = pyqtSignal()
    color_masks_by_type_event = pyqtSignal()
    toggle_display_bar_event = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_menu_bar()

    def _create_menu_bar(self):
        self.exit_act = QAction(utils.createIcon("exit.png"), "Quit Application", self)
        self.exit_act.setShortcut("Ctrl+Q")
        self.exit_act.triggered.connect(self.close)

        self.open_act = QAction(utils.createIcon("file_open.png"), "Open", self)
        self.open_act.setShortcut("Ctrl+O")
        self.open_act.triggered.connect(lambda: self.select_image_event.emit())

        self.close_act = QAction(utils.createIcon("close.png"), "Close", self)
        self.close_act.triggered.connect(lambda: self.close_canvas_event.emit())

        self.save_act = QAction(utils.createIcon("save.png"), "Save", self)
        self.save_act.setShortcut("Ctrl+S")
        self.save_act.triggered.connect(lambda: self.save_project_event.emit())

        self.load_act = QAction(utils.createIcon("load.png"), "Load", self)
        self.load_act.triggered.connect(lambda: self.load_project_event.emit())

        self.export_act = QAction(utils.createIcon("export.png"), "Export", self)
        self.export_act.triggered.connect(lambda: self.export_image_event.emit())

        self.export_json_act = QAction(utils.createIcon("export.png"), "Export Json data", self)
        self.export_json_act.triggered.connect(lambda: self.export_json_event.emit())

        self.export_shapefile_act = QAction(utils.createIcon("export.png"), "Export shapefile", self)
        self.export_shapefile_act.triggered.connect(lambda: self.export_shapefile_event.emit())

        self.undo_act = QAction(utils.createIcon("undo.png"), "Undo", self)
        self.undo_act.setShortcut("Ctrl+Z")
        self.undo_act.triggered.connect(lambda: self.undo_clicked_event.emit())

        self.redo_act = QAction(utils.createIcon("redo.png"), "Redo", self)
        self.redo_act.setShortcut("Ctrl+Y")
        self.redo_act.triggered.connect(lambda: self.redo_clicked_event.emit())

        self.bulk_coloring_act = QAction(utils.createIcon("palette.png"), "Color Masks by Type", self)
        self.bulk_coloring_act.triggered.connect(lambda: self.color_masks_by_type_event.emit())

        self.toggle_view_act = QAction(utils.createIcon("right_menu_open.png"), "Toggle Mask Menu", self)
        self.toggle_view_act.triggered.connect(lambda: self.toggle_display_bar_event.emit())

        file_menu = self.addMenu("File")
        file_menu.addAction(self.open_act)
        file_menu.addAction(self.close_act)
        file_menu.addAction(self.save_act)
        file_menu.addAction(self.load_act)
        file_menu.addAction(self.export_act)
        file_menu.addAction(self.export_json_act)
        file_menu.addAction(self.export_shapefile_act)
        file_menu.addSeparator()
        edit_menu = self.addMenu("Edit")
        edit_menu.addAction(self.undo_act)
        edit_menu.addAction(self.redo_act)
        edit_menu.addAction(self.bulk_coloring_act)
        view_menu = self.addMenu("View")
        view_menu.addAction(self.toggle_view_act)
