import imagingcontrol4 as ic4


class ImagingSourceRecorder:
    def __init__(self):
        self.capture_to_video = False
        self.video_capture_pause = False
        self.video_writer = ic4.VideoWriter(ic4.VideoWriterType.MP4_H264)

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
                # self.device_property_map.connect_chunkdata(buf)

                # with self.shoot_photo_mutex:
                #     if self.shoot_photo:
                #         self.shoot_photo = False

                #         # Send an event to the main thread with a reference to
                #         # the main thread of our GUI.
                #         QApplication.postEvent(self, GotPhotoEvent(buf))

                if self.capture_to_video and not self.video_capture_pause:
                    try:
                        self.video_writer.add_frame(buf)
                    except ic4.IC4Exception as ex:
                        pass

        self.grabber = ic4.Grabber()

        self.sink = ic4.QueueSink(Listener())

    def load_state_from_file(self, filename: str):
        self.grabber.device_open_from_state_file(filename)

    def get_frame_rate(self) -> float:
        return self.grabber.device_property_map.get_value_float(
            ic4.PropId.ACQUISITION_FRAME_RATE
        )

    def enable_trigger_mode(self, enable: bool):
        self.grabber.device_property_map.set_value_bool(
            ic4.PropId.TRIGGER_MODE,
            enable,
        )

    def stop_capture_video(self):
        self.capture_to_video = False
        self.video_writer.finish_file()

    def start_stop_stream(self, display: ic4.Display):
        if self.grabber.is_device_valid:
            if self.grabber.is_streaming:
                self.grabber.stream_stop()
                if self.capture_to_video:
                    self.stop_capture_video()
            else:
                self.grabber.stream_setup(self.sink, display)
