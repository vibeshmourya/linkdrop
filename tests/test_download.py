"""
LinkDrop - Download Pipeline Test
"""
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.downloader import create_download_job, get_job_status
from core.config import DOWNLOADS_DIR, TEMP_DIR

def test_image_download():
    print("--> Testing Image Download Job...")
    # Public test image
    test_img = "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=300"
    job_id = create_download_job(
        url=test_img,
        title="Sample Artwork",
        media_type="image",
        quality_or_format="image_jpg",
        extra_data={"thumbnail": test_img}
    )

    # Wait for completion
    for _ in range(25):
        status = get_job_status(job_id)
        if status and status.get("status") in ("completed", "failed"):
            break
        time.sleep(0.5)

    status = get_job_status(job_id)
    assert status["status"] == "completed", f"Job failed: {status.get('error')}"
    file_path = Path(status["file_path"])
    assert file_path.exists(), "Downloaded file does not exist on disk"
    assert file_path.stat().st_size > 0, "Downloaded file is empty"
    print(f"[OK] Image download passed! File: {file_path.name} ({file_path.stat().st_size} bytes)")

    # Clean test file
    file_path.unlink(missing_ok=True)

def test_audio_extraction():
    print("--> Testing Audio Extraction Job...")
    # Short public audio / video clip to extract MP3
    # Use a small public clip
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Me at the zoo (19s)
    job_id = create_download_job(
        url=test_url,
        title="Me at the zoo audio",
        media_type="audio",
        quality_or_format="audio_mp3"
    )

    for _ in range(50):
        status = get_job_status(job_id)
        if status and status.get("status") in ("completed", "failed"):
            break
        time.sleep(1.0)

    status = get_job_status(job_id)
    assert status["status"] == "completed", f"Audio extraction failed: {status.get('error')}"
    file_path = Path(status["file_path"])
    assert file_path.exists(), "Audio file does not exist"
    assert file_path.suffix == ".mp3", "Extension should be .mp3"
    assert file_path.stat().st_size > 0, "Audio file is empty"
    print(f"[OK] Audio extraction passed! File: {file_path.name} ({file_path.stat().st_size} bytes)")

    # Clean test file
    file_path.unlink(missing_ok=True)

if __name__ == "__main__":
    test_image_download()
    test_audio_extraction()
    print("\n>>> ALL DOWNLOAD AND EXTRACTION PIPELINE TESTS PASSED! <<<")
