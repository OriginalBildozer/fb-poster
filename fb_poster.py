#!/usr/bin/env python3
"""
Lancez ce script UNE FOIS en local pour générer fb_cookies.json.
Ensuite copiez son contenu dans le secret GitHub FB_COOKIES.

Usage :
  pip install playwright
  playwright install chromium
  python setup_cookies.py
"""

import json
from playwright.sync_api import sync_playwright

EMAIL = input("Email Facebook : ").strip()
PASSWORD = input("Mot de passe Facebook : ").strip()

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)  # visible pour gérer le 2FA si besoin
    ctx = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    )
    ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    page = ctx.new_page()
    page.goto("https://www.facebook.com/login")
    page.fill("#email", EMAIL)
    page.fill("#pass", PASSWORD)
    page.click('[name="login"]')
    page.wait_for_load_state("networkidle")

    if "checkpoint" in page.url or "two_step" in page.url:
        print("\n⚠️  Facebook demande une vérification. Complétez-la dans la fenêtre du navigateur.")
        input("Appuyez sur Entrée une fois connecté…")

    cookies = ctx.cookies()
    with open("fb_cookies.json", "w") as f:
        json.dump(cookies, f, indent=2)

    print(f"\n✅ {len(cookies)} cookies sauvegardés dans fb_cookies.json")
    print("Copiez le contenu de ce fichier dans le secret GitHub FB_COOKIES.")
    browser.close()
