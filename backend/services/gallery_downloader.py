"""
LinkDrop - Gallery & Carousel Downloader Service
"""
import logging
import zipfile
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any
import requests
from core.config import DOWNLOADS_DIR, MAX_DOWNLOAD_SIZE_BYTES
from utils.filenames import get_safe_destination_path, get_temp_workspace
from core.security import sanitize_filename

logger = logging.getLogger("gallery_downloader")

def download_gallery(
    items: List[Dict[str, Any]],
    gallery_title: str,
    progress_callback: Optional[Callable[[dict], None]] = None
) -> Path:
    """
    Downloads gallery/carousel items and packages them into a safe ZIP archive.
    """
    dest_path, filename = get_safe_destination_path(gallery_title, "zip", target_dir=DOWNLOADS_DIR)
    temp_dir = get_temp_workspace(dest_path.stem)

    total_items = len(items)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    downloaded_files = []
    total_bytes = 0

    for idx, item in enumerate(items):
        item_url = item.get("thumbnail") or item.get("url")
        if not item_url:
            continue

        item_num = idx + 1
        ext = "mp4" if item.get("type") == "video" else "jpg"
        safe_item_name = f"item_{item_num:02d}.{ext}"
        target_file = temp_dir / safe_item_name

        try:
            res = requests.get(item_url, headers=headers, stream=True, timeout=15)
            if res.status_code == 200:
                with open(target_file, "wb") as f:
                    for chunk in res.iter_content(chunk_size=32768):
                        if chunk:
                            f.write(chunk)
                            total_bytes += len(chunk)
                            if total_bytes > MAX_DOWNLOAD_SIZE_BYTES:
                                raise ValueError("Gallery size exceeds maximum limit.")
                downloaded_files.append(target_file)
        except Exception as e:
            logger.warning(f"Failed to download gallery item {item_num}: {e}")

        if progress_callback and total_items > 0:
            percent = (item_num / total_items) * 85.0
            progress_callback({
                "status": "downloading",
                "percent": round(percent, 1),
                "message": f"Downloading item {item_num} of {total_items}..."
            })

    if not downloaded_files:
        raise RuntimeError("Could not retrieve any items from the gallery.")

    if progress_callback:
        progress_callback({
            "status": "processing",
            "percent": 95.0,
            "message": "Archiving files into ZIP..."
        })

    # Create ZIP archive
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zip_out:
        for f in downloaded_files:
            zip_out.write(f, arcname=f.name)

    # Clean temp files
    for f in downloaded_files:
        f.unlink(missing_ok=True)
    try:
        temp_dir.rmdir()
    except Exception:
        pass

    if progress_callback:
        progress_callback({
            "status": "completed",
            "percent": 100.0,
            "total_bytes": dest_path.stat().st_size
        })

    return dest_path
