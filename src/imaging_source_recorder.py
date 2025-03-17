import time
import imagingcontrol4 as ic4
from recorder import VideoRecorderInterface


class ImagingSourceRecorder(VideoRecorderInterface):
    # interface methods
    def get_frame_rate(self) -> float:
        return self.grabber.device_property_map.get_value_float(
            ic4.PropId.ACQUISITION_FRAME_RATE
        )

    def start_streaming(self, display: ic4.Display | None = None):
        if not self.grabber.is_device_valid:
            return

        if not self.grabber.is_streaming:
            self.grabber.stream_setup(self.sink, display)
            self.stream_start_time = time.perf_counter_ns()

    def enable_triggered_recording_mode(self, enable: bool = True):
        self.grabber.device_property_map.try_set_value(
            ic4.PropId.TRIGGER_MODE,
            enable,
        )

    def get_triggered_record_mode(self) -> bool:
        return self.grabber.device_property_map.get_value_bool(ic4.PropId.TRIGGER_MODE)

    def is_streaming(self) -> bool:
        return self.grabber.is_streaming

    def is_recording(self) -> bool:
        return self.capture_to_video

    def get_filename(self) -> str:
        if not self.capture_to_video:
            return ""
        return self.filename

    def __init__(self):
        self.capture_to_video = False
        self.video_capture_pause = False
        self.video_writer = ic4.VideoWriter(ic4.VideoWriterType.MP4_H264)
        self.stream_start_time = 0

        class Listener(ic4.QueueSinkListener):
            def sink_connected(
                self,
                sink: ic4.QueueSink,
                image_type: ic4.ImageType,
                min_buffers_required: int,
            ) -> bool:
                # Allocate more buffers than suggested, because we temporarily take some buffers
                # out of circulation when saving an image or video files.
                sink.alloc_and_queue_buffers(min_buffers_required + 2)
                return True

            def sink_disconnected(self, sink: ic4.QueueSink):
                pass

            def frames_queued(listener, sink: ic4.QueueSink):
                buf = sink.pop_output_buffer()

                # Connect the buffer's chunk data to the device's property map
                # This allows for properties backed by chunk data to be updated
                self.grabber.device_property_map.connect_chunkdata(buf)

                if self.capture_to_video and not self.video_capture_pause:
                    try:
                        self.video_writer.add_frame(buf)
                    except ic4.IC4Exception as ex:
                        pass

        self.grabber = ic4.Grabber()

        self.sink = ic4.QueueSink(Listener())

    def load_state_from_file(self, filename: str):
        self.grabber.device_open_from_state_file(filename)

    def start_recording(
        self, file_name, frame_rate=None, triggered_mode=False, settings=None
    ):
        if not self.grabber.is_device_valid:
            self.capture_to_video = False
            return

        try:
            self.enable_triggered_recording_mode(triggered_mode)

            if not self.is_streaming():
                self.start_streaming()

            if frame_rate is None:
                frame_rate = self.grabber.device_property_map.get_value_float(
                    ic4.PropId.ACQUISITION_FRAME_RATE
                )

            self.video_writer.begin_file(
                path=file_name,
                image_type=self.sink.output_image_type,
                frame_rate=frame_rate,
            )
            self.capture_to_video = True

            self.filename = file_name
        except ic4.IC4Exception as ex:
            self.capture_to_video = False
            raise ex

    def stop_recording(self):
        self.capture_to_video = False
        self.video_writer.finish_file()

    def stop_streaming(self):
        if not self.grabber.is_device_valid:
            return

        if self.grabber.is_streaming:
            self.grabber.stream_stop()

    def toggle_streaming(self, display: ic4.Display | None = None):
        if self.grabber.is_device_valid:
            if self.grabber.is_streaming:
                self.grabber.stream_stop()
            else:
                self.start_streaming(display)

    def pause_recording(self):
        self.video_capture_pause = True

    def get_number_of_written_frames(self) -> int:
        return self.grabber.stream_statistics.sink_delivered

    def get_frames_per_second(self):
        return (
            self.grabber.stream_statistics.sink_delivered
            / (time.perf_counter_ns() - self.stream_start_time)
            * 1e9
        )

    def __del__(self):
        self.grabber.device_close()
