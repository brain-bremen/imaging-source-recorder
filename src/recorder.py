from abc import ABC, abstractmethod
from os import PathLike

RECORDINGS_DIR = "recordings"


class RecorderSettings(ABC):
    pass


class VideoRecorderInterface(ABC):
    @abstractmethod
    def start_recording(
        self,
        file_name: str | PathLike,
        frame_rate: float | None = None,
        triggered_mode: bool = False,
        settings: RecorderSettings | None = None,
    ):
        pass

    @abstractmethod
    def enable_triggered_recording_mode(self, enable: bool = True):
        pass

    @abstractmethod
    def stop_recording(self):
        pass

    @abstractmethod
    def get_number_of_written_frames(self) -> int:
        pass

    @abstractmethod
    def get_frames_per_second(self) -> float:
        pass

    @abstractmethod
    def start_streaming(self):
        pass

    @abstractmethod
    def stop_streaming(self):
        pass

    @abstractmethod
    def toggle_streaming(self):
        pass

    @abstractmethod
    def is_streaming(self) -> bool:
        pass

    @abstractmethod
    def is_recording(self) -> bool:
        pass
