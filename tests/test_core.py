"""
LinkDrop - Automated Test Suite
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from core.security import is_safe_ip, validate_url_security, sanitize_filename
from core.validators import validate_media_url
from services.source_detector import detect_source
from services.media_analyzer import analyze_url
from utils.filenames import get_safe_destination_path

def test_security_and_ssrf():
    print("--> Testing Security & SSRF Protection...")
    # Blocked IP checks
    assert not is_safe_ip("127.0.0.1"), "Should block loopback"
    assert not is_safe_ip("10.0.0.1"), "Should block private 10.x"
    assert not is_safe_ip("192.168.1.1"), "Should block private 192.168.x"
    assert not is_safe_ip("172.16.0.1"), "Should block private 172.16.x"
    assert not is_safe_ip("169.254.169.254"), "Should block AWS/GCP metadata"
    assert not is_safe_ip("0.0.0.0"), "Should block 0.0.0.0"
    assert is_safe_ip("8.8.8.8"), "Should allow public IP 8.8.8.8"
    assert is_safe_ip("1.1.1.1"), "Should allow public IP 1.1.1.1"

    # URL validation security
    safe, msg, _ = validate_url_security("http://localhost:8000")
    assert not safe, "Should block localhost"

    safe, msg, _ = validate_url_security("http://127.0.0.1:5000/secret")
    assert not safe, "Should block 127.0.0.1"

    safe, msg, _ = validate_url_security("ftp://example.com/file.mp4")
    assert not safe, "Should block non-http/https"

    safe, msg, _ = validate_url_security("file:///etc/passwd")
    assert not safe, "Should block file protocol"

    safe, msg, norm = validate_url_security("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert safe, f"Should accept public valid URL: {msg}"
    print("[OK] Security & SSRF tests passed!")

def test_filename_sanitization():
    print("--> Testing Filename Sanitization & Path Traversal Prevention...")
    name1 = sanitize_filename("../../../etc/passwd")
    assert ".." not in name1 and "/" not in name1, f"Failed traversal sanitization: {name1}"

    name2 = sanitize_filename("..\\..\\Windows\\System32\\cmd.exe")
    assert ".." not in name2 and "\\" not in name2, f"Failed Windows traversal sanitization: {name2}"

    name3 = sanitize_filename('My Video: Best Scenes / Cuts * "Special" ? 2024')
    assert all(c not in name3 for c in '<>:"/\\|?*'), f"Failed special char removal: {name3}"

    dest, fname = get_safe_destination_path("Test Title", "mp4")
    assert dest.is_absolute()
    assert fname.endswith(".mp4")
    print("[OK] Filename sanitization tests passed!")

def test_source_detection():
    print("--> Testing Source Detector...")
    yt = detect_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert yt["platform_id"] == "youtube"

    yt_short = detect_source("https://youtu.be/dQw4w9WgXcQ")
    assert yt_short["platform_id"] == "youtube"

    ig = detect_source("https://www.instagram.com/reel/C3abc123/")
    assert ig["platform_id"] == "instagram"

    fb = detect_source("https://www.facebook.com/watch/?v=123456789")
    assert fb["platform_id"] == "facebook"

    tt = detect_source("https://www.tiktok.com/@user/video/1234567890123")
    assert tt["platform_id"] == "tiktok"

    tw = detect_source("https://x.com/user/status/123456789")
    assert tw["platform_id"] == "twitter"

    direct_vid = detect_source("https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4")
    assert direct_vid["is_direct"] is True
    assert direct_vid["direct_type"] == "video"

    direct_img = detect_source("https://example.com/photos/landscape.jpg")
    assert direct_img["is_direct"] is True
    assert direct_img["direct_type"] == "image"
    print("[OK] Source detection tests passed!")

def test_direct_media_analysis():
    print("--> Testing Media Analysis on Direct Public Video...")
    # Public sample video link
    sample_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    data = analyze_url(sample_url)
    assert data is not None
    assert "source" in data
    assert "title" in data
    assert data["media_type"] == "video"
    print(f"[OK] Direct media analysis passed! Detected title: {data['title']}")

def test_youtube_analysis():
    print("--> Testing Media Analysis on Public YouTube Video...")
    # Short public test video
    sample_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    data = analyze_url(sample_url)
    assert data is not None
    assert data["source"] == "YouTube"
    assert "Never Gonna Give You Up" in data["title"]
    assert len(data.get("video_options", [])) > 0
    assert len(data.get("audio_options", [])) > 0
    print(f"[OK] YouTube analysis passed! Found {len(data['video_options'])} video options and {len(data['audio_options'])} audio options.")

if __name__ == "__main__":
    test_security_and_ssrf()
    test_filename_sanitization()
    test_source_detection()
    test_direct_media_analysis()
    test_youtube_analysis()
    print("\n>>> ALL UNIT AND INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")

