from PyQt6.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QVBoxLayout, QGraphicsPolygonItem, QApplication, QMainWindow  # fmt: skip
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QColor, QImageReader, QKeyEvent, QCursor, QMouseEvent, QWheelEvent, QDragLeaveEvent  # fmt: skip
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPoint, QEvent, QObject, QBuffer, pyqtBoundSignal  # fmt: skip

from components.display_bar import DisplayBar

import qimage2ndarray
from typing import TypedDict, List, Tuple
import pickle
from PIL import Image, ImageDraw, ExifTags
import io
import json
from datetime import datetime

from utils.async_worker import AsyncWorker
from utils.tool_mode import ToolMode
from utils.mask import MaskItem
from segment_agent import SegmentAgent
from utils.mask_manager import MaskManager


Image.MAX_IMAGE_PIXELS = None


class ImageCanvas(QGraphicsView):
    """Used to display and edit an image"""

    image_loaded: pyqtBoundSignal = pyqtSignal()
    tab_key_pressed = pyqtSignal()
    project_saved = pyqtSignal()
    export_done = pyqtSignal()
    mask_change = pyqtSignal(MaskItem)

    def __init__(self):
        super().__init__()

        self.display_bar = None

        self.tool_mode = ToolMode.CREATE_MASK
        self.mask_color = QColor(30, 144, 255, 75)
        self.mouse_position_x = "-"
        self.mouse_position_y = "-"
        self.masks = []
        self.mask_id = 1
        self.loaded_mask_ids = []
        self.viewport_moved = True
        self.setStyleSheet("""ImageCanvas { border: 3px solid rgb(230, 230, 230);}""")
        self.middle_mouse_button_pressed = False
        self.zoom_factor_base = 1.1
        self.zoom_level = 1.0
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.scene: QGraphicsScene = QGraphicsScene(self)
        self.scene.installEventFilter(self)
        self.setScene(self.scene)
        QImageReader.setAllocationLimit(0)
        self.widget = QWidget()
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self)
        self.widget.setLayout(self.vbox)

        self.mask_managers = []
        self.current_mask_manager = None

        self.image_path = None

    def loadImage(self, file_path: str):
        self.image_path = file_path

        def runnable():
            image: Image.Image = Image.open(file_path)
            image = self.rotateImageByExifTag(image)
            image = image.convert("RGBA")
            qimage = QImage(image.tobytes("raw", "RGBA"), image.size[0], image.size[1], QImage.Format.Format_RGBA8888)
            return qimage

        self.image_loader_worker = AsyncWorker(runnable)
        self.image_loader_worker.setCallbackFunction(self.asyncWorkerDone)
        self.image_loader_worker.start()

    def loadProject(self, project_path: str):
        self.image_path = None

        def runnable():
            with open(project_path, "rb") as inp:
                project = pickle.load(inp)
            qimage = qimage2ndarray.array2qimage(project[0])
            polygons: list[dict] = project[1]
            return qimage, polygons

        self.project_loader_worker = AsyncWorker(runnable)
        self.project_loader_worker.setCallbackFunction(self.projectLoaded)
        self.project_loader_worker.start()

    def projectLoaded(self, project_properties: Tuple[QImage, List[dict[str, QColor, List[Tuple[float, float]]]]]):
        self.loadExistingPolygons(project_properties[1])
        self.asyncWorkerDone(project_properties[0])

    def asyncWorkerDone(self, image: QImage):
        self.image: QImage = image
        self.pixmap = QPixmap.fromImage(image)
        self.image_item = self.scene.addPixmap(self.pixmap)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.fitInView(self.image_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.image_loaded.emit()

    def captureScreenshot(self):
        area = self.viewport().rect()
        image = QImage(area.size(), QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        visible_area = QRectF(image.rect())
        self.render(painter, visible_area, area)
        painter.end()
        array = qimage2ndarray.rgb_view(image)
        return array

    def undoMask(self):
        if self.current_mask_manager == None:
            return
        self.current_mask_manager.displayPreviousMaskItem(self.display_bar)

    def redoMask(self):
        if self.current_mask_manager == None:
            return
        self.current_mask_manager.displayNextMaskItem(self.display_bar)

    def mousePressEvent(self, event: QMouseEvent):

        if not self.isPointInEditableArea(event.pos()):
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self.middle_mouse_button_pressed = True
            self.last_scroll_position = event.pos()
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton or event.button() == Qt.MouseButton.RightButton:

            # Create a mask through clicking. Points are created with left click, negative points are created with right click
            if self.tool_mode == ToolMode.CREATE_MASK:

                # If clicking on an existing polygon, select it and take no further action
                if event.button() == Qt.MouseButton.LeftButton:
                    point = self.mapToScene(event.pos())
                    items = self.scene.items(point)
                    for item in items:
                        if isinstance(item, MaskItem):
                            if self.current_mask_manager != None:
                                self.current_mask_manager.unselectCurrentMask()
                            self.current_mask_manager = item.getMaskManager()
                            item.setSelected(True)
                            self.display_bar.getRightDrawer().moveToMask(item)
                            return

                # If right-clicking without holding control, do nothing
                if event.button() == Qt.MouseButton.RightButton and QApplication.keyboardModifiers() != Qt.KeyboardModifier.ControlModifier:
                    return

                polarity = None

                # If control is held down, append the clicked point to the clicked points list
                if QApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
                    # Ensure we have a current mask manager to append points to
                    if self.current_mask_manager is None or self.current_mask_manager.hasNothingDisplayed():
                        return

                    if event.button() == Qt.MouseButton.LeftButton:
                        polarity = 1
                    elif event.button() == Qt.MouseButton.RightButton:
                        polarity = 0

                else:
                    # Start a new polygon if control is not held down
                    if self.current_mask_manager is not None:
                        self.current_mask_manager.unselectCurrentMask()

                    mask_name = f"mask{self.mask_id}"

                    while mask_name in self.loaded_mask_ids:
                        self.mask_id += 1
                        mask_name = f"mask{self.mask_id}"

                    self.current_mask_manager = MaskManager(mask_name)
                    self.current_mask_manager.setGraphicsView(self)
                    self.mask_id += 1
                    self.mask_managers.append(self.current_mask_manager)
                    polarity = 1

                if self.viewport_moved:
                    self.updateCurrentImage()

                unique_point = [event.pos().x(), event.pos().y(), polarity]

                mask_polygon = MaskItem(self.mask_color, self.current_mask_manager, unique_point)
                mask_polygon.setName(self.current_mask_manager.getName())
                display_name = self.display_bar.getAnnotationLabel()
                if display_name == "":
                    display_name = self.current_mask_manager.getName()
                mask_polygon.setDisplayName(display_name)

                self.current_mask_manager.appendMaskItem(mask_polygon)
                self.current_mask_manager.displayNextMaskItem()

                editing_existing_polygon = self.current_mask_manager.getClickedPointsCount() > 1

                if editing_existing_polygon:
                    mask_array = self.segment_agent.generateMaskFromPoints(self.current_mask_manager.getClickedPoints())
                else:
                    mask_array = self.segment_agent.generateMaskFromPoint(event.pos().x(), event.pos().y())

                mask_polygon.draw(self, mask_array)
                mask_polygon.setSelected(True)

                # Update mask menu
                if editing_existing_polygon:
                    self.display_bar.getRightDrawer().displayPolygonImage(mask_polygon)
                    self.display_bar.getRightDrawer().updateMask(mask_polygon)
                else:
                    self.display_bar.getRightDrawer().addMask(mask_polygon)

            elif self.tool_mode == ToolMode.ERASE_MASK:
                point = self.mapToScene(event.pos())
                items = self.scene.items(point)
                for item in items:
                    if isinstance(item, QGraphicsPolygonItem):
                        self.scene.removeItem(item)
                        self.display_bar.getRightDrawer().removeMask(item)
                        return

    def isPointInEditableArea(self, point: QPoint) -> bool:
        relative_position = self.mapToScene(point)
        rel_x = relative_position.x()
        rel_y = relative_position.y()
        return 0 < rel_x < self.pixmap.width() and 0 < rel_y < self.pixmap.height()

    def updateCurrentImage(self):
        image_array = self.captureScreenshot()
        self.segment_agent.setImage(image_array)
        self.viewport_moved = False

    def wheelEvent(self, event: QWheelEvent):
        self.viewport_moved = True
        if event.angleDelta().y() > 0:
            factor = self.zoom_factor_base
        else:
            factor = 1 / self.zoom_factor_base
        self.zoom_level *= factor
        self.scale(factor, factor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.middle_mouse_button_pressed = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):

        if self.isPointInEditableArea(event.pos()):

            if self.middle_mouse_button_pressed:
                QApplication.setOverrideCursor(Qt.CursorShape.SizeAllCursor)
            elif self.tool_mode == ToolMode.CREATE_MASK:
                QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
            else:
                QApplication.setOverrideCursor(QCursor(QPixmap("assets/icons/circle.png")))
        else:
            QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)

        relative_position = self.mapToScene(event.pos())
        rel_x = relative_position.x()
        rel_y = relative_position.y()

        if rel_x < 0:
            self.mouse_position_x = 0
        elif rel_x > self.pixmap.width():
            self.mouse_position_x = self.pixmap.width()
        else:
            self.mouse_position_x = rel_x

        if rel_y < 0:
            self.mouse_position_y = 0
        elif rel_y > self.pixmap.height():
            self.mouse_position_y = self.pixmap.height()
        else:
            self.mouse_position_y = rel_y

        self.display_bar.getCoordinateDisplayWindow().updateCoordinates(int(self.mouse_position_x), int(self.mouse_position_y))

        if self.middle_mouse_button_pressed:
            self.viewport_moved = True

            delta = event.pos() - self.last_scroll_position
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.last_scroll_position = event.pos()
        else:
            super().mouseMoveEvent(event)

    def leaveEvent(self, event: QEvent):
        QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def eventFilter(self, object: QObject, event: QEvent):
        if isinstance(event, QKeyEvent) and event.key() == Qt.Key.Key_Tab:
            self.tab_key_pressed.emit()
            if self.isPointInEditableArea(self.display_bar.getCoordinateDisplayWindow().getCoordinates()):
                if self.tool_mode == ToolMode.CREATE_MASK:
                    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
                else:
                    QApplication.setOverrideCursor(QCursor(QPixmap("assets/icons/circle.png")))
            return True
        return super().eventFilter(object, event)

    def close(self):
        self.masks.clear()
        self.loaded_mask_ids.clear()
        self.mask_id = 1
        self.mask_managers.clear()
        self.scene.clear()
        self.current_mask_manager = None
        self.viewport_moved = True
        self.hide()

    def setToolMode(self, tool_mode: ToolMode):
        self.tool_mode = tool_mode

    def setMaskColor(self, mask_color: QColor):
        self.mask_color = mask_color

    def getMaskColor(self):
        return self.mask_color

    def setSegmentAgent(self, segment_agent: SegmentAgent):
        self.segment_agent = segment_agent

    def setCoordinateDisplay(self, display_bar: DisplayBar):
        self.display_bar: DisplayBar = display_bar

    def getScene(self) -> QGraphicsScene:
        return self.scene

    def getAllMaskManagers(self):
        return self.mask_managers

    def loadExistingPolygons(self, polygon_dict: List[dict[str, QColor, List[Tuple[float, float]]]]):
        for mask in polygon_dict:
            manager = MaskManager(mask["name"])
            manager.setGraphicsView(self)
            point = [mask["points"][0][0], mask["points"][0][1], 1]
            mask_polygon = MaskItem(mask["mask_color"], manager, point)
            mask_polygon.setName(manager.getName())
            mask_polygon.setDisplayName(mask["display_name"])
            self.loaded_mask_ids.append(manager.getName())
            manager.appendMaskItem(mask_polygon)
            manager.displayNextMaskItem()
            mask_polygon.drawFixed(mask["points"])
            mask_polygon.setZValue(10)
            self.mask_managers.append(manager)
            self.display_bar.getRightDrawer().addMask(mask_polygon)

    def saveProject(self, path: str, main_window: QMainWindow):
        mask_managers = self.getAllMaskManagers()
        polygons = []

        def runnable():
            manager: MaskManager
            for manager in mask_managers:
                if not manager.hasNothingDisplayed():
                    polygons.append(manager.displayed_mask.toDictionary())

            arr = qimage2ndarray.byte_view(self.image)
            project = [arr, polygons]
            filehandler = open(path, "wb")
            pickle.dump(project, filehandler, pickle.HIGHEST_PROTOCOL)
            return main_window

        self.project_saver_worker = AsyncWorker(runnable)
        self.project_saver_worker.setCallbackFunction(self.project_saved.emit)
        self.project_saver_worker.start()

    def rotateImageByExifTag(self, image: Image.Image):
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == "Orientation":
                    exif = dict(image.getexif().items())

                    if exif[orientation] == 3:
                        image = image.rotate(180, expand=True)
                    elif exif[orientation] == 6:
                        image = image.rotate(270, expand=True)
                    elif exif[orientation] == 8:
                        image = image.rotate(90, expand=True)
                    return image
        except (AttributeError, KeyError, IndexError):
            return image

    def exportAsImage(self, file_path: str):
        def runnable():
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            self.image.save(buffer, "PNG")
            original_image = Image.open(io.BytesIO(buffer.data()))
            size = self.image.size()
            mask_image = Image.new("RGBA", (size.width(), size.height()), (0, 0, 0, 0))
            draw = ImageDraw.Draw(mask_image)
            polygons = []
            for item in self.scene.items():
                if isinstance(item, QGraphicsPolygonItem):
                    polygons.append(item)

            mask: MaskItem
            for mask in polygons:
                polygon = mask.polygon()
                points = [(point.x(), point.y()) for point in polygon]
                r, g, b, a = mask.mask_color.getRgb()
                draw.polygon(points, fill=(r, g, b, a))

            if original_image.mode != "RGBA":
                original_image = original_image.convert("RGBA")

            output_image = Image.alpha_composite(original_image, mask_image)
            output_image.save(file_path)
            return output_image

        self.image_saver_worker = AsyncWorker(runnable)
        self.image_saver_worker.setCallbackFunction(self.export_done.emit)
        self.image_saver_worker.start()

    def exportJson(self, file_path: str):

        data: dict = {}

        info = {"date_created": datetime.now(), "version": 1, "description": "Exported from SegmentationPainter"}

        data["info"] = info

        categories = [{"id": 0, "name": "coral", "supercategory": "none"}]

        data["categories"] = categories

        images = [{"id": 0, "file_name": self.image_path, "height": 2, "width": 3, "date_captured": "unknown"}]

        data["images"] = images

        for mask_manager in self.mask_managers:

            maskItem: MaskItem = mask_manager.getCurrentlyDisplayedMask()

            if maskItem.mask_array is None:
                continue

            datastr = self.segment_agent.generate_coco_annotations(self.image_path, maskItem.mask_array)

            data.append(datastr)

        with open(file_path, "w") as f:
            json.dump(data, f)
