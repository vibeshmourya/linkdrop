"""
LinkDrop - Instagram Media Fix Verification Test
"""
import time
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def test_instagram_exact_url():
    print("\n--> 1. Testing Exact User Instagram URL...")
    test_url = "https://www.instagram.com/p/DbhmxLlFxVE/?stkn=MXF2dHZvMG4wN25hag=="

    # Analyze
    res = requests.post(f"{BASE_URL}/api/analyze", json={"url": test_url}, timeout=25)
    assert res.status_code == 200, f"Analyze failed: {res.text}"

    data = res.json()["data"]
    print("    Source:", data.get("source"))
    print("    Media Type:", data.get("media_type"))
    print("    Title:", data.get("title"))
    print("    Thumbnail URL:", data.get("thumbnail")[:80] if data.get("thumbnail") else "None")
    print("    Video Options:", data.get("video_options"))
    print("    Audio Options:", data.get("audio_options"))
    print("    Image Options:", [opt["id"] for opt in data.get("image_options", [])])

    # Assertions
    assert data.get("media_type") in ("image", "gallery"), f"Media type must be image or gallery, got: {data.get('media_type')}"
    assert data.get("audio_options") == [], "Audio options MUST be empty for an Instagram image post!"
    assert data.get("video_options") == [], "Video options MUST be empty for an Instagram image post!"
    assert data.get("thumbnail") is not None, "Thumbnail must be extracted"
    assert "ram.ji_ke_darshan" in data.get("title", ""), "Title should reflect author"
    print("    [OK] Instagram image post media-type detection verified!")

    # Test Download
    print("\n--> 2. Testing Download of Extracted Instagram Image...")
    dl_payload = {
        "url": data.get("direct_download_url") or data.get("thumbnail") or test_url,
        "title": data.get("title") or "Instagram Post",
        "media_type": "image",
        "quality_or_format": "image_jpg",
        "extra_data": {
            "thumbnail": data.get("thumbnail"),
            "items": data.get("items", [])
        }
    }

    dl_res = requests.post(f"{BASE_URL}/api/download", json=dl_payload, timeout=15)
    assert dl_res.status_code == 200, f"Download init failed: {dl_res.text}"
    job_id = dl_res.json()["job_id"]
    print(f"    Download job queued: {job_id}")

    # Poll
    for _ in range(25):
        p = requests.get(f"{BASE_URL}/api/progress/{job_id}").json()
        if p.get("status") in ("completed", "failed"):
            break
        time.sleep(0.5)

    assert p.get("status") == "completed", f"Download job failed: {p.get('error')}"
    print(f"    Job completed: {p.get('filename')}")

    # Fetch file
    file_res = requests.get(f"{BASE_URL}/api/file/{job_id}", stream=True)
    assert file_res.status_code == 200, f"File fetch failed: {file_res.status_code}"
    assert file_res.headers.get("content-type") == "image/jpeg", f"Wrong Content-Type: {file_res.headers.get('content-type')}"
    file_bytes = file_res.content
    print(f"    Received image file size: {len(file_bytes)} bytes")
    assert len(file_bytes) > 50000, "Image file too small"
    print("    [OK] Instagram image download succeeded and verified 100%!")

def test_youtube_video_regression():
    print("\n--> 3. Testing Regression on Video (YouTube)...")
    yt_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    res = requests.post(f"{BASE_URL}/api/analyze", json={"url": yt_url}, timeout=20)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data.get("media_type") == "video"
    assert len(data.get("video_options", [])) > 0
    assert len(data.get("audio_options", [])) > 0
    print("    [OK] Video analysis regression check passed!")

if __name__ == "__main__":
    test_instagram_exact_url()
    test_youtube_video_regression()
    print("\n=======================================================")
    print(">>> ALL INSTAGRAM FIX & REGRESSION TESTS PASSED! <<<")
    print("=======================================================")
