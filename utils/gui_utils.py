import os
from PyQt6.QtWidgets import QFileDialog, QToolBar
from PyQt6.QtGui import QIcon, QAction, QActionGroup
from PyQt6.QtCore import Qt

def createIcon(filename):
    directory_path = os.path.join("assets", "icons")
    return QIcon(os.path.join(directory_path, filename))

def chooseFile():
    path, _ = QFileDialog.getOpenFileName(
        None, "Choose Image", "", "Image (*.png *.jpg *.jpeg *.gif *.tif *.tiff)"
    )
    return path

def chooseProject():
    path, _ = QFileDialog.getOpenFileName(
        None, "Choose Segmentation Project", "", "Project (*.sgmt)"
    )
    return path

def saveFile():
    path, _ = QFileDialog.getSaveFileName(None, "Choose Image", "masked_image.png", "Image (*.png)")
    return path

def saveProject():
    path, _ = QFileDialog.getSaveFileName(None, "Saving project", "project.sgmt", "Project (*.sgmt)")
    return path
