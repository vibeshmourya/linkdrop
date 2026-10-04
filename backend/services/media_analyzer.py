"""
LinkDrop - Media Analyzer Service
"""
import logging
import requests
from typing import Dict, Any, List, Optional
import yt_dlp
from core.config import ANALYSIS_TIMEOUT_SECONDS
from core.security import is_safe_ip
from services.source_detector import detect_source

logger = logging.getLogger("media_analyzer")

def format_duration(seconds: Optional[float]) -> str:
    """Formats duration in seconds to MM:SS or HH:MM:SS."""
    if not seconds or seconds <= 0:
        return ""
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    sec = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"

def format_file_size(size_bytes: Optional[int]) -> str:
    """Formats byte size into readable MB/GB."""
    if not size_bytes or size_bytes <= 0:
        return ""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"

def check_direct_media(url: str) -> Optional[Dict[str, Any]]:
    """
    Checks if URL points directly to a media file using HTTP HEAD or Range GET.
    """
    source_info = detect_source(url)
    known_ext = source_info.get("extension") if source_info.get("is_direct") else None
    direct_cat = source_info.get("direct_type") if source_info.get("is_direct") else None

    content_type = ""
    size_bytes = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }

    try:
        # Try HEAD first
        head_res = requests.head(url, allow_redirects=True, timeout=6, headers=headers)
        if head_res.status_code in (200, 206):
            content_type = head_res.headers.get("Content-Type", "").lower()
            content_length = head_res.headers.get("Content-Length")
            if content_length and content_length.isdigit():
                size_bytes = int(content_length)
        elif head_res.status_code in (403, 405):
            # Try Range GET
            get_res = requests.get(
                url,
                stream=True,
                timeout=6,
                headers={**headers, "Range": "bytes=0-1024"}
            )
            if get_res.status_code in (200, 206):
                content_type = get_res.headers.get("Content-Type", "").lower()
                content_length = get_res.headers.get("Content-Length")
                if content_length and content_length.isdigit():
                    size_bytes = int(content_length)
            get_res.close()
    except Exception as e:
        logger.debug(f"Direct media network check encountered: {e}")

    # Determine media category from content-type or direct extension
    media_type = None
    ext = known_ext or "bin"

    if "video/" in content_type:
        media_type = "video"
        ext = content_type.split("video/")[-1].split(";")[0].strip()
    elif "audio/" in content_type:
        media_type = "audio"
        ext = content_type.split("audio/")[-1].split(";")[0].strip()
    elif "image/" in content_type:
        media_type = "image"
        ext = content_type.split("image/")[-1].split(";")[0].strip()
    elif direct_cat:
        # Fallback to detected extension if extension is recognized
        media_type = direct_cat
        ext = known_ext or "mp4"

    if media_type:
        # Map common subtypes
        if "mp4" in ext: ext = "mp4"
        elif "webm" in ext: ext = "webm"
        elif "mpeg" in ext or "mp3" in ext: ext = "mp3"
        elif "jpeg" in ext or "jpg" in ext: ext = "jpg"
        elif "png" in ext: ext = "png"
        elif "webp" in ext: ext = "webp"

        raw_title = url.split("?")[0].rstrip("/").split("/")[-1]
        title = raw_title if raw_title else f"Direct_{media_type.capitalize()}"

        video_options = []
        audio_options = []
        image_options = []

        if media_type == "video":
            video_options = [
                {"id": "direct", "label": "Direct Video", "format": ext, "height": 720, "size": format_file_size(size_bytes)}
            ]
            audio_options = [
                {"id": "audio_mp3", "label": "Extracted MP3 Audio", "format": "mp3", "size": ""}
            ]
        elif media_type == "audio":
            audio_options = [
                {"id": "direct", "label": "Direct Audio", "format": ext, "size": format_file_size(size_bytes)}
            ]
        elif media_type == "image":
            image_options = [
                {"id": "direct", "label": "Direct Image", "format": ext, "size": format_file_size(size_bytes)}
            ]

        return {
            "source": source_info["platform_name"],
            "badge": source_info["badge"],
            "media_type": media_type,
            "title": title,
            "thumbnail": url if media_type == "image" else None,
            "duration": "",
            "is_gallery": False,
            "items": [],
            "video_options": video_options,
            "audio_options": audio_options,
            "image_options": image_options,
            "direct_download_url": url,
            "filesize": format_file_size(size_bytes)
        }

    return None


