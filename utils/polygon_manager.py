from PyQt6.QtGui import QColor
from components.display_bar.display_bar import DisplayBar
from utils.polygon import Polygon
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from components.image_canvas import ImageCanvas


class PolygonManager:
    """Manages a collection of polygons. Includes undo/redo functionality as well as placing polygons onto a QGraphicsView"""

    def __init__(self, name):
        self.masks = []
        self.clicked_points = []
        self.root_mask = Polygon(QColor(0, 0, 0, 0))
        self.root_mask.set_name(name)
        self.root_mask.set_selected(True)
        self.last_mask = self.root_mask
        self.displayed_mask = self.root_mask
        self.isSelected = True
        self.name = name
        self.graphics_view: ImageCanvas = None

    def appendMaskItem(self, mask_item: Polygon):
        self.displayed_mask.next = mask_item
        mask_item.previous = self.displayed_mask
        self.masks.append(mask_item)

    def displayNextMaskItem(self, display_bar: DisplayBar = None):
        if self.displayed_mask.next is not None:
            if self.displayed_mask != self.root_mask:
                self.graphics_view.get_scene().removeItem(self.displayed_mask)
            self.displayed_mask = self.displayed_mask.next
            self.displayed_mask.set_selected(True)

            self.graphics_view.scene.addItem(self.displayed_mask)
            unique_point = self.displayed_mask.get_unique_point()
            self.addClickedPoint(unique_point[0], unique_point[1], unique_point[2])

            if display_bar == None:
                return

            if self.displayed_mask.previous == self.root_mask:
                display_bar.get_toolbox().add_polygon_to_polygon_list(self.displayed_mask)
            else:
                display_bar.get_toolbox().update_polygon_list(self.displayed_mask)

    def displayPreviousMaskItem(self, display_bar: DisplayBar):

        if self.displayed_mask.previous is not None:
            self.graphics_view.scene.removeItem(self.displayed_mask)
            self.displayed_mask = self.displayed_mask.previous
            if self.displayed_mask != self.root_mask:
                self.graphics_view.scene.addItem(self.displayed_mask)
                self.removeMostRecentPoint()
            if self.hasNothingDisplayed():
                display_bar.get_toolbox().remove_polygon_from_polygon_list(self.displayed_mask)
            else:
                display_bar.get_toolbox().update_polygon_list(self.displayed_mask)

    def isRootMask(self, mask_item: Polygon) -> bool:
        return mask_item == self.root_mask

    def unselectCurrentMask(self):
        self.displayed_mask.set_selected(False)

    def addClickedPoint(self, x: int, y: int, positive=True):
        point_polarity = 1 if positive else 0
        self.clicked_points.append([[x, y], point_polarity])

    def addClickedPointEntry(self, entry):
        self.clicked_points.append(entry)

    def clearClickedPoints(self):
        self.clicked_points.clear()

    def getClickedPointsCount(self):
        return len(self.clicked_points)

    def getClickedPoints(self):
        return self.clicked_points

    def hasNothingDisplayed(self):
        return self.root_mask == self.displayed_mask

    def getCurrentlyDisplayedMask(self):
        return self.displayed_mask

    def setGraphicsView(self, graphics_view):
        self.graphics_view = graphics_view

    def getName(self):
        return self.name

    def removeMostRecentPoint(self):
        if len(self.clicked_points) > 0:
            self.clicked_points.pop()

    def getMostRecentPoint(self):
        return self.clicked_points[-1]
