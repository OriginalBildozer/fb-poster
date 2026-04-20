import os
import logging
import requests

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


class FacebookPoster:
    def __init__(self):
        self.page_id = os.environ["FB_PAGE_ID"]
        self.token = os.environ["FB_PAGE_TOKEN"]

    def post(self, text, image_path=None):
        if image_path and os.path.exists(image_path):
            self._post_with_photo(text, image_path)
        else:
            self._post_text(text)

    def _post_text(self, text):
        resp = requests.post(
            f"{GRAPH_URL}/{self.page_id}/feed",
            data={"message": text, "access_token": self.token},
            timeout=30,
        )
        self._check(resp)
        logger.info(f"Post texte publié : {resp.json().get('id')}")

    def _post_with_photo(self, text, image_path):
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{GRAPH_URL}/{self.page_id}/photos",
                data={"caption": text, "access_token": self.token},
                files={"source": f},
                timeout=60,
            )
        self._check(resp)
        logger.info(f"Post photo publié : {resp.json().get('id')}")

    def _check(self, resp):
        if not resp.ok:
            raise RuntimeError(f"Erreur API Graph ({resp.status_code}) : {resp.text}")
