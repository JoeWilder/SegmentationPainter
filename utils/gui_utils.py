from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QIcon
import os


def createIcon(filename):
    directory_path = os.path.join("assets", "icons")
    return QIcon(os.path.join(directory_path, filename))


def get_file_path():
    path, _ = QFileDialog.getOpenFileName(None, "Choose Image", "", "Image (*.png *.jpg *.jpeg *.gif *.tif *.tiff *.sgmt)")
    return path


def get_project_path():
    path, _ = QFileDialog.getOpenFileName(None, "Choose Segmentation Project", "", "Project (*.sgmt)")
    return path


def save_file_path():
    path, _ = QFileDialog.getSaveFileName(None, "Choose Image", "masked_image.png", "Image (*.png)")
    return path


def save_json_path(file_name: str):
    file_name = file_name.split(".")[0]
    path, _ = QFileDialog.getSaveFileName(None, "Save json", f"{file_name}-annotations.json", "Json (*.json)")
    return path


def save_project_path():
    path, _ = QFileDialog.getSaveFileName(None, "Saving project", "project.sgmt", "Project (*.sgmt)")
    return path


def save_shapefile_path():
    path, _ = QFileDialog.getSaveFileName(None, "Save shapefile", "annotated-shapes.shp", "Shape (*.shp)")
    return path
