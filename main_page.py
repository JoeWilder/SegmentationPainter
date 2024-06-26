from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QColorDialog, QLayout, QToolBar, QGraphicsPolygonItem, QApplication
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import Qt

from components.image_dialog import ChooseImageDialog
from components.display_bar import DisplayBar
from components.image_canvas import ImageCanvas
from components.loading_bar import LoadingBar
from segment_agent import SegmentAgent
from utils.async_worker import AsyncWorker
from utils.tool_mode import ToolMode
from utils.mask import MaskItem
import utils.gui_utils as utils
import dill
from PIL import Image, ImageDraw
import os
import requests
import time
import qimage2ndarray


class MainPage(QMainWindow):
    """The main page of the application. This page handles creation of the top menu bar, the left tool bar.
    \nIt also creates a dialog for choosing images, loading screens, and the image canvas responsible for displaying and editing images.
    \nWindow visibility and segment agent creation is also handled here."""
    def __init__(self):
        super().__init__()
        self.image_canvas: ImageCanvas = None
        self.tool_mode = ToolMode.CREATE_MASK
        self.margin_height = 200
        self.margin_width = 400
        self.download_urls = ["https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth", 
                         "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth", 
                         "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"]
        self.initializeWindow()

    def initializeWindow(self):
        self.setMinimumSize(550, 350)
        self.setWindowTitle("Image Segmenter")
        self.setWindowIcon(utils.createIcon("app_logo.svg"))
        self.showMaximized()
        self.createMainMenuBar()
        self.createToolBar()
        self.is_loading = False

        central_widget = QWidget()
        self.central_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        container_widget = QWidget(central_widget)
        self.container_layout = QVBoxLayout(container_widget)
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.central_layout.addWidget(container_widget)

        self.download_loading_bar = LoadingBar("Downloading SAM checkpoints, please wait...")
        self.container_layout.addWidget(self.download_loading_bar)

        self.image_loading_bar = LoadingBar("Loading image, please wait...")
        self.container_layout.addWidget(self.image_loading_bar)

        self.image_saving_bar = LoadingBar("Saving, please wait...")
        self.container_layout.addWidget(self.image_saving_bar)

        # Make sure we have the checkpoints available
        if self.allCheckpointsDownloaded():
            self.beginLoadingSegmentAgent()
        else:
            os.makedirs("sam_checkpoints", exist_ok=True)
            def runnable():
                self.downloadSamCheckpoints()
            self.downloader_worker = AsyncWorker(runnable)
            self.downloader_worker.job_done.connect(self.beginLoadingSegmentAgent)
            self.downloader_worker.start()
            self.download_loading_bar.start()

    def allCheckpointsDownloaded(self):
        for url in self.download_urls:
            file_name = url.split("/")[-1]
            if not os.path.exists(os.path.join("sam_checkpoints", file_name)):
                return False
        return True
            

    def downloadSamCheckpoints(self):
        for url in self.download_urls:
            file_name = url.split("/")[-1]
            if not os.path.exists(os.path.join("sam_checkpoints", file_name)):
                r = requests.get(url, allow_redirects=True)
                open(f'sam_checkpoints/{file_name}', 'wb').write(r.content)



    def beginLoadingSegmentAgent(self):
        self.download_loading_bar.stop()
        def runnable():
            return SegmentAgent()
        self.agent_loader_worker = AsyncWorker(runnable)
        self.agent_loader_worker.job_done.connect(self.agentLoadedEvent)
        self.agent_loader_worker.start()

    def createMainMenuBar(self):
        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(False)

        self.exit_act = QAction(utils.createIcon("exit.png"), "Quit Application", self)
        self.exit_act.setShortcut("Ctrl+Q")
        self.exit_act.triggered.connect(self.close)

        self.open_act = QAction(utils.createIcon("file_open.png"), "Open", self)
        self.open_act.setShortcut("Ctrl+O")
        self.open_act.triggered.connect(self.selectImage)

        self.close_act = QAction(utils.createIcon("close.png"), "Close", self)
        self.close_act.triggered.connect(self.closeImageDisplay)

        self.save_act = QAction(utils.createIcon("save.png"), "Save", self)
        self.save_act.setShortcut("Ctrl+S")
        self.save_act.triggered.connect(self.saveProject)

        self.load_act = QAction(utils.createIcon("load.png"), "Load", self)
        self.load_act.triggered.connect(self.loadProject)

        self.export_act = QAction(utils.createIcon("export.png"), "Export", self)
        self.export_act.triggered.connect(self.saveImage)

        self.undo_act = QAction(utils.createIcon("undo.png"), "Undo", self)
        self.undo_act.setShortcut("Ctrl+Z")
        self.undo_act.triggered.connect(self.undoMask)

        self.redo_act = QAction(utils.createIcon("redo.png"), "Redo", self)
        self.redo_act.setShortcut("Ctrl+Y")
        self.redo_act.triggered.connect(self.redoMask)

        self.toggle_view_act = QAction(utils.createIcon("right_menu_open.png"), "Toggle Mask Menu", self)
        self.toggle_view_act.triggered.connect(self.toggleMaskMenu)

        file_menu = self.menu_bar.addMenu("File")
        file_menu.addAction(self.open_act)
        file_menu.addAction(self.close_act)
        file_menu.addAction(self.save_act)
        file_menu.addAction(self.load_act)
        file_menu.addAction(self.export_act)
        file_menu.addSeparator()
        edit_menu = self.menu_bar.addMenu("Edit")
        edit_menu.addAction(self.undo_act)
        edit_menu.addAction(self.redo_act)
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

    def cycleToNextTool(self):
        action: QAction
        for action in self.actions:
            if action.isChecked():
                current_index = self.actions.index(action)
                next_index = current_index + 1
                if (next_index >= len(self.actions)):
                    next_index = 0
                self.actions[next_index].setChecked(True)
                self.updateToolMode()
                
                return

    def agentLoadedEvent(self, agent: SegmentAgent):
        self.segment_agent = agent
        self.choose_image_dialog = ChooseImageDialog(self)
        self.choose_image_dialog.imageChosen.connect(self.imageSelectedEvent)
        self.choose_image_dialog.projectChosen.connect(self.projectSelected)
        self.container_layout.addWidget(self.choose_image_dialog)

    def imageSelectedEvent(self, chosen_image_path):
        if chosen_image_path != "":
            self.openImageDisplay(chosen_image_path)
            self.image_canvas.loadImage()

    def openImageDisplay(self, image_source):
        if self.image_canvas != None:
            self.image_canvas.close()
        self.choose_image_dialog.hide()
        self.image_loading_bar.start()
        self.image_canvas = ImageCanvas(image_source)
        self.image_canvas.setSegmentAgent(self.segment_agent)
        self.image_canvas.image_loaded.connect(self.imageDisplayLoadedEvent)
        

    def closeImageDisplay(self):
        if self.image_canvas == None:
            return
        self.choose_image_dialog.show()
        self.image_canvas.close()
        self.margin_height = 200
        self.margin_width = 400
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.container_layout.addWidget(self.choose_image_dialog)
        self.menu_bar.setEnabled(False)
        self.toolbar.setEnabled(False)

    def imageDisplayLoadedEvent(self):
        self.container_layout.addWidget(self.image_canvas)
        self.display_bar = DisplayBar(self.image_canvas)
        self.image_canvas.setCoordinateDisplay(self.display_bar)
        self.actions[0].setChecked(True)
        self.display_bar.right_drawer.save_signal.connect(self.saveImage)
        self.display_bar.right_drawer.mask_level_change_signal.connect(self.changeMaskLevel)
        
        self.central_layout.addWidget(self.display_bar)
        self.image_loading_bar.stop()
        self.margin_height = 50
        self.margin_width = 50
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.menu_bar.setEnabled(True)
        self.toolbar.setEnabled(True)
        self.image_canvas.tab_key_pressed.connect(self.cycleToNextTool)

        if self.is_loading:
            self.image_canvas.loadExistingPolygons(self.temporary)
            self.is_loading = False


    def changeMaskLevel(self, mask_level):
        self.segment_agent.setMaskLevel(mask_level)

    def selectImage(self):
        chosen_image_path = utils.chooseFile()
        self.imageSelectedEvent(chosen_image_path)

    def saveImage(self):
        if self.image_canvas != None:
            self.exportImage()

    def undoMask(self):
        if self.image_canvas != None:
            self.image_canvas.undoMask()

    def redoMask(self):
        if self.image_canvas != None:
            self.image_canvas.redoMask()

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.centralWidget() == None:
            return
        available_width = self.centralWidget().width()
        available_height = self.centralWidget().height()
        margin_width = min(available_width // 4, self.margin_width)
        margin_height = min(available_height // 4, self.margin_height)
        self.container_layout.setContentsMargins(margin_width, margin_height, margin_width, margin_height)

    def toggleMaskMenu(self):
        self.image_canvas.viewport_moved = True
        if self.display_bar.isVisible():
            self.display_bar.hide()
        else:
            self.display_bar.show()

    def saveProject(self):

        path = utils.saveProject()
        if path == "":
            return

        mask_managers = self.image_canvas.getAllMaskManagers()

        polygons = []

        for manager in mask_managers:
            
            if not manager.hasNothingDisplayed():
                polygons.append(manager.displayed_mask.toDictionary())



        arr = qimage2ndarray.rgb_view(self.image_canvas.image)

        project = [arr, polygons]


        with open(path, 'wb') as outp:
            dill.dump(project, outp, dill.HIGHEST_PROTOCOL)

    def projectSelected(self, path):
        with open(path, 'rb') as inp:
            project = dill.load(inp)

        self.is_loading = True
        self.temporary = project[1]

        qimage = qimage2ndarray.array2qimage(project[0])
        self.openImageDisplay(qimage)
        print(qimage)
        self.image_canvas.asyncWorkerDone(qimage)

    def loadProject(self):
        project_path = utils.chooseProject()
        if project_path == "":
            return
        
        with open(project_path, 'rb') as inp:
            project = dill.load(inp)

        self.is_loading = True
        self.temporary = project[1]
        qimage = qimage2ndarray.array2qimage(project[0])
        self.openImageDisplay(qimage)
        self.image_canvas.asyncWorkerDone(qimage)
        

    def exportImage(self):
        path = utils.saveFile()
        if path == "":
            return
        
        self.image_canvas.hide()
        self.display_bar.hide()
        self.image_saving_bar.start()
        self.margin_height = 200
        self.margin_width = 400
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.menu_bar.setEnabled(False)
        self.toolbar.setEnabled(False)
        
        def runnable():
            original_image = Image.open(self.image_canvas.image_path)
            size = self.image_canvas.image.size()
            mask_image = Image.new("RGBA", (size.width(), size.height()), (0, 0, 0, 0))
            draw = ImageDraw.Draw(mask_image)

            polygons = []
            for item in self.image_canvas.scene.items():
                if isinstance(item, QGraphicsPolygonItem):
                    polygons.append(item)

            mask: MaskItem
            for mask in polygons:
                polygon = mask.polygon()
                points = [(point.x(), point.y()) for point in polygon]
                r, g, b, a = mask.mask_color.getRgb()

                draw.polygon(points, fill=(r, g, b, a))

            if original_image.mode != 'RGBA':
                original_image = original_image.convert('RGBA')

            output_image = Image.alpha_composite(original_image, mask_image)
            output_image.save(path)
            return output_image
        
        self.image_saver_worker = AsyncWorker(runnable)
        self.image_saver_worker.setCallbackFunction(self.savingDone)
        self.image_saver_worker.start()

    def savingDone(self):
        self.margin_height = 50
        self.margin_width = 50
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.menu_bar.setEnabled(True)
        self.toolbar.setEnabled(True)
        self.image_saving_bar.stop()
        self.image_canvas.show()
        self.display_bar.show()
    