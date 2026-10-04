"""
LinkDrop - Image Downloader Service
"""
import logging
from pathlib import Path
from typing import Callable, Optional
import requests
from PIL import Image
from core.config import DOWNLOADS_DIR, MAX_DOWNLOAD_SIZE_BYTES
from utils.filenames import get_safe_destination_path

logger = logging.getLogger("image_downloader")

def download_image(
    image_url: str,
    title: str,
    target_format: str = "jpg",
    progress_callback: Optional[Callable[[dict], None]] = None
) -> Path:
    """
    Downloads an image file and converts to requested format (jpg, png, webp).
    """
    clean_format = target_format.lower()
    if clean_format not in ["jpg", "jpeg", "png", "webp"]:
        clean_format = "jpg"

    dest_path, filename = get_safe_destination_path(title, clean_format, target_dir=DOWNLOADS_DIR)

    if progress_callback:
        progress_callback({"status": "downloading", "percent": 20.0, "message": "Downloading image..."})

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    res = requests.get(image_url, headers=headers, stream=True, timeout=20)
    res.raise_for_status()

    temp_raw_path = dest_path.with_suffix(".raw")
    total_downloaded = 0

    with open(temp_raw_path, "wb") as f:
        for chunk in res.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                total_downloaded += len(chunk)
                if total_downloaded > MAX_DOWNLOAD_SIZE_BYTES:
                    temp_raw_path.unlink(missing_ok=True)
                    raise ValueError("Image file exceeds maximum allowable size.")

    if progress_callback:
        progress_callback({"status": "processing", "percent": 85.0, "message": "Converting format..."})

    try:
        with Image.open(temp_raw_path) as img:
            # Convert RGBA to RGB for JPEG if needed
            if clean_format in ["jpg", "jpeg"] and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(dest_path)
    except Exception as e:
        logger.warning(f"Pillow conversion failed, saving raw file: {e}")
        temp_raw_path.replace(dest_path)
    finally:
        temp_raw_path.unlink(missing_ok=True)

    if progress_callback:
        progress_callback({
            "status": "completed",
            "percent": 100.0,
            "downloaded_bytes": dest_path.stat().st_size,
            "total_bytes": dest_path.stat().st_size
        })

    return dest_path
