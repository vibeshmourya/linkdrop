"""
Universal Media Downloader - Upgraded Dedicated Instagram Extractor
Supports: Posts (Images, Videos, Carousels), Reels, Stories, Public Profile Media.
Strictly link-only. No login, no passwords, no cookies, no auth tokens.
"""
import re
import html
import logging
from typing import Dict, Any, List, Optional
import requests
import yt_dlp

logger = logging.getLogger("instagram_extractor")

CRAWLER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def classify_instagram_url(url: str) -> Dict[str, Any]:
    """
    Classifies Instagram URL into:
    - 'story': (username, story_id)
    - 'reel': shortcode
    - 'post': shortcode
    - 'profile': username
    - 'unknown': raw URL
    """
    clean = url.split("?")[0].rstrip("/")

    # 1. Stories: /stories/{username}/{story_id}/
    m_story = re.search(r'instagram\.com\/stories\/([a-zA-Z0-9_\.]+)\/([0-9]+)', clean)
    if m_story:
        return {"kind": "story", "username": m_story.group(1), "story_id": m_story.group(2)}

    # 2. Reels: /reel/{code}/ or /reels/{code}/
    m_reel = re.search(r'instagram\.com\/(?:reel|reels)\/([a-zA-Z0-9_\-]+)', clean)
    if m_reel:
        return {"kind": "reel", "shortcode": m_reel.group(1)}

    # 3. Posts: /p/{code}/
    m_post = re.search(r'instagram\.com\/p\/([a-zA-Z0-9_\-]+)', clean)
    if m_post:
        return {"kind": "post", "shortcode": m_post.group(1)}

    # 4. Profile: /{username}/
    m_profile = re.search(r'instagram\.com\/([a-zA-Z0-9_\.]+)\/?$', clean)
    if m_profile:
        u = m_profile.group(1)
        reserved = {"explore", "reels", "stories", "accounts", "developer", "about", "legal", "direct"}
        if u not in reserved:
            return {"kind": "profile", "username": u}

    return {"kind": "unknown"}

