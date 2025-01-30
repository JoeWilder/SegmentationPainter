from PyQt6.QtWidgets import QGraphicsPolygonItem, QGraphicsView
from PyQt6.QtGui import QBrush, QPolygonF, QColor, QPen
from PyQt6.QtCore import QPointF
import cv2
import numpy as np


class Polygon(QGraphicsPolygonItem):
    """Used to represent a mask polygon"""

    def __init__(self, mask_color, manager=None, unique_point=None):
        super().__init__()
        self.mask_color: QColor = mask_color
        self.next: Polygon = None
        self.previous: Polygon = None
        self.name = None
        self.display_name = None
        self.manager = manager
        self.unique_point = unique_point
        self.mask_array = None

    def draw(self, graphics_view: QGraphicsView, mask_array: np.ndarray, map=True):
        self.mask_array = mask_array
        # np.save("DEBUG1.npy", self.mask_array)
        contours, _ = cv2.findContours(mask_array.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        num_true_values = np.sum(mask_array)
        # print(f"true vals: {num_true_values}")

        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            polygon = QPolygonF()

            for point in largest_contour:
                x, y = point[0]
                if map:
                    scene_point = graphics_view.mapToScene(x, y)
                    # print(f"Original: ({x}, {y}), Scene: {scene_point}")
                    polygon.append(scene_point)
                else:
                    qpoint = QPointF(x, y)
                    # print(f"Original: ({x}, {y}), QPointF: {qpoint}")
                    polygon.append(qpoint)

            self.setPolygon(polygon)

            brush = QBrush(self.mask_color)
            self.setBrush(brush)
            self.setPen(QPen(QColor(0, 0, 0, 0)))

    def drawFixed(self, pixel_array):
        self.mask_array = pixel_array
        polygon = QPolygonF()

        for point in pixel_array:
            test = QPointF(point[0], point[1])
            polygon.append(test)

        self.setPolygon(polygon)
        brush = QBrush(self.mask_color)
        self.setBrush(brush)
        self.setPen(QPen(QColor(0, 0, 0, 0)))

    def set_name(self, name: str):
        self.name = name

    def set_display_name(self, display_name: str):
        self.display_name = display_name

    def get_display_name(self):
        return self.display_name

    def get_name(self):
        return self.name

    def set_selected(self, is_selected):
        if is_selected:
            self.setBrush(self.mask_color.darker(150))
        else:
            self.setBrush(self.mask_color)

    def get_mask_manager(self):
        return self.manager

    def get_unique_point(self):
        return self.unique_point

    def to_dictionary(self):
        return {
            "name": self.name,
            "display_name": self.display_name,
            "mask_color": self.mask_color,
            "points": [(point.x(), point.y()) for point in self.polygon()],
        }

    def set_color(self, color: QColor):
        self.setBrush(color)
        self.mask_color = color
