"""
LinkDrop - Temporary File Cleanup
"""
import os
import shutil
import time
import logging
from pathlib import Path
from core.config import TEMP_DIR, DOWNLOADS_DIR, FILE_RETENTION_SECONDS

logger = logging.getLogger("cleanup")

def cleanup_expired_files(max_age_seconds: int = FILE_RETENTION_SECONDS):
    """
    Scans temporary and downloads folders and deletes files older than max_age_seconds.
    """
    now = time.time()

    for folder in [TEMP_DIR, DOWNLOADS_DIR]:
        if not folder.exists():
            continue

        try:
            for item in folder.iterdir():
                try:
                    # Check age
                    mtime = item.stat().st_mtime
                    if now - mtime > max_age_seconds:
                        if item.is_file():
                            item.unlink(missing_ok=True)
                            logger.info(f"Cleaned up expired file: {item.name}")
                        elif item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                            logger.info(f"Cleaned up expired folder: {item.name}")
                except Exception as e:
                    logger.debug(f"Error inspecting {item}: {e}")
        except Exception as e:
            logger.error(f"Error scanning directory {folder}: {e}")

def delete_job_files(file_path: Path):
    """
    Deletes a specific downloaded file after it has been delivered.
    """
    try:
        if file_path and file_path.exists():
            if file_path.is_file():
                file_path.unlink(missing_ok=True)
            elif file_path.is_dir():
                shutil.rmtree(file_path, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Could not delete completed job file {file_path}: {e}")