def analyze_url(url: str) -> Dict[str, Any]:
    """
    Main extraction and analysis function using yt-dlp and direct fallback.
    Returns normalized metadata and available download options.
    """
    source_info = detect_source(url)

    # 1. Dedicated handling for Instagram
    if source_info.get("platform_id") == "instagram":
        from services.instagram_extractor import analyze_instagram_url
        return analyze_instagram_url(url)

    # 2. If detected as direct link, try direct header inspect first
    if source_info.get("is_direct"):
        direct_result = check_direct_media(url)
        if direct_result:
            return direct_result

    # 2. Extract using yt-dlp
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "socket_timeout": ANALYSIS_TIMEOUT_SECONDS,
        "noplaylist": False,
        "ignoreerrors": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as de:
        error_msg = str(de).lower()
        if "private" in error_msg or "login" in error_msg or "sign in" in error_msg:
            raise ValueError("This media is private or requires authentication and cannot be accessed.")
        if "drm" in error_msg or "protected" in error_msg:
            raise ValueError("This content is protected by digital rights management (DRM) and cannot be downloaded.")
        if "404" in error_msg or "not found" in error_msg:
            raise ValueError("The requested media could not be found. The link may have expired or been deleted.")
        if "unsupported" in error_msg or "no video" in error_msg:
            # Try direct media inspect fallback in case yt-dlp does not recognize the direct stream
            direct_res = check_direct_media(url)
            if direct_res:
                return direct_res
            raise ValueError("We couldn't find downloadable public media at this URL. The source may be unsupported.")
        raise ValueError(f"Could not retrieve media information: The source may be temporarily unavailable or protected.")
    except Exception as e:
        logger.error(f"Analysis error for {url}: {e}")
        # Direct inspect fallback
        direct_res = check_direct_media(url)
        if direct_res:
            return direct_res
        raise ValueError("This URL could not be processed. The page may be unsupported, private, or protected.")

    if not info:
        # Fallback to direct check
        direct_res = check_direct_media(url)
        if direct_res:
            return direct_res
        raise ValueError("No media content could be detected at the provided URL.")

    # 3. Check for Playlist / Carousel / Gallery
    is_playlist = info.get("_type") == "playlist" or "entries" in info
    if is_playlist and info.get("entries"):
        entries = [e for e in info.get("entries") if e]
        if len(entries) > 1:
            items = []
            for idx, entry in enumerate(entries[:20]):  # Cap at 20 items for safety
                item_title = entry.get("title") or f"Item {idx + 1}"
                item_thumb = entry.get("thumbnail") or (entry.get("thumbnails", [{}])[-1].get("url") if entry.get("thumbnails") else None)
                item_url = entry.get("url") or entry.get("webpage_url") or url
                items.append({
                    "index": idx + 1,
                    "title": item_title,
                    "thumbnail": item_thumb,
                    "url": item_url,
                    "duration": format_duration(entry.get("duration")),
                })

            return {
                "source": source_info["platform_name"],
                "badge": source_info["badge"],
                "media_type": "gallery",
                "title": info.get("title") or f"{source_info['platform_name']} Gallery",
                "thumbnail": items[0]["thumbnail"] if items else None,
                "duration": "",
                "is_gallery": True,
                "item_count": len(entries),
                "items": items,
                "formats": [
                    {"id": "zip_all", "label": "Download All (.ZIP)", "format": "zip", "type": "gallery"}
                ]
            }
        elif len(entries) == 1:
            info = entries[0]

    # 4. Single Media Item Processing
    title = info.get("title") or f"{source_info['platform_name']} Media"
    duration = format_duration(info.get("duration"))
    thumbnail = info.get("thumbnail") or (info.get("thumbnails", [{}])[-1].get("url") if info.get("thumbnails") else None)

    # Check available video qualities
    formats_raw = info.get("formats", [])
    video_qualities = set()
    has_audio = False

    # Standard quality tiers we want to display cleanly
    tier_map = {
        2160: "4K (2160p)",
        1440: "2K (1440p)",
        1080: "1080p (Full HD)",
        720: "720p (HD)",
        480: "480p (SD)",
        360: "360p",
        240: "240p",
        144: "144p"
    }

    # Find heights present
    found_heights = set()
    best_size_by_height = {}

    for f in formats_raw:
        if f.get("vcodec") != "none":
            h = f.get("height")
            if h and isinstance(h, (int, float)) and h > 0:
                int_h = int(h)
                found_heights.add(int_h)
                f_size = f.get("filesize") or f.get("filesize_approx")
                if f_size and (int_h not in best_size_by_height or f_size > best_size_by_height[int_h]):
                    best_size_by_height[int_h] = f_size
        if f.get("acodec") != "none":
            has_audio = True

    # Build clean user choices for video
    video_options = []
    # Sort descending
    sorted_heights = sorted(list(found_heights), reverse=True)

    # Pick representative tiers
    for h in sorted_heights:
        # Find closest friendly label
        label = tier_map.get(h, f"{h}p")
        # Don't add duplicate tiers
        if not any(opt["height"] == h for opt in video_options):
            f_size_str = format_file_size(best_size_by_height.get(h))
            video_options.append({
                "id": f"video_{h}",
                "height": h,
                "label": label,
                "format": "mp4",
                "type": "video",
                "size": f_size_str if f_size_str else ""
            })

    # Audio options - ONLY if true audio stream exists
    audio_options = []
    if has_audio and (len(video_options) > 0 or has_audio):
        audio_options = [
            {"id": "audio_mp3", "label": "MP3 Audio (High Quality)", "format": "mp3", "type": "audio", "quality": "320k"},
            {"id": "audio_m4a", "label": "M4A Audio (AAC)", "format": "m4a", "type": "audio", "quality": "auto"},
            {"id": "audio_wav", "label": "WAV Audio (Lossless)", "format": "wav", "type": "audio", "quality": "lossless"}
        ]

    # Image option if thumbnail exists and not a video
    image_options = []
    if thumbnail and not video_options:
        image_options = [
            {"id": "image_jpg", "label": "Image (JPG)", "format": "jpg", "type": "image"},
            {"id": "image_png", "label": "Image (PNG)", "format": "png", "type": "image"},
            {"id": "image_webp", "label": "Image (WEBP)", "format": "webp", "type": "image"}
        ]

    # Determine primary media type accurately
    if video_options:
        primary_type = "video"
    elif has_audio and not video_options:
        primary_type = "audio"
    elif image_options:
        primary_type = "image"
    else:
        primary_type = "unknown"

    return {
        "source": source_info["platform_name"],
        "badge": source_info["badge"],
        "media_type": primary_type,
        "title": title,
        "thumbnail": thumbnail,
        "duration": duration,
        "is_gallery": False,
        "items": [],
        "video_options": video_options,
        "audio_options": audio_options,
        "image_options": image_options,
    }
