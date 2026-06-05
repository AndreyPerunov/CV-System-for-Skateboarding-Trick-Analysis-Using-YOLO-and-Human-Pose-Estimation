"""FastAPI backend for skate trick analysis.

Three endpoints:
    GET  /health         → {"status": "ok"}
    GET  /stats          → request counter snapshot
    POST /analyze_video  → multipart upload → AnalysisResponse

Run locally:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from skate_analysis import AnalysisResponse, analyze, load_models


class RequestStats:
    """Only /analyze_video is tracked."""
    def __init__(self) -> None:
        self._lock = Lock()
        self._analyze_video = 0
        self._analyze_video_failed = 0

    def hit_analyze(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self._analyze_video += 1
            else:
                self._analyze_video_failed += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "total_requests":         self._analyze_video + self._analyze_video_failed,
                "analyze_video_success":  self._analyze_video,
                "analyze_video_failed":   self._analyze_video_failed,
            }


stats = RequestStats()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_models()
    yield


app = FastAPI(
    title="Skate Trick Analysis API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stats")
def get_stats() -> dict:
    return stats.snapshot()


_ALLOWED_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@app.post("/analyze_video", response_model=AnalysisResponse)
async def analyze_video(
    file: UploadFile = File(...),
    is_regular: bool = True,
    board_length_cm: float = 81.0,
    height_threshold_cm: float = 3.0,
    frame_step: int = 1,
) -> AnalysisResponse:
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in _ALLOWED_SUFFIXES:
        stats.hit_analyze(ok=False)
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported video format: {suffix!r}. Allowed: {sorted(_ALLOWED_SUFFIXES)}",
        )

    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(tmp_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        result = analyze(
            tmp_path,
            is_regular=is_regular,
            board_length_cm=board_length_cm,
            height_threshold_cm=height_threshold_cm,
            frame_step=frame_step,
        )
        result["video_path"] = file.filename or ""
    except Exception as exc:
        stats.hit_analyze(ok=False)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    stats.hit_analyze(ok=True)
    return AnalysisResponse.model_validate(result)
