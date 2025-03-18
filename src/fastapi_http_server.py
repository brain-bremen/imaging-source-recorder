import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Callable, Dict
from fastapi.staticfiles import StaticFiles
import os

RECORDINGS_DIR = "recordings"
PORT = 8000

# Ensure the recordings directory exists
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

app = FastAPI()
recordings: Dict[str, Dict] = {}

# Populate recordings with existing mp4 files in the recordings directory
for filename in os.listdir(RECORDINGS_DIR):
    if filename.endswith(".mp4"):
        recording_id = str(len(recordings) + 1)
        recordings[recording_id] = {
            "filename": filename[:-4],  # Remove the .mp4 extension
            "metadata": {},
            "status": "stopped",
        }


# Data models
class StartRecordingRequest(BaseModel):
    filename: str


class StartRecordingResponse(BaseModel):
    message: str
    recording_id: str


class StopRecordingRequest(BaseModel):
    recording_id: str


class StopRecordingResponse(BaseModel):
    message: str
    filename: str


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
@app.post("/recordings/start", response_model=StartRecordingResponse)
async def start_recording(request: StartRecordingRequest):
    if any(recording["status"] == "recording" for recording in recordings.values()):
        raise HTTPException(
            status_code=400, detail="A recording is already in progress"
        )
    recording_id = str(len(recordings) + 1)
    recordings[recording_id] = {
        "filename": request.filename,
        "metadata": {},
        "status": "recording",
    }
    start_recording_func(request.filename)

    # Placeholder for actual recording logic
    return {"message": "Recording started", "recording_id": recording_id}


@app.post("/recordings/stop", response_model=StopRecordingResponse)
async def stop_recording(request: StopRecordingRequest):
    if request.recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording ID not found")
    recordings[request.recording_id]["status"] = "stopped"
    stop_recording_func()

    return {
        "message": "Recording stopped",
        "filename": recordings[request.recording_id]["filename"],
    }


@app.post("/recordings/metadata", response_model=MetadataResponse)
async def add_metadata(request: AddMetadataRequest):
    if request.recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording ID not found")
    recordings[request.recording_id]["metadata"] = request.metadata
    metadata_filename = os.path.join(
        RECORDINGS_DIR, f"{recordings[request.recording_id]['filename']}.json"
    )
    with open(metadata_filename, "w") as metadata_file:
        json.dump(request.metadata, metadata_file)
    return {"message": "Metadata added"}


@app.get("/recordings/{recording_id}", response_model=RecordingResponse)
async def get_recording(recording_id: str):
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording ID not found")
    recording = recordings[recording_id]
    if recording["status"] != "stopped":
        raise HTTPException(status_code=400, detail="Recording is not yet stopped")
    return {
        "recording_id": recording_id,
        "filename": recording["filename"],
        "metadata": recording["metadata"],
        "file_url": f"http://localhost:8000/files/{recording['filename']}.mp4",
    }


@app.get("/recordings", response_model=Dict[str, RecordingResponse])
async def list_recordings():
    available_recordings = {}
    for recording_id, recording in recordings.items():
        if recording["status"] == "stopped":
            available_recordings[recording_id] = {
                "recording_id": recording_id,
                "filename": recording["filename"],
                "metadata": recording["metadata"],
                "file_url": f"http://localhost:8000/files/{recording['filename']}.mp4",
            }
    return available_recordings


# Mount static files route
app.mount("/files", StaticFiles(directory=RECORDINGS_DIR), name="files")


def run_fastapi_server(
    start_func: Callable[[str], None], stop_func: Callable[[], None]
):
    global start_recording_func, stop_recording_func
    start_recording_func = start_func
    stop_recording_func = stop_func
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
