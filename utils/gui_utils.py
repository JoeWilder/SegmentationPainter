import os
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QIcon

def createIcon(filename):
    directory_path = os.path.join("assets", "icons")
    return QIcon(os.path.join(directory_path, filename))

def getFilePath():
    path, _ = QFileDialog.getOpenFileName(
        None, "Choose Image", "", "Image (*.png *.jpg *.jpeg *.gif *.tif *.tiff *.sgmt)"
    )
    return path

def getProjectPath():
    path, _ = QFileDialog.getOpenFileName(
        None, "Choose Segmentation Project", "", "Project (*.sgmt)"
    )
    return path

def saveFilePath():
    path, _ = QFileDialog.getSaveFileName(None, "Choose Image", "masked_image.png", "Image (*.png)")
    return path

def saveProjectPath():
    path, _ = QFileDialog.getSaveFileName(None, "Saving project", "project.sgmt", "Project (*.sgmt)")
    return path
