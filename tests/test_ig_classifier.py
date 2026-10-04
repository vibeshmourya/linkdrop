import re

def classify_instagram_url(url: str):
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

# Test cases
test_cases = [
    "https://www.instagram.com/p/DbhmxLlFxVE/?stkn=MXF2dHZvMG4wN25hag==",
    "https://www.instagram.com/reel/C3abc123/?igsh=123",
    "https://www.instagram.com/reels/C3abc123/",
    "https://www.instagram.com/stories/some_user/3321456789012345678/",
    "https://www.instagram.com/ram.ji_ke_darshan/",
    "https://www.instagram.com/explore/"
]

for tc in test_cases:
    print(tc, "->", classify_instagram_url(tc))
