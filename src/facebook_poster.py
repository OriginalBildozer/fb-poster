import json
import os
import time
import random
import logging

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

COOKIES_ENV = "FB_COOKIES"
COOKIES_FILE = "fb_cookies.json"


def _random_delay(lo=1.5, hi=3.5):
    time.sleep(random.uniform(lo, hi))


def _human_type(locator, text):
    for char in text:
        locator.type(char, delay=random.randint(40, 120))


class FacebookPoster:
    def __init__(self):
        self.email = os.environ["FB_EMAIL"]
        self.password = os.environ["FB_PASSWORD"]
        self.page_url = os.environ["FB_PAGE_URL"].rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def post(self, text, image_path=None):
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 768},
                locale="fr-FR",
            )

            # Inject stealth script
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            self._load_cookies(ctx)

            page = ctx.new_page()
            page.goto("https://www.facebook.com/", timeout=30000)
            page.wait_for_load_state("domcontentloaded")

            if self._needs_login(page):
                logger.info("Session expirée — connexion en cours…")
                self._login(page)

            self._go_to_page(page)
            self._create_post(page, text, image_path)

            self._save_cookies(ctx)
            browser.close()
            logger.info("Post publié avec succès.")

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _needs_login(self, page):
        return "login" in page.url or page.query_selector("#email") is not None

    def _login(self, page):
        page.goto("https://www.facebook.com/login", timeout=20000)
        page.wait_for_selector("#email", timeout=10000)
        _random_delay()
        _human_type(page.locator("#email"), self.email)
        _random_delay(0.5, 1.2)
        _human_type(page.locator("#pass"), self.password)
        _random_delay(0.8, 1.5)
        page.click('[name="login"]')
        page.wait_for_load_state("networkidle", timeout=20000)
        _random_delay(2, 4)

        if "checkpoint" in page.url or "two_step" in page.url:
            raise RuntimeError(
                "Facebook demande une vérification 2FA — connexion impossible en mode headless."
            )

    def _load_cookies(self, ctx):
        # Priority: env var > file
        raw = os.environ.get(COOKIES_ENV)
        if raw:
            try:
                ctx.add_cookies(json.loads(raw))
                return
            except Exception:
                pass
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE) as f:
                try:
                    ctx.add_cookies(json.load(f))
                except Exception:
                    pass

    def _save_cookies(self, ctx):
        cookies = ctx.cookies()
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f, indent=2)

    # ------------------------------------------------------------------
    # Page navigation & posting
    # ------------------------------------------------------------------

    def _go_to_page(self, page):
        page.goto(self.page_url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        _random_delay(2, 4)

    def _create_post(self, page, text, image_path=None):
        # Try to open the post composer
        composer_opened = False

        # Selector list for the "Write something…" clickable area (changes often)
        trigger_selectors = [
            '[aria-label*="Écrire quelque chose"]',
            '[aria-label*="Write something"]',
            '[data-testid="status-attachment-mentions-input"]',
            'div[role="button"]:has-text("Écrire quelque chose")',
            'div[role="button"]:has-text("Write something")',
            'span:has-text("Écrire quelque chose")',
            'span:has-text("Write something")',
        ]

        for sel in trigger_selectors:
            try:
                el = page.wait_for_selector(sel, timeout=5000)
                if el:
                    el.click()
                    _random_delay(1.5, 2.5)
                    composer_opened = True
                    break
            except PWTimeout:
                continue

        if not composer_opened:
            # Last resort: look for any "Create post" button
            try:
                page.get_by_role("button", name=lambda n: "post" in n.lower() or "publier" in n.lower()).first.click()
                _random_delay(1.5, 2.5)
                composer_opened = True
            except Exception:
                pass

        if not composer_opened:
            raise RuntimeError("Impossible d'ouvrir le compositeur de post.")

        # Type the post text
        editor_selectors = [
            '[contenteditable="true"][aria-label*="Écrire"]',
            '[contenteditable="true"][aria-label*="Write"]',
            '[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ]

        typed = False
        for sel in editor_selectors:
            try:
                editor = page.wait_for_selector(sel, timeout=5000)
                if editor:
                    editor.click()
                    _random_delay(0.5, 1)
                    # Use clipboard paste for long text (faster, more reliable)
                    page.keyboard.press("Control+a")
                    _random_delay(0.2, 0.4)
                    # Type in chunks to avoid timeout
                    for chunk in [text[i : i + 200] for i in range(0, len(text), 200)]:
                        editor.type(chunk, delay=20)
                    typed = True
                    break
            except PWTimeout:
                continue

        if not typed:
            raise RuntimeError("Impossible de trouver le champ de texte du compositeur.")

        # Add image if provided
        if image_path and os.path.exists(image_path):
            self._attach_image(page, image_path)

        _random_delay(1, 2)

        # Click Post / Publier button
        post_button_selectors = [
            'div[aria-label="Publier"]',
            'div[aria-label="Post"]',
            'button[aria-label="Publier"]',
            'button[aria-label="Post"]',
        ]

        posted = False
        for sel in post_button_selectors:
            try:
                btn = page.wait_for_selector(sel, timeout=5000)
                if btn:
                    btn.click()
                    _random_delay(3, 5)
                    posted = True
                    break
            except PWTimeout:
                continue

        if not posted:
            # Try by role
            try:
                page.get_by_role("button", name=lambda n: n.lower() in ("publier", "post", "share", "partager")).click()
                _random_delay(3, 5)
            except Exception:
                raise RuntimeError("Impossible de cliquer sur le bouton Publier.")

    def _attach_image(self, page, image_path):
        photo_selectors = [
            '[aria-label*="Photo"]',
            '[aria-label*="photo"]',
            'input[type="file"][accept*="image"]',
        ]

        for sel in photo_selectors:
            try:
                if "input" in sel:
                    page.set_input_files(sel, image_path)
                else:
                    page.click(sel, timeout=4000)
                    _random_delay(1, 2)
                    # After clicking the photo button an <input type="file"> appears
                    with page.expect_file_chooser() as fc_info:
                        page.click(sel, timeout=3000)
                    fc_info.value.set_files(image_path)

                _random_delay(2, 4)
                return
            except Exception:
                continue

        # Try file chooser via keyboard shortcut area click
        try:
            with page.expect_file_chooser(timeout=5000) as fc_info:
                page.get_by_role("button", name=lambda n: "photo" in n.lower() or "image" in n.lower()).first.click()
            fc_info.value.set_files(image_path)
            _random_delay(2, 4)
        except Exception:
            logger.warning("Impossible d'attacher l'image — le post sera publié sans image.")
