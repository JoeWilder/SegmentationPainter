import os
from PyQt6.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QVBoxLayout, QGraphicsPolygonItem, QApplication, QMainWindow
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QColor, QImageReader, QKeyEvent, QCursor
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPoint, QEvent, QObject, QPointF
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

from utils.async_worker import AsyncWorker
from utils.tool_mode import ToolMode
from utils.mask import MaskItem
import utils.gui_utils as utils
from components.loading_bar import LoadingBar
from segment_agent import SegmentAgent
from components.display_bar import DisplayBar
from utils.mask_manager import MaskManager
import qimage2ndarray
import time


class ImageCanvas(QGraphicsView):
    """Used to display and edit an image"""
    image_loaded = pyqtSignal()
    tab_key_pressed = pyqtSignal()

    def __init__(self, image_source):
        super().__init__()
        

        self.image_path = None
        if isinstance(image_source, str):  # If image_source is a path
            self.image_path = image_source
            #self.image_data = QImage(image_source)
        elif isinstance(image_source, QImage):  # If image_source is already a QImage
            self.image = image_source


        self.tool_mode = ToolMode.CREATE_MASK
        self.mask_color = QColor(30, 144, 255, 75)
        self.mouse_position_x = "-"
        self.mouse_position_y = "-"
        self.masks = []
        self.mask_id = 1
        self.loaded_mask_ids = []
        self.viewport_moved = True
        self.setStyleSheet("""ImageCanvas { 
                           border: 3px solid rgb(230, 230, 230);
                           }""")
        self.factor = None
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



    def loadImage(self):
        def runnable():
            image = QImage(self.image_path)
            return image
        self.image_loader_worker = AsyncWorker(runnable)
        self.image_loader_worker.setCallbackFunction(self.asyncWorkerDone)
        self.image_loader_worker.start()

    def asyncWorkerDone(self, image):
        self.image: QImage = image
        self.pixmap = QPixmap.fromImage(image)
        self.image_item = self.scene.addPixmap(self.pixmap)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.centerImageInView()
        self.image_loaded.emit()

    def centerImageInView(self):
        view_rect = self.viewport().rect()
        scene_rect = self.scene.sceneRect()
        if not scene_rect.isEmpty():
            view_aspect_ratio = view_rect.width() / view_rect.height()
            scene_aspect_ratio = scene_rect.width() / scene_rect.height()
            
            if view_aspect_ratio >= scene_aspect_ratio:
                scale_factor = view_rect.width() / scene_rect.width()
            else:
                scale_factor = view_rect.height() / scene_rect.height()
            
            self.scale(scale_factor, scale_factor)

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
        if self.current_mask_manager != None:
            self.current_mask_manager.displayPreviousMaskItem(self.display_bar)

    def redoMask(self):
        if self.current_mask_manager != None:
            self.current_mask_manager.displayNextMaskItem(self.display_bar)

    def mousePressEvent(self, event):

        if not self.isPointInEditableArea(event.pos()):
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self.middle_mouse_button_pressed = True
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
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
        return (0 < rel_x < self.pixmap.width() and 0 < rel_y < self.pixmap.height())
            

    def updateCurrentImage(self):
        image_array = self.captureScreenshot()
        self.segment_agent.setImage(image_array)
        self.viewport_moved = False

    def wheelEvent(self, event):
        self.viewport_moved = True
        if event.angleDelta().y() > 0:
            factor = self.zoom_factor_base
        else:
            factor = 1 / self.zoom_factor_base
        self.factor = factor
        self.zoom_level *= factor
        self.scale(factor, factor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.middle_mouse_button_pressed = False
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):


        if self.isPointInEditableArea(event.pos()):
            if self.tool_mode == ToolMode.CREATE_MASK:
                QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
            else:
                QApplication.setOverrideCursor(QCursor(QPixmap('assets/icons/circle.png')))
        else:
            QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)

        relative_position = self.mapToScene(event.pos())
        rel_x = relative_position.x()
        rel_y = relative_position.y()

        if rel_x < 0 :
            self.mouse_position_x = 0
        elif rel_x > self.pixmap.width():
            self.mouse_position_x = self.pixmap.width()
        else:
            self.mouse_position_x = rel_x

        if rel_y < 0 :
            self.mouse_position_y = 0
        elif rel_y > self.pixmap.height():
            self.mouse_position_y = self.pixmap.height()
        else:
            self.mouse_position_y = rel_y
        
        
        self.display_bar.getCoordinateDisplayWindow().updateCoordinates(int(self.mouse_position_x), int(self.mouse_position_y))
        
        if self.middle_mouse_button_pressed:
            self.viewport_moved = True

            delta = event.pos() - self.last_scroll_position
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            self.last_scroll_position = event.pos()
        else:
            super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def eventFilter(self, object: QObject, event: QEvent):
        if isinstance(event, QKeyEvent) and event.key() == Qt.Key.Key_Tab:
            self.tab_key_pressed.emit()
            if self.isPointInEditableArea(self.display_bar.getCoordinateDisplayWindow().getCoordinates()):
                if self.tool_mode == ToolMode.CREATE_MASK:
                    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
                else:
                    QApplication.setOverrideCursor(QCursor(QPixmap('assets/icons/circle.png')))
            return True
        return super().eventFilter(object, event)

    def close(self):
        self.scene.clear()
        self.hide()
        self.display_bar.hide()

    def setToolMode(self, tool_mode):
        self.tool_mode = tool_mode

    def setMaskColor(self, mask_color):
        self.mask_color = mask_color

    def getMaskColor(self):
        return self.mask_color
    
    def setSegmentAgent(self, segment_agent: SegmentAgent):
        self.segment_agent = segment_agent
    
    def setCoordinateDisplay(self, display_bar):
        self.display_bar: DisplayBar = display_bar

    def getScene(self) -> QGraphicsScene:
        return self.scene

    def getAllMaskManagers(self):
        return self.mask_managers

    def loadExistingPolygons(self, polygon_dict):
        for mask in polygon_dict:
            manager = MaskManager(mask["name"])
            manager.setGraphicsView(self)

            point = [mask["points"][0][0], mask["points"][0][1], 1]

            mask_polygon = MaskItem(mask["mask_color"], manager, point)
            mask_polygon.setName(manager.getName())
            self.loaded_mask_ids.append(manager.getName())
            manager.appendMaskItem(mask_polygon)
            manager.displayNextMaskItem()

            mask_polygon.drawFixed(mask["points"])


            #self.scene.addItem(mask_polygon)
            mask_polygon.setZValue(10)


            self.mask_managers.append(manager)


            # Update mask menu
            self.display_bar.getRightDrawer().addMask(mask_polygon)