def extract_public_profile_media(username: str) -> Dict[str, Any]:
    """
    Extracts public profile picture (DP) from public profile page without authentication.
    """
    url = f"https://www.instagram.com/{username}/"
    try:
        res = requests.get(url, headers=CRAWLER_HEADERS, timeout=10)
        if res.status_code != 200:
            raise ValueError(f"Could not connect to Instagram profile for @{username}.")

        text = res.text

        # 1. Check og:image meta tag
        og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', text)
        if not og_img:
            og_img = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', text)

        profile_img_url = html.unescape(og_img.group(1)) if og_img else None

        # 2. Fallback search for CDN profile_pic url
        if not profile_img_url:
            m = re.search(r'https:\/\/[^"\'\s\\<>]+(?:fbcdn\.net|cdninstagram\.com)[^"\'\s\\<>]*profile_pic[^\s"\'\\<>]*', text)
            if m:
                profile_img_url = html.unescape(m.group(0).replace('\\/', '/'))

        if not profile_img_url:
            raise ValueError(
                f"No public profile picture could be detected for @{username}. "
                "The account may be private or restricted."
            )

        # Verify image accessibility
        check = requests.get(profile_img_url, headers=BROWSER_HEADERS, timeout=6, stream=True)
        if check.status_code != 200:
            check.close()
            raise ValueError(f"Profile picture for @{username} is not accessible without login.")
        check.close()

        return {
            "source": "Instagram",
            "badge": "Instagram",
            "media_type": "image",
            "title": f"Profile Picture - @{username}",
            "thumbnail": profile_img_url,
            "duration": "",
            "is_gallery": False,
            "items": [
                {"index": 1, "type": "image", "url": profile_img_url, "thumbnail": profile_img_url, "format": "jpg"}
            ],
            "video_options": [],
            "audio_options": [],
            "image_options": [
                {"id": "image_jpg", "label": "Image (JPG)", "format": "jpg", "type": "image"},
                {"id": "image_png", "label": "Image (PNG)", "format": "png", "type": "image"},
                {"id": "image_webp", "label": "Image (WEBP)", "format": "webp", "type": "image"}
            ],
            "direct_download_url": profile_img_url
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error extracting profile media: {e}")
        raise ValueError(f"Unable to access profile for @{username}. The account may be private or restricted.")

def extract_public_story_media(url: str, username: str, story_id: str) -> Dict[str, Any]:
    """
    Attempts unauthenticated public extraction for an Instagram Story.
    Strictly follows requirement: If authentication is required, clearly informs the user.
    """
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 12,
    }

    # 1. Attempt unauthenticated yt-dlp first
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                formats = info.get("formats", [])
                has_video = any(f.get("vcodec") != "none" for f in formats)
                title = f"Story by @{username}"

                if has_video:
                    video_qualities = []
                    seen_h = set()
                    for f in formats:
                        h = f.get("height")
                        if h and h not in seen_h and f.get("vcodec") != "none":
                            seen_h.add(h)
                            video_qualities.append({
                                "id": f"video_{h}",
                                "height": h,
                                "label": f"{h}p (MP4)",
                                "format": "mp4",
                                "type": "video",
                                "size": ""
                            })
                    video_qualities.sort(key=lambda x: x["height"], reverse=True)

                    return {
                        "source": "Instagram",
                        "badge": "Instagram",
                        "media_type": "video",
                        "title": title,
                        "thumbnail": info.get("thumbnail"),
                        "duration": info.get("duration", ""),
                        "is_gallery": False,
                        "items": [],
                        "video_options": video_qualities if video_qualities else [
                            {"id": "video_720", "height": 720, "label": "Story Video (MP4)", "format": "mp4", "type": "video", "size": ""}
                        ],
                        "audio_options": [],
                        "image_options": []
                    }
                elif info.get("thumbnail") or info.get("url"):
                    img_url = info.get("url") or info.get("thumbnail")
                    return {
                        "source": "Instagram",
                        "badge": "Instagram",
                        "media_type": "image",
                        "title": title,
                        "thumbnail": img_url,
                        "duration": "",
                        "is_gallery": False,
                        "items": [
                            {"index": 1, "type": "image", "url": img_url, "thumbnail": img_url, "format": "jpg"}
                        ],
                        "video_options": [],
                        "audio_options": [],
                        "image_options": [
                            {"id": "image_jpg", "label": "Story Image (JPG)", "format": "jpg", "type": "image"},
                            {"id": "image_png", "label": "Story Image (PNG)", "format": "png", "type": "image"}
                        ],
                        "direct_download_url": img_url
                    }
    except Exception as e:
        logger.debug(f"yt-dlp story extraction unauthenticated notice: {e}")

    # 2. Check public page / embed / Open Graph metadata
    try:
        res = requests.get(url, headers=CRAWLER_HEADERS, timeout=10)
        if res.status_code == 200:
            og_vid = re.search(r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)["\']', res.text)
            if og_vid:
                vid_url = html.unescape(og_vid.group(1))
                return {
                    "source": "Instagram",
                    "badge": "Instagram",
                    "media_type": "video",
                    "title": f"Story by @{username}",
                    "thumbnail": None,
                    "duration": "",
                    "is_gallery": False,
                    "items": [],
                    "video_options": [
                        {"id": "video_mp4", "height": 720, "label": "Story Video (MP4)", "format": "mp4", "type": "video", "size": ""}
                    ],
                    "audio_options": [],
                    "image_options": [],
                    "direct_video_url": vid_url
                }

            og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', res.text)
            if og_img:
                img_url = html.unescape(og_img.group(1))
                if "profile_pic" not in img_url:
                    return {
                        "source": "Instagram",
                        "badge": "Instagram",
                        "media_type": "image",
                        "title": f"Story by @{username}",
                        "thumbnail": img_url,
                        "duration": "",
                        "is_gallery": False,
                        "items": [
                            {"index": 1, "type": "image", "url": img_url, "thumbnail": img_url, "format": "jpg"}
                        ],
                        "video_options": [],
                        "audio_options": [],
                        "image_options": [
                            {"id": "image_jpg", "label": "Story Image (JPG)", "format": "jpg", "type": "image"}
                        ],
                        "direct_download_url": img_url
                    }
    except Exception:
        pass

    # 3. Instagram requires authentication for this Story
    raise ValueError(
        "This Instagram Story is not publicly accessible to this downloader without authentication."
    )

def extract_public_embed_media(shortcode: str) -> Optional[Dict[str, Any]]:
    """
    Extracts publicly accessible image/video resources from the Instagram public embed.
    Accurately distinguishes IMAGE vs GALLERY vs VIDEO. Never generates fake audio options.
    """
    embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
    try:
        res = requests.get(embed_url, headers=CRAWLER_HEADERS, timeout=12)
        if res.status_code != 200:
            return None

        text = res.text

        # 1. Extract username / author for clean title
        username = ""
        user_m = re.search(r'class="UsernameText"[^>]*>(.*?)</div>', text, re.DOTALL)
        if user_m:
            username = re.sub(r'<[^>]+>', '', user_m.group(1)).strip()
            username = re.sub(r'[0-9]+(?:\.[0-9]+)?[KMkm]?\s*followers?.*$', '', username).strip()
        if not username:
            user_link = re.search(r'instagram\.com\/([a-zA-Z0-9_\.]+)\/', text)
            if user_link and user_link.group(1) not in ("p", "reel", "explore"):
                username = user_link.group(1)

        post_title = f"Post by {username}" if username else "Instagram Post"

        # 2. Check for public video in embed
        video_matches = re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', text)
        if video_matches:
            video_url = html.unescape(video_matches[0])
            thumb_match = re.search(r'<img[^>]*class=["\'][^"\']*EmbeddedMediaImage[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', text)
            thumb = html.unescape(thumb_match.group(1)) if thumb_match else None
            return {
                "source": "Instagram",
                "badge": "Instagram",
                "media_type": "video",
                "title": post_title,
                "thumbnail": thumb,
                "duration": "",
                "is_gallery": False,
                "items": [],
                "video_options": [
                    {"id": "video_mp4", "height": 720, "label": "MP4 Video", "format": "mp4", "type": "video", "size": ""}
                ],
                "audio_options": [
                    {"id": "audio_mp3", "label": "MP3 Audio", "format": "mp3", "type": "audio", "quality": "320k"}
                ],
                "image_options": [],
                "direct_video_url": video_url
            }

        # 3. Primary Post Image (EmbeddedMediaImage)
        primary_img = None
        m_embedded = re.search(r'<img[^>]*class=["\'][^"\']*EmbeddedMediaImage[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', text)
        if not m_embedded:
            m_embedded = re.search(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*EmbeddedMediaImage', text)

        if m_embedded:
            primary_img = html.unescape(m_embedded.group(1))

        # Check for multiple carousel items in the embed
        candidate_images = []
        if primary_img:
            candidate_images.append(primary_img)

        # Look for additional carousel slides
        carousel_urls = set()
        for u in re.findall(r'https:\/\/[^"\'\s\\<>]+(?:fbcdn\.net|cdninstagram\.com)[^"\'\s\\<>]+', text):
            clean_u = html.unescape(u.replace('\\/', '/'))
            if 'profile_pic' not in clean_u and 's100x100' not in clean_u and 'rsrc.php' not in clean_u:
                if 'CAROUSEL_ITEM' in clean_u or 'c0.' in clean_u:
                    carousel_urls.add(clean_u)

        # Validate candidate URLs
        valid_images = []
        for img_url in candidate_images:
            try:
                head_check = requests.get(img_url, headers=BROWSER_HEADERS, timeout=6, stream=True)
                if head_check.status_code == 200:
                    valid_images.append(img_url)
                head_check.close()
            except Exception:
                pass

        # If primary image is verified, check other carousel candidates
        if len(carousel_urls) > 0 and len(valid_images) > 0:
            for extra_url in carousel_urls:
                if extra_url not in valid_images and len(valid_images) < 12:
                    try:
                        c_check = requests.get(extra_url, headers=BROWSER_HEADERS, timeout=4, stream=True)
                        if c_check.status_code == 200 and int(c_check.headers.get("content-length", 0)) > 20000:
                            valid_images.append(extra_url)
                        c_check.close()
                    except Exception:
                        pass

        if not valid_images and primary_img:
            valid_images = [primary_img]

        if not valid_images:
            return None

        # 4. If more than 1 image -> GALLERY
        if len(valid_images) > 1:
            items = []
            for idx, img_url in enumerate(valid_images):
                items.append({
                    "index": idx + 1,
                    "type": "image",
                    "title": f"Image {idx + 1}",
                    "url": img_url,
                    "thumbnail": img_url,
                    "format": "jpg"
                })

            return {
                "source": "Instagram",
                "badge": "Instagram",
                "media_type": "gallery",
                "title": f"{post_title} (Carousel)",
                "thumbnail": valid_images[0],
                "duration": "",
                "is_gallery": True,
                "item_count": len(items),
                "items": items,
                "video_options": [],
                "audio_options": [],
                "image_options": [],
                "formats": [
                    {"id": "zip_all", "label": "Download All (.ZIP)", "format": "zip", "type": "gallery"}
                ]
            }

        # 5. Exactly 1 image -> IMAGE (Never Audio!)
        single_img = valid_images[0]
        return {
            "source": "Instagram",
            "badge": "Instagram",
            "media_type": "image",
            "title": post_title,
            "thumbnail": single_img,
            "duration": "",
            "is_gallery": False,
            "items": [
                {"index": 1, "type": "image", "url": single_img, "thumbnail": single_img, "format": "jpg"}
            ],
            "video_options": [],
            "audio_options": [],
            "image_options": [
                {"id": "image_jpg", "label": "Image (JPG)", "format": "jpg", "type": "image"},
                {"id": "image_png", "label": "Image (PNG)", "format": "png", "type": "image"},
                {"id": "image_webp", "label": "Image (WEBP)", "format": "webp", "type": "image"}
            ],
            "direct_download_url": single_img
        }

    except Exception as e:
        logger.error(f"Error extracting Instagram embed media: {e}", exc_info=True)
        return None

def analyze_instagram_url(url: str) -> Dict[str, Any]:
    """
    Dedicated analyzer for all Instagram URLs:
    - Posts: /p/{code}/ (Image, Video, Carousel)
    - Reels: /reel/{code}/ or /reels/{code}/
    - Stories: /stories/{username}/{story_id}/
    - Profiles: /{username}/ (Public profile picture / DP)
    """
    classified = classify_instagram_url(url)
    kind = classified.get("kind")

    # 1. Stories
    if kind == "story":
        return extract_public_story_media(
            url=url,
            username=classified.get("username", "user"),
            story_id=classified.get("story_id", "")
        )

    # 2. Profiles (DP)
    if kind == "profile":
        return extract_public_profile_media(username=classified.get("username", "user"))

    # 3. Reels & Posts
    shortcode = classified.get("shortcode")

    # Attempt yt-dlp first for video streams
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "socket_timeout": 15,
        "noplaylist": False,
        "ignoreerrors": True,
    }

    yt_info = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            yt_info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.debug(f"yt-dlp Instagram extraction notice: {e}")

    # Inspect if yt-dlp found actual video formats
    if yt_info:
        # Check playlist / entries
        if yt_info.get("_type") == "playlist" or yt_info.get("entries"):
            entries = [e for e in yt_info.get("entries", []) if e]
            video_entries = [e for e in entries if any(f.get("vcodec") != "none" for f in e.get("formats", []))]
            if video_entries:
                items = []
                for idx, entry in enumerate(video_entries):
                    items.append({
                        "index": idx + 1,
                        "type": "video",
                        "title": entry.get("title") or f"Video {idx + 1}",
                        "thumbnail": entry.get("thumbnail"),
                        "url": entry.get("url") or entry.get("webpage_url") or url
                    })
                return {
                    "source": "Instagram",
                    "badge": "Instagram",
                    "media_type": "gallery",
                    "title": yt_info.get("title") or "Instagram Video Carousel",
                    "thumbnail": items[0]["thumbnail"] if items else None,
                    "duration": "",
                    "is_gallery": True,
                    "item_count": len(items),
                    "items": items,
                    "video_options": [],
                    "audio_options": [],
                    "image_options": [],
                    "formats": [
                        {"id": "zip_all", "label": "Download All (.ZIP)", "format": "zip", "type": "gallery"}
                    ]
                }

        formats_raw = yt_info.get("formats", [])
        has_video = any(f.get("vcodec") != "none" and f.get("height") for f in formats_raw)

        if has_video:
            video_qualities = []
            seen_h = set()
            for f in formats_raw:
                h = f.get("height")
                if h and h not in seen_h and f.get("vcodec") != "none":
                    seen_h.add(h)
                    video_qualities.append({
                        "id": f"video_{h}",
                        "height": h,
                        "label": f"{h}p (MP4)",
                        "format": "mp4",
                        "type": "video",
                        "size": ""
                    })
            video_qualities.sort(key=lambda x: x["height"], reverse=True)

            title_prefix = "Instagram Reel" if kind == "reel" else "Instagram Video"
            return {
                "source": "Instagram",
                "badge": "Instagram",
                "media_type": "video",
                "title": yt_info.get("title") or title_prefix,
                "thumbnail": yt_info.get("thumbnail"),
                "duration": yt_info.get("duration", ""),
                "is_gallery": False,
                "items": [],
                "video_options": video_qualities if video_qualities else [
                    {"id": "video_720", "height": 720, "label": "HD Video (MP4)", "format": "mp4", "type": "video", "size": ""}
                ],
                "audio_options": [
                    {"id": "audio_mp3", "label": "MP3 Audio (High Quality)", "format": "mp3", "type": "audio", "quality": "320k"},
                    {"id": "audio_m4a", "label": "M4A Audio", "format": "m4a", "type": "audio", "quality": "auto"}
                ],
                "image_options": []
            }

    # If yt-dlp did not extract video, use public embed fallback
    if shortcode:
        embed_media = extract_public_embed_media(shortcode)
        if embed_media:
            return embed_media

    # If unauthenticated extraction fails:
    media_desc = "Reel" if kind == "reel" else "post"
    raise ValueError(
        f"No downloadable public media was found for this Instagram {media_desc}. "
        "The content may be private, protected, expired, or require an account login."
    )
