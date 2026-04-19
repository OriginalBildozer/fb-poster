import hashlib
import re
import feedparser
from bs4 import BeautifulSoup


RSS_URL = "https://www.google.fr/alerts/feeds/05073360985782739742/9023529830405776624"


def strip_html(text):
    if not text:
        return ""
    return BeautifulSoup(text, "lxml").get_text(separator=" ").strip()


def extract_image_from_entry(entry):
    # media:content
    for media in entry.get("media_content", []):
        if media.get("type", "").startswith("image") or media.get("url", "").endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".gif")
        ):
            return media.get("url")

    # enclosures
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href") or enc.get("url")

    # img tag inside summary/content
    html = entry.get("summary", "") or ""
    for content in entry.get("content", []):
        html += content.get("value", "")

    soup = BeautifulSoup(html, "lxml")
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]

    return None


def get_rss_items():
    feed = feedparser.parse(RSS_URL)
    items = []

    for entry in feed.entries:
        raw_id = entry.get("id") or entry.get("link") or entry.get("title") or ""
        item_id = hashlib.md5(raw_id.encode()).hexdigest()

        title = strip_html(entry.get("title", ""))
        summary = strip_html(entry.get("summary", ""))
        link = entry.get("link", "")
        image = extract_image_from_entry(entry)

        # Google Alerts wraps the real URL — unwrap it
        if "google.com/url?q=" in link:
            match = re.search(r"[?&]q=([^&]+)", link)
            if match:
                from urllib.parse import unquote
                link = unquote(match.group(1))

        items.append(
            {
                "id": item_id,
                "title": title,
                "summary": summary,
                "link": link,
                "image": image,
                "published": entry.get("published", ""),
            }
        )

    return items
