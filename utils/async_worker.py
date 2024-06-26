from PyQt6.QtCore import QThread, pyqtSignal


class AsyncWorker(QThread):
    """A class for running a function on a separate thread"""
    job_done = pyqtSignal(object)

    def __init__(self, async_function):
        super().__init__()
        self.async_function = async_function

    def setCallbackFunction(self, callback_function):
        self.job_done.connect(callback_function)

    def run(self):
        try:
            result = self.async_function()
            self.job_done.emit(result)
        except: Exception

        