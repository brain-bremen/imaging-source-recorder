# Imaging Source Recorder

A Qt-desktop app for recording from an Imaging Source Camera. Based on the [PySide6 demoapp](https://github.com/TheImagingSource/ic4-examples), licensed with the APACHE license.

![Screenshot](images/screenshot.png)

## Design goals

- [x] Provide desktop app to manually start/stop triggered recordings from Imaging Source Cameras
- [ ] Allow starting/stopping of recordings with a given filename via RPC
- [ ] Add metadata to recordings
- [ ] Add retreiving last recorded file via HTTP

## Execute the GUI with uv

```
uvx --from git+https://github.com/brain-bremen/imaging-source-recorder imaging-source-recorder-gui
```


