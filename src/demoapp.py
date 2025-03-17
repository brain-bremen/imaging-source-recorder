import imagingcontrol4 as ic4

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, Slot
from fastapi import FastAPI
import uvicorn
import threading

from mainwindow import MainWindow

from abc import ABC, abstractmethod


class AppInterface(ABC):
    @abstractmethod
    def start_recording(self, filename: str | None = None):
        pass

    @abstractmethod
    def stop_recording(self):
        pass

    @abstractmethod
    def pause_recording(self):
        pass

    @abstractmethod
    def resume_recording(self):
        pass

    @abstractmethod
    def set_filename(self):
        pass

    @abstractmethod
    def set_metadata(self):
        pass

    @abstractmethod
    def receive_recording(self):
        pass


# class QtAppInterface(QObject, AppInterface):
#     start_recording_signal = Signal()
#     stop_recording_signal = Signal()

#     def __init__(self, main_window):
#         super().__init__()
#         self.main_window = main_window

#         # Connect signals to slots
#         self.start_recording_signal.connect(self.main_window.start_recording)
#         self.stop_recording_signal.connect(self.main_window.stop_recording)

#     def start_recording(self):
#         self.start_recording_signal.emit()

#     def stop_recording(self):
#         self.stop_recording_signal.emit()


# remote_app = FastAPI()


# # Define your FastAPI endpoints here
# @remote_app.get("/start")
# def start_recording():
#     # app_interface.start_recording()
#     return {"status": "recording started"}


# @remote_app.get("/stop")
# def stop_recording():
#     app_interface.stop_recording()
#     return {"status": "recording stopped"}


# def run_fastapi():
# uvicorn.run(remote_app, host="0.0.0.0", port=8000)


def imaging_source_recorder():
    with ic4.Library.init_context():
        app = QApplication()
        app.setApplicationName("imaging-source-recorder")
        app.setApplicationDisplayName("Imaging Source Recorder")
        app.setStyle("fusion")

        main_window = MainWindow()
        # global app_interface
        # app_interface = AppInterface(main_window)

        main_window.show()
        # # Start FastAPI in a separate thread
        # api_thread = threading.Thread(target=run_fastapi, daemon=True)
        # api_thread.start()
        app.exec()


if __name__ == "__main__":
    imaging_source_recorder()
