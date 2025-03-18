from enum import Enum
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Callable, Dict
from fastapi.staticfiles import StaticFiles
from recorder import RECORDINGS_DIR
import os

PORT = 8000
HOST = "localhost"


def url_from_filename(filename: str) -> str:
    # strip folder from filename
    filename = os.path.basename(filename)
    return f"http://{HOST}:{PORT}/files/{filename}"


def metadata_filename_from_recording_id(recording_id: str) -> str:
    return f"{recording_id}.metadata.json"


def recording_id_from_video_filename(filename: str) -> str:
    return filename[:-4]


class RecordingStatus(Enum):
    STOPPED = "stopped"
    RECORDING = "recording"


# Ensure the recordings directory exists
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

app = FastAPI()


class Recording(BaseModel):
    recording_id: str  # basename without extension
    video_filename: str
    metadata_filename: str
    metadata: Dict[str, str]
    status: RecordingStatus
    video_url: str
    metadata_url: str | None = None


# Populate recordings with existing mp4 files in the recordings directory
def update_recordings_from_disk() -> Dict[str, Recording]:
    recordings: Dict[str, Recording] = {}
    for filename in os.listdir(RECORDINGS_DIR):
        if filename.endswith(".mp4"):
            recording_id = recording_id_from_video_filename(filename)
            metadata_filename = metadata_filename_from_recording_id(recording_id)
            metadata = {}
            if os.path.exists(os.path.join(RECORDINGS_DIR, metadata_filename)):
                try:
                    with open(
                        os.path.join(RECORDINGS_DIR, metadata_filename)
                    ) as metadata_file:
                        metadata = json.load(metadata_file)
                except Exception as e:
                    msg = f"Failed to load metadata for {filename}: {e}"
                    metadata = {"error": msg}

            recordings[recording_id] = Recording(
                recording_id=recording_id,
                video_filename=filename,
                metadata=metadata,
                status=RecordingStatus.STOPPED,
                video_url=url_from_filename(filename),
                metadata_filename=metadata_filename,
                metadata_url=url_from_filename(metadata_filename)
                if os.path.exists(os.path.join(RECORDINGS_DIR, metadata_filename))
                else None,
            )
    return recordings


recordings: Dict[str, Recording] = update_recordings_from_disk()


# Data models
class StartRecordingRequest(BaseModel):
    filename: str
    metadata: Dict[str, str] = {}


class StopRecordingRequest(BaseModel):
    recording_id: str


class StopRecordingResponse(BaseModel):
    message: str
    recording: Recording


class AddMetadataRequest(BaseModel):
    recording_id: str
    metadata: Dict[str, str]


class MetadataResponse(BaseModel):
    message: str


class RecordingResponse(BaseModel):
    recording_id: str
    filename: str
    metadata: Dict[str, str]
    file_url: str


def start_recording_func(filename: str) -> None:
    return None


def stop_recording_func() -> None:
    return None


# Endpoints
@app.post("/recordings/start", response_model=Recording)
async def start_recording(request: StartRecordingRequest):
    if any(
        recording.status == RecordingStatus.RECORDING
        for recording in recordings.values()
    ):
        raise HTTPException(
            status_code=400, detail="A recording is already in progress"
        )

    # if filename has no extension add .mp4
    if "." not in request.filename:
        request.filename += ".mp4"

    # make sure filename is a valid mp4 file
    if not request.filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Filename must end with .mp4")

    recording_id = recording_id_from_video_filename(request.filename)
    metadata_filename = metadata_filename_from_recording_id(recording_id)
    with open(os.path.join(RECORDINGS_DIR, metadata_filename), "w") as metadata_file:
        json.dump(request.metadata, metadata_file)

    recordings[recording_id] = Recording(
        recording_id=recording_id,
        video_filename=request.filename,
        metadata=request.metadata,
        metadata_filename=metadata_filename,
        status=RecordingStatus.RECORDING,
        video_url=url_from_filename(request.filename),
        metadata_url=url_from_filename(
            metadata_filename_from_recording_id(recording_id)
        ),
    )
    start_recording_func(request.filename)

    return recordings[recording_id]


@app.post("/recordings/stop", response_model=StopRecordingResponse)
async def stop_recording(request: StopRecordingRequest):
    if request.recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording ID not found")
    recordings[request.recording_id].status = RecordingStatus.STOPPED

    stop_recording_func()

    return {
        "message": "Recording stopped",
        "recording": recordings[request.recording_id],
    }


@app.post("/recordings/metadata", response_model=MetadataResponse)
async def add_metadata(request: AddMetadataRequest):
    if request.recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording ID not found")
    recordings[request.recording_id].metadata = request.metadata
    metadata_filename = metadata_filename_from_recording_id(request.recording_id)
    with open(os.path.join(RECORDINGS_DIR, metadata_filename), "w") as metadata_file:
        json.dump(request.metadata, metadata_file)
    return {"message": "Metadata added"}


@app.get("/recordings/{recording_id}", response_model=Recording)
async def get_recording(recording_id: str):
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording ID not found")
    recording = recordings[recording_id]
    if recording.status != RecordingStatus.STOPPED:
        raise HTTPException(status_code=400, detail="Recording is not yet stopped")
    return recordings[recording_id]


@app.get("/recordings", response_model=Dict[str, Recording])
async def list_recordings():
    available_recordings = {}
    # update_recordings_from_disk()

    for recording_id, recording in recordings.items():
        if recording.status == RecordingStatus.STOPPED:
            available_recordings[recording_id] = recording

    return available_recordings


# Mount static files route
app.mount("/files", StaticFiles(directory=RECORDINGS_DIR), name="files")


def run_http_server(start_func: Callable[[str], None], stop_func: Callable[[], None]):
    global start_recording_func, stop_recording_func
    start_recording_func = start_func
    stop_recording_func = stop_func
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    run_http_server(start_recording_func, stop_recording_func)
