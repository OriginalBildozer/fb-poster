#!/usr/bin/env python3
"""
Facebook Bot — poste depuis un flux RSS + liens d'affiliation (Google Sheets).
Appelé par GitHub Actions 5 fois par jour.
"""

import logging
import os
import sys
import time

from image_handler import get_image_path
from facebook_poster import FacebookPoster
from rss_reader import get_rss_items
from sheets_reader import get_affiliate_links
from state import load_state, save_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

DELAY_BETWEEN_POSTS = int(os.environ.get("DELAY_BETWEEN_POSTS", "60"))  # seconds


def build_rss_text(item):
    parts = []
    if item["title"]:
        parts.append(item["title"])
    if item["summary"]:
        parts.append(item["summary"])
    if item["link"]:
        parts.append(f"\n🔗 {item['link']}")
    return "\n\n".join(parts)


def build_affiliate_text(affiliate):
    if affiliate.get("description"):
        return f"{affiliate['description']}\n\n👉 {affiliate['url']}"
    return f"👉 {affiliate['url']}"


def main():
    state = load_state()
    posted_ids = set(state.get("posted_ids", []))
    affiliate_index = state.get("affiliate_index", 0)

    # --- Fetch data ---
    logger.info("Récupération du flux RSS…")
    rss_items = get_rss_items()
    logger.info(f"{len(rss_items)} articles trouvés dans le flux.")

    logger.info("Récupération des liens d'affiliation…")
    affiliate_links = get_affiliate_links()
    if not affiliate_links:
        logger.error("Aucun lien d'affiliation trouvé dans le Google Sheet.")
        sys.exit(1)
    logger.info(f"{len(affiliate_links)} liens d'affiliation chargés.")

    # --- Pick next unposted RSS item ---
    unposted = [item for item in rss_items if item["id"] not in posted_ids]
    if not unposted:
        logger.info("Aucun nouvel article RSS à publier. Fin du script.")
        return

    rss_item = unposted[0]
    logger.info(f"Article sélectionné : {rss_item['title'][:80]}")

    # --- Resolve images ---
    logger.info("Recherche d'une image pour l'article RSS…")
    rss_image = get_image_path(rss_item, keywords=rss_item.get("title", ""))

    affiliate = affiliate_links[affiliate_index % len(affiliate_links)]
    next_affiliate_index = (affiliate_index + 1) % len(affiliate_links)

    logger.info("Recherche d'une image pour le lien d'affiliation…")
    aff_image_item = {"image": affiliate.get("image"), "link": affiliate.get("url")}
    aff_image = get_image_path(aff_image_item, keywords="promotion deal")

    # --- Post ---
    poster = FacebookPoster()

    # 1. Post RSS content
    logger.info("Publication de l'article RSS sur Facebook…")
    rss_text = build_rss_text(rss_item)
    try:
        poster.post(rss_text, image_path=rss_image)
        logger.info("Article RSS publié.")
    except Exception as exc:
        logger.error(f"Échec de la publication RSS : {exc}")
        sys.exit(1)
    finally:
        if rss_image:
            try:
                os.unlink(rss_image)
            except OSError:
                pass

    # Wait before the affiliate post
    logger.info(f"Pause de {DELAY_BETWEEN_POSTS}s avant le post d'affiliation…")
    time.sleep(DELAY_BETWEEN_POSTS)

    # 2. Post affiliate link
    logger.info("Publication du lien d'affiliation sur Facebook…")
    aff_text = build_affiliate_text(affiliate)
    try:
        poster.post(aff_text, image_path=aff_image)
        logger.info("Lien d'affiliation publié.")
    except Exception as exc:
        logger.error(f"Échec de la publication d'affiliation : {exc}")
    finally:
        if aff_image:
            try:
                os.unlink(aff_image)
            except OSError:
                pass

    # --- Save state ---
    from datetime import datetime, timezone

    posted_ids.add(rss_item["id"])
    state["posted_ids"] = list(posted_ids)
    state["affiliate_index"] = next_affiliate_index
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    logger.info("État sauvegardé.")


if __name__ == "__main__":
    main()
