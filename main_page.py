from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QColorDialog, QLayout, QToolBar, QListWidgetItem  # fmt: skip
from PyQt6.QtGui import QAction, QActionGroup, QColor
from PyQt6.QtCore import Qt

from components.display_bar import DisplayBar
from components.image_canvas import ImageCanvas
from components.image_dialog import ChooseImageDialog
from components.loading_modal import LoadingModal
from components.color_modal import ColorModal

from segment_agent import SegmentAgent
from utils.async_worker import AsyncWorker
from utils.checkpoint_downloader import CheckpointDownloader
from utils.mask import MaskItem
from utils.tool_mode import ToolMode
import utils.gui_utils as utils


class MainPage(QMainWindow):
    """The main page of the application. This page handles creation of the top menu bar, the left tool bar.
    \nIt also creates a dialog for choosing images, loading screens, and the image canvas responsible for displaying and editing images.
    \nWindow visibility and segment agent creation is also handled here."""

    def __init__(self):
        super().__init__()
        self.margin_height: int = 200
        self.margin_width: int = 400
        self.image_canvas: ImageCanvas = None
        self.dialog = None

        self.tool_mode = ToolMode.CREATE_MASK

        self.image_canvas = ImageCanvas()
        self.image_canvas.mask_change.connect(self.maskChangeEvent)

        self.display_bar = DisplayBar(self.image_canvas)
        self.image_canvas.setCoordinateDisplay(self.display_bar)

        self.initializeWindow()

    def initializeWindow(self):
        self.setMinimumSize(550, 350)
        self.setWindowTitle("Image Segmenter")
        self.setWindowIcon(utils.createIcon("app_logo.svg"))
        self.showMaximized()

        central_widget = QWidget()
        self.central_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        container_widget = QWidget(central_widget)
        self.container_layout = QVBoxLayout(container_widget)
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.central_layout.addWidget(container_widget)

        self.createMainMenuBar()
        self.createToolBar()

        downloader = CheckpointDownloader()
        if not downloader.all_checkpoints_downloaded():
            self.showDialog("Downloading\ncheckpoints")
            downloader.checkpoints_downloaded.connect(self.loadSegmentAgent)
            downloader.download_sam_checkpoints()
        else:
            self.loadSegmentAgent()

    def createMainMenuBar(self):
        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(False)

        self.exit_act = QAction(utils.createIcon("exit.png"), "Quit Application", self)
        self.exit_act.setShortcut("Ctrl+Q")
        self.exit_act.triggered.connect(self.close)

        self.open_act = QAction(utils.createIcon("file_open.png"), "Open", self)
        self.open_act.setShortcut("Ctrl+O")
        self.open_act.triggered.connect(self.selectImageFromFileManager)

        self.close_act = QAction(utils.createIcon("close.png"), "Close", self)
        self.close_act.triggered.connect(self.closeImageDisplay)

        self.save_act = QAction(utils.createIcon("save.png"), "Save", self)
        self.save_act.setShortcut("Ctrl+S")
        self.save_act.triggered.connect(self.saveProject)

        self.load_act = QAction(utils.createIcon("load.png"), "Load", self)
        self.load_act.triggered.connect(self.loadProject)

        self.export_act = QAction(utils.createIcon("export.png"), "Export", self)
        self.export_act.triggered.connect(self.exportImage)

        self.export_json_act = QAction(utils.createIcon("export.png"), "Export Json data", self)
        self.export_json_act.triggered.connect(self.exportJson)

        self.undo_act = QAction(utils.createIcon("undo.png"), "Undo", self)
        self.undo_act.setShortcut("Ctrl+Z")
        self.undo_act.triggered.connect(self.undoButtonClicked)

        self.redo_act = QAction(utils.createIcon("redo.png"), "Redo", self)
        self.redo_act.setShortcut("Ctrl+Y")
        self.redo_act.triggered.connect(self.redoButtonClicked)

        self.bulk_coloring_act = QAction(utils.createIcon("palette.png"), "Color Masks by Type", self)
        self.bulk_coloring_act.triggered.connect(self.colorMasksByType)

        self.toggle_view_act = QAction(utils.createIcon("right_menu_open.png"), "Toggle Mask Menu", self)
        self.toggle_view_act.triggered.connect(self.toggleMaskMenu)

        file_menu = self.menu_bar.addMenu("File")
        file_menu.addAction(self.open_act)
        file_menu.addAction(self.close_act)
        file_menu.addAction(self.save_act)
        file_menu.addAction(self.load_act)
        file_menu.addAction(self.export_act)
        file_menu.addAction(self.export_json_act)
        file_menu.addSeparator()
        edit_menu = self.menu_bar.addMenu("Edit")
        edit_menu.addAction(self.undo_act)
        edit_menu.addAction(self.redo_act)
        edit_menu.addAction(self.bulk_coloring_act)
        view_menu = self.menu_bar.addMenu("View")
        view_menu.addAction(self.toggle_view_act)
        self.menu_bar.setEnabled(False)

    def createToolBar(self):
        self.toolbar = QToolBar(self)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolbar)

        tool_group = QActionGroup(self)
        tool_group.setExclusive(True)

        self.brush_action = QAction(utils.createIcon("brush.png"), "Paint masks", self)
        self.brush_action.setCheckable(True)
        self.brush_action.setChecked(True)
        self.brush_action.triggered.connect(self.updateToolMode)

        self.toolbar.addAction(self.brush_action)
        tool_group.addAction(self.brush_action)

        self.toolbar.addSeparator()

        self.eraser_action = QAction(utils.createIcon("eraser.png"), "Erase masks", self)
        self.eraser_action.setCheckable(True)
        self.eraser_action.triggered.connect(self.updateToolMode)
        self.toolbar.addAction(self.eraser_action)
        tool_group.addAction(self.eraser_action)

        self.toolbar.addSeparator()

        palette_action = QAction(utils.createIcon("palette.png"), "Change color", self)
        palette_action.triggered.connect(self.showColorDialog)
        self.toolbar.addAction(palette_action)
        self.toolbar.setMovable(False)
        self.toolbar.setEnabled(False)
        self.actions: list[QAction] = [self.brush_action, self.eraser_action]

    def showDialog(self, text):
        self.dialog = LoadingModal(self, text)
        self.dialog.start()

    def loadSegmentAgent(self):
        if self.dialog != None:
            self.dialog.stop()

        def runnable():
            return SegmentAgent()

        self.agent_loader_worker = AsyncWorker(runnable)
        self.agent_loader_worker.job_done.connect(self.segmentAgentLoaded)
        self.agent_loader_worker.start()

    def segmentAgentLoaded(self, agent: SegmentAgent):
        self.segment_agent = agent
        self.image_canvas.setSegmentAgent(self.segment_agent)
        self.choose_image_dialog = ChooseImageDialog(self)
        self.choose_image_dialog.image_chosen.connect(self.imageFileChosen)
        self.container_layout.addWidget(self.choose_image_dialog)

    def imageFileChosen(self, file_path: str):

        self.display_bar.close()
        self.image_canvas.close()
        self.choose_image_dialog.hide()
        self.container_layout.addWidget(self.image_canvas)
        self.central_layout.addWidget(self.display_bar)
        self.image_canvas.show()
        self.display_bar.show()
        self.showDialog("Loading image")

        self.margin_height = 50
        self.margin_width = 50
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)

        if file_path.lower().endswith(".sgmt"):
            self.image_canvas.loadProject(file_path)
        else:
            self.image_canvas.loadImage(file_path)
        self.image_canvas.image_loaded.connect(self.imageCanvasLoaded)

    def imageCanvasLoaded(self):
        self.dialog.stop()

        self.actions[0].setChecked(True)
        self.display_bar.right_drawer.save_signal.connect(self.exportImage)
        self.display_bar.right_drawer.mask_level_change_signal.connect(self.changeMaskLevel)

        self.margin_height = 50
        self.margin_width = 50
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.menu_bar.setEnabled(True)
        self.toolbar.setEnabled(True)
        self.image_canvas.tab_key_pressed.connect(self.cycleToNextTool)

    def selectImageFromFileManager(self):
        file_path = utils.getFilePath()
        if file_path == "":
            return
        self.imageFileChosen(file_path)

    def closeImageDisplay(self):
        if self.image_canvas == None:
            return
        self.choose_image_dialog.show()
        self.image_canvas.close()
        self.display_bar.close()
        self.margin_height = 200
        self.margin_width = 400
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.container_layout.addWidget(self.choose_image_dialog)
        self.menu_bar.setEnabled(False)
        self.toolbar.setEnabled(False)

    def saveProject(self):
        path = utils.saveProjectPath()
        if path == "":
            return
        self.showDialog("Saving Project")
        self.image_canvas.saveProject(path, self)
        self.image_canvas.project_saved.connect(self.projectFinishedSaving)

    def projectFinishedSaving(self):
        self.menu_bar.setEnabled(True)
        self.toolbar.setEnabled(True)
        self.dialog.stop()

    def loadProject(self):
        project_path = utils.getProjectPath()
        if project_path == "":
            return
        self.imageFileChosen(project_path)

    def exportImage(self):
        path = utils.saveFilePath()
        if path == "":
            return
        self.showDialog("Exporting Image")
        self.menu_bar.setEnabled(False)
        self.toolbar.setEnabled(False)
        self.image_canvas.setEnabled(False)
        self.display_bar.setEnabled(False)

        self.image_canvas.export_done.connect(self.exportFinished)
        self.image_canvas.exportAsImage(path)

    def exportJson(self):
        path = utils.saveJsonPath(self.image_canvas.image_path)
        if path == "":
            return
        # self.showDialog("Exporting json")
        # self.menu_bar.setEnabled(False)
        # self.toolbar.setEnabled(False)
        # self.image_canvas.setEnabled(False)
        # self.display_bar.setEnabled(False)

        # self.image_canvas.export_done.connect(self.exportFinished)
        self.image_canvas.exportJson(path)
        # print(path)

    def exportFinished(self):
        self.menu_bar.setEnabled(True)
        self.toolbar.setEnabled(True)
        self.image_canvas.setEnabled(True)
        self.display_bar.setEnabled(True)
        self.dialog.stop()

    def undoButtonClicked(self):
        if self.image_canvas == None:
            return
        self.image_canvas.undoMask()

    def redoButtonClicked(self):
        if self.image_canvas == None:
            return
        self.image_canvas.redoMask()

    def toggleMaskMenu(self):
        self.image_canvas.viewport_moved = True
        if self.display_bar.isVisible():
            self.display_bar.hide()
        else:
            self.display_bar.show()

    def updateToolMode(self):
        if self.image_canvas == None:
            return
        if self.brush_action.isChecked():
            self.image_canvas.setToolMode(ToolMode.CREATE_MASK)
        else:
            self.image_canvas.setToolMode(ToolMode.ERASE_MASK)

    def showColorDialog(self):
        dialog = QColorDialog(self)
        dialog.setWindowTitle("Select Mask Color")
        dialog.setOptions(QColorDialog.ColorDialogOption.ShowAlphaChannel | QColorDialog.ColorDialogOption.DontUseNativeDialog)
        dialog.setModal(True)
        dialog.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        dialog.setMinimumSize(700, 450)
        dialog.setCurrentColor(self.image_canvas.getMaskColor())

        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            color = dialog.selectedColor()
            if color.isValid():
                self.mask_color = color
                if self.image_canvas != None:
                    self.image_canvas.setMaskColor(color)

    def colorMasksByType(self):
        mask_list = self.display_bar.right_drawer.mask_list
        unique_types = []
        for i in range(mask_list.count()):
            mask_type = mask_list.itemWidget(mask_list.item(i)).mask_item.getDisplayName()
            if mask_type not in unique_types:
                unique_types.append(mask_type)

        color_modal = ColorModal(self, unique_types)
        color_modal.apply_color_signal.connect(self.applyMaskTypeColoring)
        color_modal.setSelectedColor(self.image_canvas.getMaskColor())
        color_modal.start()

    def applyMaskTypeColoring(self, mask_class: str, color: QColor):
        for manager in self.image_canvas.mask_managers:
            if mask_class == manager.getCurrentlyDisplayedMask().getDisplayName():
                manager.getCurrentlyDisplayedMask().setColor(color)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.centralWidget() == None:
            return
        available_width = self.centralWidget().width()
        available_height = self.centralWidget().height()
        margin_width = min(available_width // 4, self.margin_width)
        margin_height = min(available_height // 4, self.margin_height)
        self.container_layout.setContentsMargins(margin_width, margin_height, margin_width, margin_height)

    def cycleToNextTool(self):
        action: QAction
        for action in self.actions:
            if action.isChecked():
                current_index = self.actions.index(action)
                next_index = current_index + 1
                if next_index >= len(self.actions):
                    next_index = 0
                self.actions[next_index].setChecked(True)
                self.updateToolMode()
                return

    def changeMaskLevel(self, mask_level):
        self.segment_agent.set_mask_level(mask_level)

    def maskChangeEvent(self, mask: MaskItem):
        pass
