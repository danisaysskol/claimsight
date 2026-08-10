"""Capture the 5 Streamlit dashboard pages to docs/screenshots/ (headless).

Run against a live Streamlit server via Playwright/Chromium. Intended to run in
a container on the same Docker network as the Streamlit container:

    pip install playwright && playwright install --with-deps chromium
    STREAMLIT_URL=http://claimsight_st:8501 python scripts/screenshot_dashboard.py
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("STREAMLIT_URL", "http://claimsight_st:8501/")
OUT = Path(os.environ.get("SHOT_DIR", "/app/docs/screenshots"))
PAGES = [
    ("Executive Summary", "executive"),
    ("Claims Operations", "operations"),
    ("Financial Performance", "financial"),
    ("Provider Network", "network"),
    ("Data Quality", "data_quality"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        page.goto(URL, wait_until="networkidle", timeout=90_000)
        page.wait_for_timeout(5000)
        for label, slug in PAGES:
            try:
                page.get_by_text(label, exact=True).first.click(timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                print(f"WARN: could not select '{label}': {exc}")
            page.wait_for_timeout(5000)      # let Streamlit rerun + charts render
            page.mouse.wheel(0, -5000)       # scroll to top
            page.wait_for_timeout(500)
            out = OUT / f"{slug}.png"
            page.screenshot(path=str(out))
            print(f"saved {out}")
        browser.close()
    print("SCREENSHOTS DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
