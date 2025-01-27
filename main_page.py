from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QColorDialog, QLayout
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtCore import Qt

from components.display_bar import DisplayBar
from components.image_canvas import ImageCanvas
from components.image_dialog import ChooseImageDialog
from components.loading_modal import LoadingModal
from components.color_modal import ColorModal
from components.menu_bar import MenuBar
from components.tool_bar import ToolBar

from segment_agent import SegmentAgent
from utils.async_worker import AsyncWorker
from utils.checkpoint_downloader import CheckpointDownloader
from utils.tool_mode import ToolMode
import utils.gui_utils as utils


class MainPage(QMainWindow):
    """The main page of the application. This page handles creation of the top menu bar and the left tool bar.
    \nIt also creates a dialog for choosing images, handles loading screens, and manages the image canvas responsible for displaying and editing images.
    \nWindow visibility and segment agent creation is also handled here."""

    def __init__(self):
        super().__init__()
        self.margin_height: int = 200
        self.margin_width: int = 400
        self.dialog: LoadingModal = None
        self.tool_mode: ToolMode = ToolMode.CREATE_MASK
        self.image_canvas = ImageCanvas()
        self.display_bar = DisplayBar(self.image_canvas)
        self.image_canvas.set_coord_display(self.display_bar)

        self.display_bar.right_drawer.save_signal.connect(self.export_image)
        self.display_bar.right_drawer.mask_level_change_signal.connect(self.change_mask_level)
        self.image_canvas.tab_key_pressed.connect(self.cycle_tool)

        self._create_window()

    def _create_window(self):
        """Create a blank window and begins loading the rest of the project"""
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

        self.menu_bar = self._create_menu_bar()
        self.tool_bar = self._create_tool_bar()
        self.actions: list[QAction] = self.tool_bar.get_actions()

        downloader = CheckpointDownloader()
        if not downloader.all_checkpoints_downloaded():
            self.show_loading_modal("Downloading\ncheckpoints")
            downloader.checkpoints_downloaded.connect(self._load_segment_agent)
            downloader.download_sam_checkpoints()
        else:
            self._load_segment_agent()

    def _create_menu_bar(self):
        """Create the menu bar at the top of the UI"""
        menu_bar = MenuBar(self)
        self.setMenuBar(menu_bar)
        menu_bar.setEnabled(False)
        menu_bar.select_image_event.connect(self.select_image)
        menu_bar.close_canvas_event.connect(self.close_image_canvas)
        menu_bar.save_project_event.connect(self.save_project)
        menu_bar.load_project_event.connect(self.load_project)
        menu_bar.export_image_event.connect(self.export_image)
        menu_bar.export_json_event.connect(self.export_json)
        menu_bar.export_shapefile_event.connect(self.export_shapefile)
        menu_bar.undo_clicked_event.connect(self.undo_clicked)
        menu_bar.redo_clicked_event.connect(self.redo_clicked)
        menu_bar.color_masks_by_type_event.connect(self.color_masks_by_type)
        menu_bar.toggle_display_bar_event.connect(self.toggle_display_bar)
        return menu_bar

    def _create_tool_bar(self):
        """Create the tool bar on the left of the UI"""
        tool_bar = ToolBar(self)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tool_bar)
        tool_bar.setEnabled(False)
        tool_bar.tool_switch_event.connect(self.update_tool_mode)
        tool_bar.palette_event.connect(self.show_color_dialog)
        return tool_bar

    def show_loading_modal(self, text: str):
        """Displays a loading modal"""
        self.dialog = LoadingModal(self, text)
        self.dialog.start()

    def _load_segment_agent(self):
        """Load SAM asyncronously"""
        if self.dialog != None:
            self.dialog.stop()

        def runnable():
            return SegmentAgent()

        self.agent_loader_worker = AsyncWorker(runnable)
        self.agent_loader_worker.job_done.connect(self._segment_agent_loaded)
        self.agent_loader_worker.start()

    def _segment_agent_loaded(self, agent: SegmentAgent):
        """Callback that is fired when SAM finishes loading"""
        self.segment_agent = agent
        self.image_canvas.set_segment_agent(self.segment_agent)
        self.choose_image_dialog = ChooseImageDialog(self)
        self.choose_image_dialog.image_chosen.connect(self.load_file)
        self.container_layout.addWidget(self.choose_image_dialog)

    def load_file(self, file_path: str):
        """Load the given file into the image canvas"""
        self.display_bar.close()
        self.image_canvas.close()
        self.choose_image_dialog.hide()
        self.container_layout.addWidget(self.image_canvas)
        self.central_layout.addWidget(self.display_bar)
        self.image_canvas.show()
        self.display_bar.show()
        self.show_loading_modal("Loading image")

        self.margin_height = 50
        self.margin_width = 50
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)

        if file_path.lower().endswith(".sgmt"):
            self.image_canvas.load_project(file_path)
        else:
            self.image_canvas.load_image(file_path)
        self.image_canvas.image_loaded.connect(self._image_canvas_loaded)

    def _image_canvas_loaded(self):
        """Callback that is fired when the image canvas loads the given file"""
        self.dialog.stop()

        self.actions[0].setChecked(True)

        self.margin_height = 50
        self.margin_width = 50
        self.container_layout.setContentsMargins(self.margin_width, self.margin_height, self.margin_width, self.margin_height)
        self.menu_bar.setEnabled(True)
        self.tool_bar.setEnabled(True)

    def select_image(self):
        """Called from the menu bar. Selects and loads an image into the image canvas"""
        file_path = utils.get_file_path()
        if file_path == "":
            return
        self.load_file(file_path)

    def close_image_canvas(self):
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
        self.tool_bar.setEnabled(False)

    def save_project(self):
        """Save the image and its masks into a .sgmt file"""
        path = utils.save_project_path()
        if path == "":
            return
        self.show_loading_modal("Saving Project")
        self.image_canvas.save_project(path, self)
        self.image_canvas.project_saved.connect(self._project_finished_saving)

    def _project_finished_saving(self):
        """Callback that is fired when a project finishes saving"""
        self.menu_bar.setEnabled(True)
        self.tool_bar.setEnabled(True)
        self.dialog.stop()

    def load_project(self):
        """Load a .sgmt file"""
        project_path = utils.get_project_path()
        if project_path == "":
            return
        self.load_file(project_path)

    def export_image(self):
        """Export the image and the drawn masks to an image file"""
        path = utils.save_file_path()
        if path == "":
            return
        self.show_loading_modal("Exporting Image")
        self.menu_bar.setEnabled(False)
        self.tool_bar.setEnabled(False)
        self.image_canvas.setEnabled(False)
        self.display_bar.setEnabled(False)

        self.image_canvas.export_done.connect(self._export_finished)
        self.image_canvas.export_as_image(path)

    def export_json(self):
        """Export the image and the drawn masks to json"""
        image_path = "sam" if self.image_canvas.image_path is None else self.image_canvas.image_path
        path = utils.save_json_path(image_path)
        if path == "":
            return
        self.image_canvas.export_json(path)

    def export_shapefile(self):
        """Export the drawn masks to a shapefile"""
        path = utils.save_shapefile_path()
        if path == "":
            return
        self.image_canvas.export_shapefile(path)

    def _export_finished(self):
        """Callback that is fired when an export is finished"""
        self.menu_bar.setEnabled(True)
        self.tool_bar.setEnabled(True)
        self.image_canvas.setEnabled(True)
        self.display_bar.setEnabled(True)
        self.dialog.stop()

    def undo_clicked(self):
        if self.image_canvas == None:
            return
        self.image_canvas.undo_mask()

    def redo_clicked(self):
        if self.image_canvas == None:
            return
        self.image_canvas.redo_mask()

    def toggle_display_bar(self):
        self.image_canvas.viewport_moved = True
        if self.display_bar.isVisible():
            self.display_bar.hide()
        else:
            self.display_bar.show()

    def update_tool_mode(self):
        if self.image_canvas == None:
            return
        if self.tool_bar.brush_action.isChecked():
            self.image_canvas.set_tool_mode(ToolMode.CREATE_MASK)
        else:
            self.image_canvas.set_tool_mode(ToolMode.ERASE_MASK)

    def show_color_dialog(self):
        dialog = QColorDialog(self)
        dialog.setWindowTitle("Select Mask Color")
        dialog.setOptions(QColorDialog.ColorDialogOption.ShowAlphaChannel | QColorDialog.ColorDialogOption.DontUseNativeDialog)
        dialog.setModal(True)
        dialog.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        dialog.setMinimumSize(700, 450)
        dialog.setCurrentColor(self.image_canvas.get_mask_color())

        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            color = dialog.selectedColor()
            if color.isValid():
                self.mask_color = color
                if self.image_canvas != None:
                    self.image_canvas.set_mask_color(color)

    def color_masks_by_type(self):
        mask_list = self.display_bar.right_drawer.mask_list
        unique_types = []
        for i in range(mask_list.count()):
            mask_type = mask_list.itemWidget(mask_list.item(i)).mask_item.get_display_name()
            if mask_type not in unique_types:
                unique_types.append(mask_type)

        color_modal = ColorModal(self, unique_types)
        color_modal.apply_color_signal.connect(self.apply_mask_type_coloring)
        color_modal.setSelectedColor(self.image_canvas.get_mask_color())
        color_modal.start()

    def apply_mask_type_coloring(self, mask_class: str, color: QColor):
        for manager in self.image_canvas.mask_managers:
            if mask_class == manager.getCurrentlyDisplayedMask().get_display_name():
                manager.getCurrentlyDisplayedMask().set_color(color)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.centralWidget() == None:
            return
        available_width = self.centralWidget().width()
        available_height = self.centralWidget().height()
        margin_width = min(available_width // 4, self.margin_width)
        margin_height = min(available_height // 4, self.margin_height)
        self.container_layout.setContentsMargins(margin_width, margin_height, margin_width, margin_height)

    def cycle_tool(self):
        action: QAction
        for action in self.actions:
            if action.isChecked():
                current_index = self.actions.index(action)
                next_index = current_index + 1
                if next_index >= len(self.actions):
                    next_index = 0
                self.actions[next_index].setChecked(True)
                self.update_tool_mode()
                return

    def change_mask_level(self, mask_level):
        self.segment_agent.set_mask_level(mask_level)
