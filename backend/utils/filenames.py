"""
LinkDrop - Filename & Path Utilities
"""
import uuid
from pathlib import Path
from typing import Tuple
from core.security import sanitize_filename
from core.config import DOWNLOADS_DIR, TEMP_DIR

def get_safe_destination_path(
    title: str,
    extension: str,
    target_dir: Path = DOWNLOADS_DIR,
    prefix: str = ""
) -> Tuple[Path, str]:
    """
    Generates a safe, non-traversing absolute path within target_dir.
    Returns: (absolute_path, safe_filename)
    """
    clean_title = sanitize_filename(title)
    clean_ext = extension.lstrip(".").lower()
    if not clean_ext:
        clean_ext = "mp4"

    # Add prefix if given
    base_name = f"{prefix}_{clean_title}" if prefix else clean_title

    # Safe unique filename
    unique_suffix = uuid.uuid4().hex[:6]
    filename = f"{base_name}_{unique_suffix}.{clean_ext}"

    dest_path = (target_dir / filename).resolve()

    # Absolute directory containment check
    resolved_dir = target_dir.resolve()
    try:
        dest_path.relative_to(resolved_dir)
    except ValueError:
        # Fallback to pure safe unique name if path escaping was attempted
        filename = f"media_{uuid.uuid4().hex[:8]}.{clean_ext}"
        dest_path = (target_dir / filename).resolve()

    return dest_path, filename

def get_temp_workspace(job_id: str) -> Path:
    """
    Returns an isolated temporary directory for a specific download job.
    """
    safe_job_id = sanitize_filename(job_id)
    job_dir = (TEMP_DIR / safe_job_id).resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir
