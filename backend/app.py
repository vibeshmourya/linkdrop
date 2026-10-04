"""
LinkDrop - FastAPI Application
"""
import os
import sys
import shutil
import logging
from pathlib import Path

# Add backend directory to sys.path
CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from core.config import FRONTEND_DIR, HOST, PORT
from core.validators import validate_media_url
from services.media_analyzer import analyze_url
from services.downloader import create_download_job, get_job_status
from utils.cleanup import cleanup_expired_files, delete_job_files

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LinkDrop backend starting up...")
    cleanup_expired_files()
    yield
    logger.info("LinkDrop backend shutting down...")

app = FastAPI(
    title="LinkDrop",
    description="Simple link-based media downloader",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="Media URL to analyze")

class DownloadRequest(BaseModel):
    url: str = Field(..., description="Original or direct media URL")
    title: str = Field(..., description="Clean media title")
    media_type: str = Field("video", description="video, audio, image, or gallery")
    quality_or_format: str = Field("video_720", description="Selected quality ID or format ID")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

# Endpoints
@app.get("/api/health")
async def health_check():
    """Returns server and engine health status."""
    import yt_dlp
    ffmpeg_path = shutil.which("ffmpeg")
    return {
        "status": "ok",
        "yt_dlp_version": yt_dlp.version.__version__,
        "ffmpeg_available": bool(ffmpeg_path)
    }

@app.post("/api/analyze")
async def api_analyze(payload: AnalyzeRequest):
    """
    Validates URL security, identifies source, and extracts downloadable media formats.
    """
    is_safe, error_msg, normalized_url = validate_media_url(payload.url)
    if not is_safe:
        return JSONResponse(status_code=400, content={"success": False, "error": error_msg})

    try:
        media_data = analyze_url(normalized_url)
        return {"success": True, "data": media_data}
    except ValueError as ve:
        return JSONResponse(status_code=400, content={"success": False, "error": str(ve)})
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "This URL could not be processed. The resource may be private, protected, or currently unavailable."
            }
        )

@app.post("/api/download")
async def api_download(payload: DownloadRequest):
    """
    Starts an asynchronous download job and returns a job_id for progress tracking.
    """
    is_safe, error_msg, normalized_url = validate_media_url(payload.url)
    if not is_safe:
        return JSONResponse(status_code=400, content={"success": False, "error": error_msg})

    try:
        job_id = create_download_job(
            url=normalized_url,
            title=payload.title,
            media_type=payload.media_type,
            quality_or_format=payload.quality_or_format,
            extra_data=payload.extra_data
        )
        return {"success": True, "job_id": job_id}
    except Exception as e:
        logger.error(f"Download initiation failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to start download job. Please try again."}
        )

@app.get("/api/progress/{job_id}")
async def api_progress(job_id: str):
    """
    Returns current download percentage, transfer speed, and status.
    """
    job_info = get_job_status(job_id)
    if not job_info:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Download job not found or expired."}
        )

    return {
        "success": True,
        "job_id": job_id,
        "status": job_info.get("status"),
        "percent": job_info.get("percent", 0.0),
        "speed": job_info.get("speed", 0.0),
        "downloaded_bytes": job_info.get("downloaded_bytes", 0),
        "total_bytes": job_info.get("total_bytes", 0),
        "filename": job_info.get("filename"),
        "message": job_info.get("message"),
        "error": job_info.get("error")
    }

MIME_MAP = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".zip": "application/zip",
}

@app.api_route("/api/file/{job_id}", methods=["GET", "HEAD"])
async def api_file(job_id: str):
    """
    Transfers the finished file to the user's browser as a verified download attachment.
    Supports both GET and HEAD requests and enforces proper Content-Type & Content-Length.
    """
    job_info = get_job_status(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Download job not found or expired.")

    if job_info.get("status") != "completed":
        raise HTTPException(
            status_code=409,
            detail="Media file is still processing. Please wait until download completes."
        )

    file_path_str = job_info.get("file_path")
    if not file_path_str:
        raise HTTPException(status_code=404, detail="File path record is missing.")

    file_path = Path(file_path_str)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="The file is no longer available on the server.")

    file_size = file_path.stat().st_size
    if file_size == 0:
        raise HTTPException(status_code=500, detail="The generated media file is 0 bytes.")

    ext = file_path.suffix.lower()
    media_type = MIME_MAP.get(ext, "application/octet-stream")
    download_filename = job_info.get("filename") or file_path.name

    # Set explicit download headers for browser compatibility
    headers = {
        "Content-Length": str(file_size),
        "Content-Disposition": f'attachment; filename="{download_filename}"',
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }

    return FileResponse(
        path=file_path,
        filename=download_filename,
        media_type=media_type,
        headers=headers
    )

# Static file serving for Frontend UI
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
