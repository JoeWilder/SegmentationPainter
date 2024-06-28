from PyQt6.QtCore import pyqtSignal, pyqtBoundSignal, QObject
import os
import requests
from typing import Final
from utils.async_worker import AsyncWorker


class CheckpointDownloader(QObject):
    checkpoints_downloaded: pyqtBoundSignal = pyqtSignal()

    def __init__(self):

        super().__init__()

        self._download_urls: Final[list[str]] = [
            "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
            "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth",
            "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
        ]

    def all_checkpoints_downloaded(self):
        for url in self._download_urls:
            file_name = url.split("/")[-1]
            if not os.path.exists(os.path.join("sam_checkpoints", file_name)):
                return False
        return True

    def download_sam_checkpoints(self):
        def runnable():
            for url in self._download_urls:
                file_name = url.split("/")[-1]
                if not os.path.exists(os.path.join("sam_checkpoints", file_name)):
                    r = requests.get(url, allow_redirects=True)
                    open(f"sam_checkpoints/{file_name}", "wb").write(r.content)

        self._downloader_worker = AsyncWorker(runnable)
        self._downloader_worker.job_done.connect(self.checkpoints_downloaded.emit)
        self._downloader_worker.start()
