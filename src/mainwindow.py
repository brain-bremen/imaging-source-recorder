from threading import Lock
from imaging_source_recorder import ImagingSourceRecorder

from PySide6.QtCore import (
    QStandardPaths,
    QDir,
    QTimer,
    QEvent,
    QFileInfo,
    Qt,
    QCoreApplication,
)
from PySide6.QtGui import QAction, QKeySequence, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QLabel,
    QApplication,
    QFileDialog,
    QToolBar,
)

import imagingcontrol4 as ic4

from resourceselector import ResourceSelector

GOT_PHOTO_EVENT = QEvent.Type(QEvent.Type.User + 1)
DEVICE_LOST_EVENT = QEvent.Type(QEvent.Type.User + 2)


class GotPhotoEvent(QEvent):
    def __init__(self, buffer: ic4.ImageBuffer):
        QEvent.__init__(self, GOT_PHOTO_EVENT)
        self.image_buffer = buffer


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        # Make sure the %appdata%/demoapp directory exists
        appdata_directory = QStandardPaths.writableLocation(
            QStandardPaths.AppDataLocation
        )
        QDir(appdata_directory).mkpath(".")

        self.save_pictures_directory = QStandardPaths.writableLocation(
            QStandardPaths.PicturesLocation
        )
        self.save_videos_directory = QStandardPaths.writableLocation(
            QStandardPaths.MoviesLocation
        )

        self.device_file = appdata_directory + "/device.json"
        self.codec_config_file = appdata_directory + "/codecconfig.json"

        self.shoot_photo_mutex = Lock()
        self.shoot_photo = False

        self.recorder = ImagingSourceRecorder()

        self.recorder.grabber.event_add_device_lost(
            lambda g: QApplication.postEvent(self, QEvent(DEVICE_LOST_EVENT))
        )

        self.property_dialog = None

        self.createUI()

        try:
            self.display = self.video_widget.as_display()
            self.display.set_render_position(ic4.DisplayRenderPosition.STRETCH_CENTER)
        except Exception as e:
            QMessageBox.critical(self, "", f"{e}", QMessageBox.StandardButton.Ok)

        if QFileInfo.exists(self.device_file):
            try:
                self.recorder.load_state_from_file(self.device_file)
                self.onDeviceOpened()
            except ic4.IC4Exception as e:
                QMessageBox.information(
                    self,
                    "",
                    f"Loading last used device failed: {e}",
                    QMessageBox.StandardButton.Ok,
                )

        if QFileInfo.exists(self.codec_config_file):
            try:
                self.recorder.video_writer.property_map.deserialize_from_file(
                    self.codec_config_file
                )
            except ic4.IC4Exception as e:
                QMessageBox.information(
                    self,
                    "",
                    f"Loading last codec configuration failed: {e}",
                    QMessageBox.StandardButton.Ok,
                )

        self.updateControls()

    def createUI(self):
        self.resize(1024, 768)

        selector = ResourceSelector()

        self.device_select_act = QAction(
            selector.loadIcon("images/camera.png"), "&Select", self
        )
        self.device_select_act.setStatusTip("Select a video capture device")
        self.device_select_act.setShortcut(QKeySequence.Open)
        self.device_select_act.triggered.connect(self.onSelectDevice)

        self.device_properties_act = QAction(
            selector.loadIcon("images/imgset.png"), "&Properties", self
        )
        self.device_properties_act.setStatusTip("Show device property dialog")
        self.device_properties_act.triggered.connect(self.onDeviceProperties)

        self.device_driver_properties_act = QAction("&Driver Properties", self)
        self.device_driver_properties_act.setStatusTip(
            "Show device driver property dialog"
        )
        self.device_driver_properties_act.triggered.connect(
            self.onDeviceDriverProperties
        )

        self.trigger_mode_act = QAction(
            selector.loadIcon("images/triggermode.png"), "&Trigger Mode", self
        )
        self.trigger_mode_act.setStatusTip("Enable and disable trigger mode")
        self.trigger_mode_act.setCheckable(True)
        self.trigger_mode_act.triggered.connect(self.onToggleTriggerMode)

        self.start_live_act = QAction(
            selector.loadIcon("images/livestream.png"), "&Live Stream", self
        )
        self.start_live_act.setStatusTip("Start and stop the live stream")
        self.start_live_act.setCheckable(True)
        self.start_live_act.triggered.connect(self.startStopStream)

        self.shoot_photo_act = QAction(
            selector.loadIcon("images/photo.png"), "&Shoot Photo", self
        )
        self.shoot_photo_act.setStatusTip("Shoot and save a photo")
        self.shoot_photo_act.triggered.connect(self.onShootPhoto)

        self.record_start_act = QAction(
            selector.loadIcon("images/recordstart.png"), "&Capture Video", self
        )
        self.record_start_act.setToolTip("Capture vidoeo into MP4 file")
        self.record_start_act.setCheckable(True)
        self.record_start_act.triggered.connect(self.onStartStopCaptureVideo)

        self.record_pause_act = QAction(
            selector.loadIcon("images/recordpause.png"), "&Pause Capture Video", self
        )
        self.record_pause_act.setStatusTip("Pause video capture")
        self.record_pause_act.setCheckable(True)
        self.record_pause_act.triggered.connect(self.onPauseCaptureVideo)

        self.record_stop_act = QAction(
            selector.loadIcon("images/recordstop.png"), "&Stop Capture Video", self
        )
        self.record_stop_act.setStatusTip("Stop video capture")
        self.record_stop_act.triggered.connect(self.onStopCaptureVideo)

        self.codec_property_act = QAction(
            selector.loadIcon("images/gear.png"), "&Codec Properties", self
        )
        self.codec_property_act.setStatusTip("Configure the video codec")
        self.codec_property_act.triggered.connect(self.onCodecProperties)

        self.close_device_act = QAction("Close", self)
        self.close_device_act.setStatusTip("Close the currently opened device")
        self.close_device_act.setShortcuts(QKeySequence.Close)
        self.close_device_act.triggered.connect(self.onCloseDevice)

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut(QKeySequence.Quit)
        exit_act.setStatusTip("Exit program")
        exit_act.triggered.connect(self.close)

        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(exit_act)

        device_menu = self.menuBar().addMenu("&Device")
        device_menu.addAction(self.device_select_act)
        device_menu.addAction(self.device_properties_act)
        device_menu.addAction(self.device_driver_properties_act)
        device_menu.addAction(self.trigger_mode_act)
        device_menu.addAction(self.start_live_act)
        device_menu.addSeparator()
        device_menu.addAction(self.close_device_act)

        capture_menu = self.menuBar().addMenu("&Capture")
        capture_menu.addAction(self.shoot_photo_act)
        capture_menu.addAction(self.record_start_act)
        capture_menu.addAction(self.record_pause_act)
        capture_menu.addAction(self.record_stop_act)
        capture_menu.addAction(self.codec_property_act)

        toolbar = QToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        toolbar.addAction(self.device_select_act)
        toolbar.addAction(self.device_properties_act)
        toolbar.addSeparator()
        toolbar.addAction(self.trigger_mode_act)
        toolbar.addSeparator()
        toolbar.addAction(self.start_live_act)
        toolbar.addSeparator()
        toolbar.addAction(self.shoot_photo_act)
        toolbar.addSeparator()
        toolbar.addAction(self.record_start_act)
        toolbar.addAction(self.record_pause_act)
        toolbar.addAction(self.record_stop_act)
        toolbar.addAction(self.codec_property_act)

        self.video_widget = ic4.pyside6.DisplayWidget()
        self.video_widget.setMinimumSize(640, 480)
        self.setCentralWidget(self.video_widget)

        self.statusBar().showMessage("Ready")
        self.statistics_label = QLabel("", self.statusBar())
        self.statusBar().addPermanentWidget(self.statistics_label)
        self.statusBar().addPermanentWidget(QLabel("  "))
        self.camera_label = QLabel(self.statusBar())
        self.statusBar().addPermanentWidget(self.camera_label)

        self.update_statistics_timer = QTimer()
        self.update_statistics_timer.timeout.connect(self.onUpdateStatisticsTimer)
        self.update_statistics_timer.start()

    def onCloseDevice(self):
        if self.recorder.grabber.is_streaming:
            self.startStopStream()

        try:
            self.recorder.grabber.device_close()
        except:
            pass

        self.device_property_map = None
        self.display.display_buffer(None)

        self.updateControls()

    def closeEvent(self, ev: QCloseEvent):
        if self.recorder.grabber.is_streaming:
            self.recorder.grabber.stream_stop()

        if self.recorder.grabber.is_device_valid:
            self.recorder.grabber.device_save_state_to_file(self.device_file)

    def customEvent(self, ev: QEvent):
        if ev.type() == DEVICE_LOST_EVENT:
            self.onDeviceLost()
        elif ev.type() == GOT_PHOTO_EVENT:
            self.savePhoto(ev.image_buffer)

    def onSelectDevice(self):
        dlg = ic4.pyside6.DeviceSelectionDialog(self.recorder.grabber, parent=self)
        if dlg.exec() == 1:
            if not self.property_dialog is None:
                self.property_dialog.update_grabber(self.recorder.grabber)

            self.onDeviceOpened()
        self.updateControls()

    def onDeviceProperties(self):
        if self.property_dialog is None:
            self.property_dialog = ic4.pyside6.PropertyDialog(
                self.recorder.grabber, parent=self, title="Device Properties"
            )
            # set default vis

        self.property_dialog.show()

    def onDeviceDriverProperties(self):
        dlg = ic4.pyside6.PropertyDialog(
            self.recorder.grabber.driver_property_map,
            parent=self,
            title="Device Driver Properties",
        )
        # set default vis

        dlg.exec()

        self.updateControls()

    def onToggleTriggerMode(self):
        try:
            self.recorder.enable_trigger_mode(self.trigger_mode_act.isChecked())

        except ic4.IC4Exception as e:
            QMessageBox.critical(self, "", f"{e}", QMessageBox.StandardButton.Ok)

    def onShootPhoto(self):
        with self.shoot_photo_mutex:
            self.shoot_photo = True

    def onUpdateStatisticsTimer(self):
        if not self.recorder.grabber.is_device_valid:
            return

        try:
            stats = self.recorder.grabber.stream_statistics
            text = f"Frames Delivered: {stats.sink_delivered} Dropped: {stats.device_transmission_error}/{stats.device_underrun}/{stats.transform_underrun}/{stats.sink_underrun}"
            self.statistics_label.setText(text)
            tooltip = (
                f"Frames Delivered: {stats.sink_delivered}"
                f"Frames Dropped:"
                f"  Device Transmission Error: {stats.device_transmission_error}"
                f"  Device Underrun: {stats.device_underrun}"
                f"  Transform Underrun: {stats.transform_underrun}"
                f"  Sink Underrun: {stats.sink_underrun}"
            )
            self.statistics_label.setToolTip(tooltip)
        except ic4.IC4Exception:
            pass

    def onDeviceLost(self):
        QMessageBox.warning(
            self,
            "",
            f"The video capture device is lost!",
            QMessageBox.StandardButton.Ok,
        )

        # stop video

        self.updateCameraLabel()
        self.updateControls()

    def onDeviceOpened(self):
        self.device_property_map = self.recorder.grabber.device_property_map

        trigger_mode = self.device_property_map.find(ic4.PropId.TRIGGER_MODE)
        trigger_mode.event_add_notification(self.updateTriggerControl)

        self.updateCameraLabel()

        # if start_stream_on_open
        self.startStopStream()

    def updateTriggerControl(self, p: ic4.Property):
        if not self.recorder.grabber.is_device_valid:
            self.trigger_mode_act.setChecked(False)
            self.trigger_mode_act.setEnabled(False)
        else:
            try:
                self.trigger_mode_act.setChecked(
                    self.device_property_map.get_value_str(ic4.PropId.TRIGGER_MODE)
                    == "On"
                )
                self.trigger_mode_act.setEnabled(True)
            except ic4.IC4Exception:
                self.trigger_mode_act.setChecked(False)
                self.trigger_mode_act.setEnabled(False)

    def updateControls(self):
        if not self.recorder.grabber.is_device_open:
            self.statistics_label.clear()

        self.device_properties_act.setEnabled(self.recorder.grabber.is_device_valid)
        self.device_driver_properties_act.setEnabled(
            self.recorder.grabber.is_device_valid
        )
        self.start_live_act.setEnabled(self.recorder.grabber.is_device_valid)
        self.start_live_act.setChecked(self.recorder.grabber.is_streaming)
        self.shoot_photo_act.setEnabled(self.recorder.grabber.is_streaming)
        self.record_stop_act.setEnabled(self.recorder.capture_to_video)
        self.record_pause_act.setChecked(self.recorder.video_capture_pause)
        self.record_start_act.setChecked(self.recorder.capture_to_video)
        self.close_device_act.setEnabled(self.recorder.grabber.is_device_open)

        self.updateTriggerControl(None)

    def updateCameraLabel(self):
        try:
            info = self.recorder.grabber.device_info
            self.camera_label.setText(f"{info.model_name} {info.serial}")
        except ic4.IC4Exception:
            self.camera_label.setText("No Device")

    def onPauseCaptureVideo(self):
        self.recorder.video_capture_pause = self.record_pause_act.isChecked()

    def onStartStopCaptureVideo(self):
        if self.recorder.capture_to_video:
            self.stopCapturevideo()
            return

        filters = ["MP4 Video Files (*.mp4)"]

        dialog = QFileDialog(self, "Capture Video")
        dialog.setNameFilters(filters)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setDirectory(self.save_videos_directory)

        if dialog.exec():
            full_path = dialog.selectedFiles()[0]
            self.save_videos_directory = QFileInfo(full_path).absolutePath()

            fps = float(25)
            try:
                fps = self.recorder.get_frame_rate()
            except:
                pass

            try:
                self.recorder.video_writer.begin_file(
                    full_path, self.sink.output_image_type, fps
                )
            except ic4.IC4Exception as e:
                QMessageBox.critical(self, "", f"{e}", QMessageBox.StandardButton.Ok)

            self.recorder.capture_to_video = True

        self.updateControls()

    def onStopCaptureVideo(self):
        self.recorder.stop_capture_video()
        self.updateControls()

    def onCodecProperties(self):
        dlg = ic4.pyside6.PropertyDialog(
            self.recorder.video_writer.property_map, self, "Codec Settings"
        )
        # set default vis
        if dlg.exec() == 1:
            self.recorder.video_writer.property_map.serialize_to_file(
                self.codec_config_file
            )

    def startStopStream(self):
        try:
            self.recorder.start_stop_stream(self.display)

        except ic4.IC4Exception as e:
            QMessageBox.critical(self, "", f"{e}", QMessageBox.StandardButton.Ok)

        self.updateControls()

    def savePhoto(self, image_buffer: ic4.ImageBuffer):
        filters = [
            "Bitmap(*.bmp)",
            "JPEG (*.jpg)",
            "Portable Network Graphics (*.png)",
            "TIFF (*.tif)",
        ]

        dialog = QFileDialog(self, "Save Photo")
        dialog.setNameFilters(filters)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setDirectory(self.save_pictures_directory)

        if dialog.exec():
            selected_filter = dialog.selectedNameFilter()

            full_path = dialog.selectedFiles()[0]
            self.save_pictures_directory = QFileInfo(full_path).absolutePath()

            try:
                if selected_filter == filters[0]:
                    image_buffer.save_as_bmp(full_path)
                elif selected_filter == filters[1]:
                    image_buffer.save_as_jpeg(full_path)
                elif selected_filter == filters[2]:
                    image_buffer.save_as_png(full_path)
                else:
                    image_buffer.save_as_tiff(full_path)
            except ic4.IC4Exception as e:
                QMessageBox.critical(self, "", f"{e}", QMessageBox.StandardButton.Ok)
