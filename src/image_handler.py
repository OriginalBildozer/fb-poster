import os
import tempfile
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def get_og_image(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        for attr in ({"property": "og:image"}, {"name": "twitter:image"}, {"name": "twitter:image:src"}):
            tag = soup.find("meta", attr)
            if tag and tag.get("content"):
                return tag["content"]
    except Exception:
        pass
    return None


def _unsplash_url(keywords):
    query = "+".join(str(keywords).split()[:4])
    return f"https://source.unsplash.com/1200x630/?{query}"


def download_image(url):
    """Download image URL to a temp file, return its path (caller must delete)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        ext = ".jpg"
        if "png" in content_type:
            ext = ".png"
        elif "gif" in content_type:
            ext = ".gif"
        elif "webp" in content_type:
            ext = ".webp"

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in resp.iter_content(8192):
            tmp.write(chunk)
        tmp.close()
        return tmp.name
    except Exception:
        return None


def get_image_path(item, keywords=None):
    """
    Resolve the best image for a post item and return a local file path.
    Returns None if no image could be found/downloaded.
    item keys: image (direct URL), link (page to scrape OG)
    """
    candidates = []

    if item.get("image"):
        candidates.append(item["image"])

    if item.get("link"):
        og = get_og_image(item["link"])
        if og:
            candidates.append(og)

    if not candidates and keywords:
        candidates.append(_unsplash_url(keywords))

    for url in candidates:
        path = download_image(url)
        if path and os.path.getsize(path) > 1024:
            return path
        if path:
            os.unlink(path)

    return None
