import requests
import re
import html
import yt_dlp

CRAWLER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def inspect_profile(username):
    url = f"https://www.instagram.com/{username}/"
    res = requests.get(url, headers=CRAWLER_HEADERS, timeout=10)
    print(f"Profile {username}: status={res.status_code}, len={len(res.text)}")
    text = res.text

    # Search for og:image
    og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', text)
    if not og_img:
        og_img = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', text)
    if og_img:
        print("  og:image found:", html.unescape(og_img.group(1))[:100])
        return html.unescape(og_img.group(1))
    
    # Search for profile_pic CDN url
    m = re.search(r'https:\/\/[^"\'\s\\<>]+(?:fbcdn\.net|cdninstagram\.com)[^"\'\s\\<>]*profile_pic[^\s"\'\\<>]*', text)
    if m:
        clean = html.unescape(m.group(0).replace('\\/', '/'))
        print("  profile_pic found:", clean[:100])
        return clean
    
    print("  No profile picture found.")
    return None

def inspect_story(url):
    print(f"Story test: {url}")
    # 1. Try yt-dlp first
    ydl_opts = {"skip_download": True, "quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print("  yt-dlp extracted story:", info.get("title") if info else None)
            return info
    except Exception as e:
        print("  yt-dlp story notice:", str(e)[:150])

    # 2. Try public page / embed / metadata
    try:
        res = requests.get(url, headers=CRAWLER_HEADERS, timeout=10)
        print(f"  Story page HTTP status={res.status_code}")
        og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', res.text)
        if og_img:
            print("  Story og:image found:", og_img.group(1)[:100])
    except Exception as e:
        print("  Story fetch error:", e)
    return None

if __name__ == "__main__":
    inspect_profile("ram.ji_ke_darshan")
    inspect_story("https://www.instagram.com/stories/instagram/1234567890123456789/")
