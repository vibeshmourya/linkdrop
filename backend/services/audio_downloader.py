"""
LinkDrop - Audio Downloader Service
"""
import shutil
import logging
from pathlib import Path
from typing import Callable, Optional
import yt_dlp
from core.config import DOWNLOADS_DIR, MAX_DOWNLOAD_SIZE_BYTES
from utils.filenames import get_safe_destination_path, get_temp_workspace

logger = logging.getLogger("audio_downloader")

INCOMPLETE_EXTENSIONS = {".part", ".ytdl", ".tmp", ".crdownload"}

def download_audio(
    url: str,
    title: str,
    audio_format: str = "mp3",
    audio_quality: str = "320",
    progress_callback: Optional[Callable[[dict], None]] = None
) -> Path:
    """
    Extracts audio from URL and converts using FFmpeg to verified audio format.
    """
    clean_format = audio_format.lower()
    if clean_format not in ["mp3", "m4a", "wav", "aac"]:
        clean_format = "mp3"

    dest_path, filename = get_safe_destination_path(title, clean_format, target_dir=DOWNLOADS_DIR)
    temp_dir = get_temp_workspace(dest_path.stem)
    out_tmpl = str(temp_dir / f"audio_stream.%(ext)s")

    def ydl_progress_hook(d):
        if not progress_callback:
            return
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            percent = (downloaded / total * 100) if total > 0 else 0
            progress_callback({
                "status": "downloading",
                "percent": min(round(percent, 1), 95.0),
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "speed": round(speed / (1024 * 1024), 2) if speed else 0,
                "eta": d.get("eta") or 0
            })
        elif status == "finished":
            progress_callback({
                "status": "processing",
                "percent": 96.0,
                "message": "Extracting and encoding audio with FFmpeg..."
            })

    postprocessors = [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": clean_format,
        "preferredquality": "320" if audio_quality == "320k" else "192",
    }]

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_tmpl,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [ydl_progress_hook],
        "max_filesize": MAX_DOWNLOAD_SIZE_BYTES,
        "postprocessors": postprocessors
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(f"yt-dlp audio download error: {e}", exc_info=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Audio extraction failed: {str(e)}")

    # Look for matching format output
    expected_file = temp_dir / f"audio_stream.{clean_format}"
    candidate_file: Optional[Path] = None

    if expected_file.exists() and expected_file.stat().st_size > 0:
        candidate_file = expected_file
    else:
        valid_files = [
            f for f in temp_dir.glob(f"*.{clean_format}")
            if f.is_file()
            and f.suffix.lower() not in INCOMPLETE_EXTENSIONS
            and f.stat().st_size > 0
        ]
        if not valid_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("No complete audio file was produced.")
        valid_files.sort(key=lambda p: p.stat().st_size, reverse=True)
        candidate_file = valid_files[0]

    # Verify candidate file size and readability
    if candidate_file.stat().st_size == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("Generated audio file is 0 bytes.")

    try:
        with open(candidate_file, "rb") as check_f:
            chunk = check_f.read(1024)
            if not chunk:
                raise RuntimeError("Audio file could not be read.")
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Audio file verification error: {e}")

    # Move to destination
    if dest_path.exists():
        dest_path.unlink(missing_ok=True)

    shutil.move(str(candidate_file), str(dest_path))

    if not dest_path.exists() or dest_path.stat().st_size == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("Final audio destination file is invalid or 0 bytes.")

    shutil.rmtree(temp_dir, ignore_errors=True)
    logger.info(f"Audio download verified: {dest_path.name} ({dest_path.stat().st_size} bytes)")
    return dest_path
