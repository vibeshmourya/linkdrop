"""
LinkDrop - Main Download Coordinator
"""
import uuid
import time
import logging
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

from services.video_downloader import download_video
from services.audio_downloader import download_audio
from services.image_downloader import download_image
from services.gallery_downloader import download_gallery
from utils.cleanup import cleanup_expired_files

logger = logging.getLogger("downloader")

# In-memory transient job tracking (No database)
JOB_STORE: Dict[str, Dict[str, Any]] = {}
JOB_LOCK = threading.Lock()

# Thread pool for asynchronous downloads
DOWNLOAD_EXECUTOR = ThreadPoolExecutor(max_workers=4)

def update_job_progress(job_id: str, data: dict):
    with JOB_LOCK:
        if job_id in JOB_STORE:
            JOB_STORE[job_id].update(data)
            JOB_STORE[job_id]["updated_at"] = time.time()

def run_download_task(
    job_id: str,
    media_type: str,
    url: str,
    title: str,
    quality_or_format: str,
    extra_data: Optional[dict] = None
):
    """
    Worker task running in thread pool.
    """
    try:
        update_job_progress(job_id, {"status": "downloading", "percent": 5.0, "message": "Starting download..."})

        def progress_hook(info: dict):
            update_job_progress(job_id, info)

        result_path: Optional[Path] = None

        if media_type == "video":
            # Extract height from quality e.g. "video_1080" -> 1080
            height = None
            if quality_or_format and "video_" in quality_or_format:
                try:
                    height = int(quality_or_format.replace("video_", ""))
                except ValueError:
                    height = None
            result_path = download_video(url, title, height=height, progress_callback=progress_hook)

        elif media_type == "audio":
            # Extract format e.g. "audio_mp3" -> "mp3"
            audio_fmt = quality_or_format.replace("audio_", "") if quality_or_format else "mp3"
            result_path = download_audio(url, title, audio_format=audio_fmt, progress_callback=progress_hook)

        elif media_type == "image":
            img_fmt = quality_or_format.replace("image_", "") if quality_or_format else "jpg"
            img_url = (extra_data or {}).get("direct_download_url") or (extra_data or {}).get("thumbnail") or url
            result_path = download_image(img_url, title, target_format=img_fmt, progress_callback=progress_hook)

        elif media_type == "gallery":
            items = (extra_data or {}).get("items", [])
            result_path = download_gallery(items, title, progress_callback=progress_hook)

        else:
            # Default to video
            result_path = download_video(url, title, progress_callback=progress_hook)

        if not result_path or not result_path.exists():
            raise RuntimeError("The media file could not be generated. Please try again.")

        file_size = result_path.stat().st_size
        if file_size <= 0:
            result_path.unlink(missing_ok=True)
            raise RuntimeError("The downloaded file is 0 bytes.")

        update_job_progress(job_id, {
            "status": "completed",
            "percent": 100.0,
            "file_path": str(result_path),
            "filename": result_path.name,
            "filesize": file_size,
            "message": "Download complete!"
        })

    except Exception as e:
        logger.error(f"Download failed for job {job_id}: {e}", exc_info=True)
        user_msg = str(e)
        if "login" in user_msg.lower() or "private" in user_msg.lower():
            user_msg = "This media could not be downloaded because it is private or requires authentication."
        elif "drm" in user_msg.lower():
            user_msg = "This media is protected by DRM and cannot be downloaded."
        else:
            user_msg = "This media could not be downloaded. The source may be unavailable, protected, or unsupported."

        update_job_progress(job_id, {
            "status": "failed",
            "error": user_msg
        })

def create_download_job(
    url: str,
    title: str,
    media_type: str,
    quality_or_format: str,
    extra_data: Optional[dict] = None
) -> str:
    """
    Creates a new transient download job and queues it in background executor.
    """
    job_id = uuid.uuid4().hex[:12]
    with JOB_LOCK:
        JOB_STORE[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "percent": 0.0,
            "speed": 0.0,
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "file_path": None,
            "filename": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time()
        }

    # Asynchronously dispatch
    DOWNLOAD_EXECUTOR.submit(
        run_download_task,
        job_id,
        media_type,
        url,
        title,
        quality_or_format,
        extra_data
    )

    # Periodic cleanup of old entries
    cleanup_expired_jobs()

    return job_id

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    with JOB_LOCK:
        return JOB_STORE.get(job_id)

def cleanup_expired_jobs():
    """Removes in-memory job records older than 1 hour and calls disk cleaner."""
    now = time.time()
    with JOB_LOCK:
        to_del = [jid for jid, info in JOB_STORE.items() if now - info.get("created_at", 0) > 3600]
        for jid in to_del:
            del JOB_STORE[jid]

    try:
        cleanup_expired_files()
    except Exception:
        pass
