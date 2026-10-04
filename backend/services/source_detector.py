"""
LinkDrop - Source Detector
"""
from urllib.parse import urlparse
from typing import Dict, Any

SUPPORTED_PLATFORMS = {
    "youtube": {
        "name": "YouTube",
        "badge": "YouTube",
        "domains": ["youtube.com", "youtu.be", "music.youtube.com", "m.youtube.com"],
        "media_types": ["Video", "Shorts", "Audio"]
    },
    "instagram": {
        "name": "Instagram",
        "badge": "Instagram",
        "domains": ["instagram.com", "instagr.am"],
        "media_types": ["Reel", "Post", "Video", "Image", "Carousel"]
    },
    "facebook": {
        "name": "Facebook",
        "badge": "Facebook",
        "domains": ["facebook.com", "fb.watch", "fb.com", "m.facebook.com"],
        "media_types": ["Video", "Reel", "Post"]
    },
    "tiktok": {
        "name": "TikTok",
        "badge": "TikTok",
        "domains": ["tiktok.com", "vm.tiktok.com"],
        "media_types": ["Video"]
    },
    "twitter": {
        "name": "X (Twitter)",
        "badge": "X",
        "domains": ["twitter.com", "x.com", "mobile.twitter.com"],
        "media_types": ["Video", "Image", "Post"]
    },
    "whatsapp": {
        "name": "WhatsApp",
        "badge": "WhatsApp",
        "domains": ["whatsapp.com"],
        "media_types": ["Public Link"]
    }
}

DIRECT_EXTENSIONS = {
    "video": [".mp4", ".webm", ".mkv", ".mov", ".flv", ".avi", ".m4v"],
    "audio": [".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus", ".flac"],
    "image": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"]
}

def detect_source(url: str) -> Dict[str, Any]:
    """
    Analyzes the URL structure to classify the source platform and category.
    """
    try:
        parsed = urlparse(url.lower())
        host = parsed.hostname or ""
        path = parsed.path or ""

        # Remove 'www.'
        if host.startswith("www."):
            host = host[4:]

        # Check known platforms
        for key, info in SUPPORTED_PLATFORMS.items():
            for domain in info["domains"]:
                if host == domain or host.endswith(f".{domain}"):
                    return {
                        "platform_id": key,
                        "platform_name": info["name"],
                        "badge": info["badge"],
                        "is_direct": False,
                        "probable_types": info["media_types"]
                    }

        # Check for direct file extensions
        for media_cat, exts in DIRECT_EXTENSIONS.items():
            for ext in exts:
                if path.endswith(ext):
                    return {
                        "platform_id": "direct",
                        "platform_name": "Direct Media Link",
                        "badge": media_cat.capitalize(),
                        "is_direct": True,
                        "direct_type": media_cat,
                        "extension": ext.lstrip("."),
                        "probable_types": [media_cat.capitalize()]
                    }

        # Generic web source
        return {
            "platform_id": "generic",
            "platform_name": host.capitalize() if host else "Web Media",
            "badge": "Web Source",
            "is_direct": False,
            "probable_types": ["Video", "Audio", "Media"]
        }
    except Exception:
        return {
            "platform_id": "unknown",
            "platform_name": "Web Media",
            "badge": "Media",
            "is_direct": False,
            "probable_types": ["Media"]
        }
