import hashlib
import re
from urllib.parse import unquote

import feedparser
import requests
from bs4 import BeautifulSoup

RSS_URL = "https://www.google.fr/alerts/feeds/05073360985782739742/9023529830405776624"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/atom+xml,application/xml,text/xml,*/*",
}


def strip_html(text):
    if not text:
        return ""
    if "<" not in text:
        return text.strip()
    return BeautifulSoup(text, "lxml").get_text(separator=" ").strip()


def _unwrap_google_url(url):
    """Extrait l'URL réelle depuis un lien de redirection Google Alerts."""
    if not url:
        return url
    # format &url=... ou ?url=...
    match = re.search(r"[?&]url=([^&]+)", url)
    if match:
        return unquote(match.group(1))
    # format &q=... ou ?q=...
    match = re.search(r"[?&]q=([^&]+)", url)
    if match:
        return unquote(match.group(1))
    return url


def _get_content(entry):
    """Retourne le texte brut du champ content ou summary (Atom vs RSS)."""
    # Atom : <content type="html">
    for block in entry.get("content", []):
        value = block.get("value", "")
        if value:
            return strip_html(value)
    # RSS : <summary> ou <description>
    return strip_html(entry.get("summary", "") or entry.get("description", ""))


def extract_image_from_entry(entry):
    for media in entry.get("media_content", []):
        url = media.get("url", "")
        if media.get("type", "").startswith("image") or url.endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".gif")
        ):
            return url

    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href") or enc.get("url")

    # Cherche une balise <img> dans le contenu HTML brut
    html = ""
    for block in entry.get("content", []):
        html += block.get("value", "")
    html += entry.get("summary", "") or ""

    if "<" not in html:
        return None
    soup = BeautifulSoup(html, "lxml")
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]

    return None


def get_rss_items():
    # Téléchargement manuel avec User-Agent pour contourner le blocage de Google
    resp = requests.get(RSS_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)

    items = []
    for entry in feed.entries:
        raw_id = entry.get("id") or entry.get("link") or entry.get("title") or ""
        item_id = hashlib.md5(raw_id.encode()).hexdigest()

        title = strip_html(entry.get("title", ""))
        summary = _get_content(entry)
        link = _unwrap_google_url(entry.get("link", ""))
        image = extract_image_from_entry(entry)

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
