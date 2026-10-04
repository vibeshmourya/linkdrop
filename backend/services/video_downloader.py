"""
LinkDrop - Video Downloader Service
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Callable, Optional
import yt_dlp
from core.config import DOWNLOADS_DIR, MAX_DOWNLOAD_SIZE_BYTES
from utils.filenames import get_safe_destination_path, get_temp_workspace

logger = logging.getLogger("video_downloader")

INCOMPLETE_EXTENSIONS = {".part", ".ytdl", ".tmp", ".crdownload"}

def download_video(
    url: str,
    title: str,
    height: Optional[int] = None,
    progress_callback: Optional[Callable[[dict], None]] = None
) -> Path:
    """
    Downloads video using yt-dlp and FFmpeg, ensuring a complete, non-zero-byte MP4 file.
    """
    dest_path, filename = get_safe_destination_path(title, "mp4", target_dir=DOWNLOADS_DIR)
    temp_dir = get_temp_workspace(dest_path.stem)
    out_tmpl = str(temp_dir / "video_stream.%(ext)s")

    # Format selector: best video (up to height) + best audio, with fallback
    if height:
        fmt = (
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )
    else:
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

    def ydl_progress_hook(d):
        if not progress_callback:
            return
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            percent = (downloaded / total * 100) if total > 0 else 0
            progress_callback({
                "status": "downloading",
                "percent": min(round(percent, 1), 95.0),
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "speed": round(speed / (1024 * 1024), 2) if speed else 0,
                "eta": eta
            })
        elif status == "finished":
            progress_callback({
                "status": "processing",
                "percent": 96.0,
                "message": "Finalizing video and audio with FFmpeg..."
            })

    ydl_opts = {
        "format": fmt,
        "outtmpl": out_tmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [ydl_progress_hook],
        "max_filesize": MAX_DOWNLOAD_SIZE_BYTES,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(f"yt-dlp video download error: {e}", exc_info=True)
        # Clean temp directory on failure
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Video download failed: {str(e)}")

    if progress_callback:
        progress_callback({
            "status": "processing",
            "percent": 98.0,
            "message": "Verifying complete video file..."
        })

    # Search for the final merged file in temp workspace
    # First priority: video_stream.mp4
    expected_mp4 = temp_dir / "video_stream.mp4"
    candidate_file: Optional[Path] = None

    if expected_mp4.exists() and expected_mp4.stat().st_size > 0:
        candidate_file = expected_mp4
    else:
        # Search all generated files excluding any incomplete or partial extensions
        valid_files = [
            f for f in temp_dir.glob("*.*")
            if f.is_file()
            and f.suffix.lower() not in INCOMPLETE_EXTENSIONS
            and not f.name.endswith(".part")
            and f.stat().st_size > 0
        ]

        if not valid_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("No complete video file was generated. The stream may be incomplete or protected.")

        # Pick the largest non-partial file (the merged video)
        valid_files.sort(key=lambda p: p.stat().st_size, reverse=True)
        candidate_file = valid_files[0]

    # Verify candidate file size and readability
    file_size = candidate_file.stat().st_size
    if file_size == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("Generated video file is empty (0 bytes).")

    # Ensure file is readable and not still locked
    try:
        with open(candidate_file, "rb") as check_f:
            chunk = check_f.read(1024)
            if not chunk:
                raise RuntimeError("Video file could not be read.")
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Video file verification failed: {e}")

    # If the candidate is not an mp4, convert/remux with FFmpeg to guarantee clean MP4
    if candidate_file.suffix.lower() != ".mp4":
        final_mp4_temp = temp_dir / "final_converted.mp4"
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        import subprocess
        cmd = [
            ffmpeg_bin, "-y", "-i", str(candidate_file),
            "-c:v", "copy", "-c:a", "aac",
            "-movflags", "+faststart",
            str(final_mp4_temp)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and final_mp4_temp.exists() and final_mp4_temp.stat().st_size > 0:
            candidate_file = final_mp4_temp

    # Safely move candidate file to destination
    if dest_path.exists():
        dest_path.unlink(missing_ok=True)

    shutil.move(str(candidate_file), str(dest_path))

    # Final destination check
    if not dest_path.exists() or dest_path.stat().st_size == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("Final destination file could not be established or is 0 bytes.")

    # Clean temporary scratch directory
    shutil.rmtree(temp_dir, ignore_errors=True)

    logger.info(f"Video download verified successfully: {dest_path.name} ({dest_path.stat().st_size} bytes)")
    return dest_path
