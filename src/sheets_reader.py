import csv
import re
import requests
from io import StringIO

SHEET_URL = "https://docs.google.com/spreadsheets/d/1QrPE9M4ZRYazj04iUN86AXwzNLjtaZoR_JF_78e-NXQ/edit?gid=0#gid=0"
SHEET_ID = "1QrPE9M4ZRYazj04iUN86AXwzNLjtaZoR_JF_78e-NXQ"
GID = "0"

URL_PATTERN = re.compile(r"https?://\S+")


def _is_url(value):
    return bool(URL_PATTERN.match(value.strip()))


def get_affiliate_links():
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    response = requests.get(csv_url, timeout=15)
    response.raise_for_status()

    reader = csv.DictReader(StringIO(response.text))
    links = []

    for row in reader:
        url = None
        description = None
        image = None

        for key, value in row.items():
            if not value:
                continue
            key_lower = key.lower().strip()
            if key_lower in ("url", "lien", "link", "affiliate", "affiliation") and _is_url(value):
                url = value.strip()
            elif key_lower in ("description", "texte", "text", "message", "caption"):
                description = value.strip()
            elif key_lower in ("image", "image_url", "photo") and _is_url(value):
                image = value.strip()

        # Fallback: pick first column that looks like a URL
        if not url:
            for value in row.values():
                if value and _is_url(value):
                    url = value.strip()
                    break

        if url:
            links.append({"url": url, "description": description, "image": image})

    return links
