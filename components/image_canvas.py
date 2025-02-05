from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QApplication
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QColor, QImageReader, QKeyEvent, QCursor, QMouseEvent, QWheelEvent
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPoint, QEvent, QObject, QBuffer, pyqtBoundSignal

from components.display_bar.display_bar import DisplayBar

import qimage2ndarray
from PIL import Image, ImageDraw, ExifTags
import io
import json
from datetime import datetime
from shapely.geometry import Polygon as ShapelyPolygon
import geopandas as gpd
import rasterio
import os

from utils.async_worker import AsyncWorker
from utils.tool_mode import ToolMode
from utils.polygon import Polygon
from segment_agent import SegmentAgent
from utils.polygon_manager import PolygonManager

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main_page import MainPage


Image.MAX_IMAGE_PIXELS = None


class ImageCanvas(QGraphicsView):
    """Used to display and edit an image"""

    image_loaded_event: pyqtBoundSignal = pyqtSignal()
    tab_key_pressed_event = pyqtSignal()
    project_saved_event = pyqtSignal()
    export_done_event = pyqtSignal()
    mask_change_event = pyqtSignal(Polygon)

    def __init__(self, parent):
        super().__init__()

        self.main_page: MainPage = parent
        self.tool_mode = ToolMode.CREATE_MASK
        self.polygon_brush_color = QColor(30, 144, 255, 75)
        self.mouse_position_x = "-"
        self.mouse_position_y = "-"
        self.unique_polygon_id = 1
        self.existing_mask_ids = []
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

        self.mask_managers = []
        self.current_mask_manager = None

        self.image_path = None

    def load_image(self, file_path: str):
        """Load the given file asyncronously and display it in the image canvas scene"""
        self.image_path = file_path

        def async_load_image():
            image: Image.Image = Image.open(file_path)
            image = self.rotate_image_by_exif_tag(image)
            image = image.convert("RGBA")
            qimage = QImage(image.tobytes("raw", "RGBA"), image.size[0], image.size[1], QImage.Format.Format_RGBA8888)
            return qimage

        self.image_loader_worker = AsyncWorker(async_load_image)
        self.image_loader_worker.setCallbackFunction(self.async_image_loaded_listener)
        self.image_loader_worker.start()

    def async_image_loaded_listener(self, image: QImage):
        self.image: QImage = image
        self.pixmap = QPixmap.fromImage(image)
        self.image_item = self.scene.addPixmap(self.pixmap)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.fitInView(self.image_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.image_loaded_event.emit()

    def take_screenshot(self):
        """Capture the currently displayed image data as a numpy array"""
        area = self.viewport().rect()
        image = QImage(area.size(), QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        visible_area = QRectF(image.rect())
        self.render(painter, visible_area, area)
        painter.end()
        array = qimage2ndarray.rgb_view(image)
        return array

    def undo_polygon(self, display_bar: DisplayBar):
        """Update currently selected polygon to its previous state"""
        if self.current_mask_manager == None:
            return
        self.current_mask_manager.displayPreviousMaskItem(display_bar)

    def redo_polygon(self, display_bar: DisplayBar):
        """Update currently selected polygon to its next state if one exists"""
        if self.current_mask_manager == None:
            return
        self.current_mask_manager.displayNextMaskItem(display_bar)

    def mousePressEvent(self, event: QMouseEvent):

        if not self.is_point_in_canvas(event.pos()):
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
                        if isinstance(item, Polygon):
                            if self.current_mask_manager != None:
                                self.current_mask_manager.unselectCurrentMask()
                            self.current_mask_manager = item.get_mask_manager()
                            item.set_selected(True)

                            self.main_page.display_bar.get_toolbox().move_selected_list_item(item)
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

                    mask_name = f"mask{self.unique_polygon_id}"

                    while mask_name in self.existing_mask_ids:
                        self.unique_polygon_id += 1
                        mask_name = f"mask{self.unique_polygon_id}"

                    self.current_mask_manager = PolygonManager(mask_name)
                    self.current_mask_manager.setGraphicsView(self)
                    self.unique_polygon_id += 1
                    self.mask_managers.append(self.current_mask_manager)
                    polarity = 1

                if self.viewport_moved:
                    self.update_current_image()

                mapped_unique_point = event.pos()

                unique_point = [round(mapped_unique_point.x()), round(mapped_unique_point.y()), polarity]

                mask_polygon = Polygon(
                    self.polygon_brush_color, self.current_mask_manager, unique_point, self.unique_polygon_id, self.main_page.display_bar.display_bar_toolbox.group_dropdown.currentText()
                )

                mask_polygon.set_name(self.current_mask_manager.getName())
                display_name = self.main_page.display_bar.get_annotation_label()
                if display_name == "":
                    display_name = self.current_mask_manager.getName()
                mask_polygon.set_display_name(display_name)

                self.current_mask_manager.appendMaskItem(mask_polygon)
                self.current_mask_manager.displayNextMaskItem()

                editing_existing_polygon = self.current_mask_manager.getClickedPointsCount() > 1

                if editing_existing_polygon:
                    mask_array = self.segment_agent.generateMaskFromPoints(self.current_mask_manager.getClickedPoints())
                else:
                    mask_array = self.segment_agent.generateMaskFromPoint(event.pos().x(), event.pos().y())

                mask_polygon.draw(self, mask_array)
                mask_polygon.set_selected(True)

                # Update mask menu
                if editing_existing_polygon:
                    self.main_page.display_bar.get_toolbox().draw_polygon_image(mask_polygon)
                    self.main_page.display_bar.get_toolbox().update_polygon_list(mask_polygon)
                else:
                    self.main_page.display_bar.get_toolbox().add_polygon_to_polygon_list(mask_polygon)

            elif self.tool_mode == ToolMode.ERASE_MASK:
                point = self.mapToScene(event.pos())
                items = self.scene.items(point)
                for item in items:
                    if isinstance(item, QGraphicsPolygonItem):
                        self.scene.removeItem(item)
                        self.main_page.display_bar.get_toolbox().remove_polygon_from_polygon_list(item)
                        return

    def is_point_in_canvas(self, point: QPoint) -> bool:
        relative_position = self.mapToScene(point)
        rel_x = relative_position.x()
        rel_y = relative_position.y()
        return 0 < rel_x < self.pixmap.width() and 0 < rel_y < self.pixmap.height()

    def update_current_image(self):
        """Capture current viewport image data and pass it into SAM model"""
        image_array = self.take_screenshot()
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

        if self.is_point_in_canvas(event.pos()):

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

        self.main_page.display_bar.get_coordinate_display_widget().update_coordinates(int(self.mouse_position_x), int(self.mouse_position_y))

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
            self.tab_key_pressed_event.emit()
            if self.is_point_in_canvas(self.main_page.display_bar.get_coordinate_display_widget().get_coordinates()):
                if self.tool_mode == ToolMode.CREATE_MASK:
                    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
                else:
                    QApplication.setOverrideCursor(QCursor(QPixmap("assets/icons/circle.png")))
            return True
        return super().eventFilter(object, event)

    def close(self):
        self.existing_mask_ids.clear()
        self.unique_polygon_id = 1
        self.mask_managers.clear()
        self.scene.clear()
        self.current_mask_manager = None
        self.viewport_moved = True
        self.image = None
        self.hide()

    def set_tool_mode(self, tool_mode: ToolMode):
        self.tool_mode = tool_mode

    def set_polygon_brush_color(self, mask_color: QColor):
        self.polygon_brush_color = mask_color

    def get_polygon_brush_color(self):
        return self.polygon_brush_color

    def set_segment_agent(self, segment_agent: SegmentAgent):
        self.segment_agent = segment_agent

    def get_scene(self) -> QGraphicsScene:
        return self.scene

    def get_mask_managers(self):
        return self.mask_managers

    def rotate_image_by_exif_tag(self, image: Image.Image):
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

    def export_as_image(self, file_path: str):
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

            mask: Polygon
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
        self.image_saver_worker.setCallbackFunction(self.export_done_event.emit)
        self.image_saver_worker.start()

    def export_json(self, file_path: str):

        data: dict = {}

        info = {"date_created": str(datetime.now()), "version": 1, "description": "Exported from SegmentationPainter"}

        data["info"] = info

        categories = [{"id": 0, "name": "coral", "supercategory": "none"}]

        data["categories"] = categories

        image_path = "None" if self.image_path is None else self.image_path

        images = [{"id": 0, "file_name": image_path, "height": 2, "width": 3, "date_captured": "unknown"}]

        data["images"] = images

        data["annotations"] = []

        mask_manager: PolygonManager
        for mask_manager in self.mask_managers:

            maskItem: Polygon = mask_manager.getCurrentlyDisplayedMask()

            if maskItem.mask_array is None:
                continue

            datastr = self.segment_agent.generate_coco_annotations(self.image_path, 0, maskItem.mask_array)

            data["annotations"].append(datastr)

        with open(file_path, "w") as f:
            json.dump(data, f)

    def export_shapefile(self, file_path: str):
        extension = os.path.splitext(self.image_path)[-1]

        transform, crs = None, None
        if extension in [".tif", ".tiff"] and self.image_path:
            with rasterio.open(self.image_path) as src:
                transform, crs = src.transform, src.crs

        rows = []

        for item in self.scene.items():
            if isinstance(item, QGraphicsPolygonItem):
                label = item.get_display_name()
                polygon_id = item.id
                group_id = item.group_id
                color = item.mask_color
                r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()

                polygon = item.polygon()
                points = [(point.x(), point.y()) for point in polygon]

                if len(points) < 3:
                    continue

                # If using a tiff file, apply transformation; otherwise, flip Y
                transformed_points = [transform * (x, y) for x, y in points] if transform else [(x, -y) for x, y in points]

                poly = ShapelyPolygon(transformed_points)
                seed_point = QPoint(round(item.unique_point[0]), round(item.unique_point[1]))
                seed_point = self.mapToScene(seed_point)

                rows.append(
                    {
                        "polygon_id": polygon_id,
                        "group_id": group_id,
                        "label": label,
                        "geometry": poly,
                        "seed_pnt_x": seed_point.x(),
                        "seed_pnt_y": seed_point.y(),
                        "red": r,
                        "green": g,
                        "blue": b,
                        "alpha": a,
                    }
                )

        gdf = gpd.GeoDataFrame(rows, columns=["polygon_id", "group_id", "label", "geometry", "seed_pnt_x", "seed_pnt_y", "red", "green", "blue", "alpha"], crs=crs if crs else None)
        # WARNING THROWN HERE DUE TO NO CRS, IT'S FINE THOUGH?
        gdf.to_file(file_path)

    def import_shapefile(self, file_path: str):
        try:
            gdf = gpd.read_file(file_path)

            required_columns = {"polygon_id", "group_id", "label", "geometry", "seed_pnt_x", "seed_pnt_y", "red", "green", "blue", "alpha"}
            if not required_columns.issubset(gdf.columns):
                raise ValueError(f"Shapefile is missing required columns: {required_columns - set(gdf.columns)}")

            transform = None
            if os.path.splitext(self.image_path)[-1] in [".tif", ".tiff"]:
                with rasterio.open(self.image_path) as src:
                    transform = ~src.transform

            for _, row in reversed(list(gdf.iterrows())):
                polygon_id = row["polygon_id"]
                group_id = row["group_id"]
                label = row["label"]
                geometry = row["geometry"]
                unique_point_x = row["seed_pnt_x"]
                unique_point_y = row["seed_pnt_y"]
                r, g, b, a = row["red"], row["green"], row["blue"], row["alpha"]

                manager = PolygonManager(f"polygon")
                manager.setGraphicsView(self)

                if transform:
                    points = [transform * (x, y) for x, y in geometry.exterior.coords]
                else:
                    points = [(x, -y) for x, y in geometry.exterior.coords]

                first_point = [unique_point_x, unique_point_y, 1]
                polygon_color = QColor(r, g, b, a)
                mask_polygon = Polygon(polygon_color, manager, first_point)
                manager.clicked_points.append([[unique_point_x, unique_point_y], 1])
                mask_polygon.set_name(manager.getName())
                mask_polygon.set_display_name(label)
                mask_polygon.id = polygon_id
                mask_polygon.group_id = group_id
                self.existing_mask_ids.append(manager.getName())
                manager.appendMaskItem(mask_polygon)
                manager.displayNextMaskItem()
                mask_polygon.drawFixed(points)
                mask_polygon.setZValue(10)
                self.mask_managers.append(manager)
                self.main_page.display_bar.display_bar_toolbox.add_polygon_to_polygon_list(mask_polygon)

            print(f"Successfully imported {len(gdf)} polygons from {file_path}")

        except Exception as e:
            print(f"Error importing shapefile: {e}")
