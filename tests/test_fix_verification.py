"""
Universal Media Downloader - Download Delivery Fix Verification Test
"""
import time
import requests
import subprocess
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def test_video_download_pipeline():
    print("\n--> 1. Testing Video Download Pipeline (YouTube clip)...")
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    res = requests.post(f"{BASE_URL}/api/download", json={
        "url": video_url,
        "title": "Delivery Fix Video",
        "media_type": "video",
        "quality_or_format": "video_360"
    })
    assert res.status_code == 200, f"Download start failed: {res.text}"
    job_id = res.json()["job_id"]
    print(f"    Job queued: {job_id}")

    # Poll until complete
    for _ in range(35):
        p = requests.get(f"{BASE_URL}/api/progress/{job_id}").json()
        status = p.get("status")
        pct = p.get("percent", 0)
        speed = p.get("speed", 0)
        if status in ("completed", "failed"):
            break
        time.sleep(1)

    assert status == "completed", f"Download failed: {p.get('error')}"
    print(f"    Status: {status} ({pct}%) - File: {p.get('filename')}")

    # 1. Test HEAD request (Crucial for Chrome!)
    head_res = requests.head(f"{BASE_URL}/api/file/{job_id}")
    print(f"    HEAD Status: {head_res.status_code}")
    print(f"    Content-Type: {head_res.headers.get('content-type')}")
    print(f"    Content-Length: {head_res.headers.get('content-length')}")
    print(f"    Content-Disposition: {head_res.headers.get('content-disposition')}")

    assert head_res.status_code == 200, f"HEAD request failed with {head_res.status_code}"
    assert head_res.headers.get("content-type") == "video/mp4", "Content-Type must be video/mp4"
    assert int(head_res.headers.get("content-length", 0)) > 100000, "Content-Length too small"
    assert "attachment" in head_res.headers.get("content-disposition", ""), "Missing attachment header"

    # 2. Test First GET request
    get_res1 = requests.get(f"{BASE_URL}/api/file/{job_id}", stream=True)
    assert get_res1.status_code == 200, "First GET failed"
    data1 = get_res1.content
    print(f"    First GET: {len(data1)} bytes received successfully")
    assert len(data1) == int(head_res.headers.get("content-length")), "Received bytes must match Content-Length"

    # 3. Test Second GET request (Verifying file was NOT prematurely deleted)
    get_res2 = requests.get(f"{BASE_URL}/api/file/{job_id}", stream=True)
    assert get_res2.status_code == 200, f"Second GET failed with status {get_res2.status_code} (premature deletion bug!)"
    data2 = get_res2.content
    print(f"    Second GET (Browser re-request/Save check): {len(data2)} bytes received successfully")
    assert len(data2) == len(data1), "Second GET size must match first GET"

    # 4. Save to temporary test file and verify with ffprobe
    test_out = Path("temp_test_video.mp4")
    test_out.write_bytes(data1)

    # Verify with ffprobe
    ffprobe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "default=noprint_wrappers=1", str(test_out)]
    try:
        probe_res = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"    FFprobe verification:\n{probe_res.stdout.strip()}")
        assert probe_res.returncode == 0, f"FFprobe could not parse video: {probe_res.stderr}"
    finally:
        test_out.unlink(missing_ok=True)

    print("    [OK] Video download delivery verified 100%!")

def test_audio_download_pipeline():
    print("\n--> 2. Testing Audio Download Pipeline (MP3)...")
    res = requests.post(f"{BASE_URL}/api/download", json={
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "title": "Delivery Fix Audio",
        "media_type": "audio",
        "quality_or_format": "audio_mp3"
    })
    job_id = res.json()["job_id"]

    for _ in range(35):
        p = requests.get(f"{BASE_URL}/api/progress/{job_id}").json()
        if p.get("status") in ("completed", "failed"):
            break
        time.sleep(1)

    assert p.get("status") == "completed", f"Audio job failed: {p.get('error')}"

    # HEAD and GET checks
    head_res = requests.head(f"{BASE_URL}/api/file/{job_id}")
    assert head_res.status_code == 200
    assert head_res.headers.get("content-type") == "audio/mpeg", f"Expected audio/mpeg, got {head_res.headers.get('content-type')}"

    get_res = requests.get(f"{BASE_URL}/api/file/{job_id}")
    assert get_res.status_code == 200
    assert len(get_res.content) > 50000, "Audio file too small"
    print(f"    Audio GET: {len(get_res.content)} bytes, Content-Type: {get_res.headers.get('content-type')}")
    print("    [OK] Audio download delivery verified 100%!")

def test_image_download_pipeline():
    print("\n--> 3. Testing Image Download Pipeline (JPG)...")
    img_url = "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=300"
    res = requests.post(f"{BASE_URL}/api/download", json={
        "url": img_url,
        "title": "Delivery Fix Image",
        "media_type": "image",
        "quality_or_format": "image_jpg",
        "extra_data": {"thumbnail": img_url}
    })
    job_id = res.json()["job_id"]

    for _ in range(25):
        p = requests.get(f"{BASE_URL}/api/progress/{job_id}").json()
        if p.get("status") in ("completed", "failed"):
            break
        time.sleep(0.5)

    assert p.get("status") == "completed", f"Image job failed: {p.get('error')}"

    head_res = requests.head(f"{BASE_URL}/api/file/{job_id}")
    assert head_res.status_code == 200
    assert head_res.headers.get("content-type") == "image/jpeg"

    get_res = requests.get(f"{BASE_URL}/api/file/{job_id}")
    assert get_res.status_code == 200
    assert len(get_res.content) > 5000
    print(f"    Image GET: {len(get_res.content)} bytes, Content-Type: {get_res.headers.get('content-type')}")
    print("    [OK] Image download delivery verified 100%!")

if __name__ == "__main__":
    test_video_download_pipeline()
    test_audio_download_pipeline()
    test_image_download_pipeline()
    print("\n=======================================================")
    print(">>> ALL DOWNLOAD PIPELINE & DELIVERY TESTS PASSED! <<<")
    print("=======================================================")
