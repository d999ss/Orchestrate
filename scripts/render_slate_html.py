"""Render the user-provided HTML slate to a 1920x1080 PNG using headless Chromium."""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = sys.argv[1] if len(sys.argv) > 1 else "/Users/donnysmith/Desktop/bttr-credits-slate.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/slate.png"

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        device_scale_factor=1,
    )
    page = context.new_page()
    page.goto(f"file://{HTML}")
    # Wait for fonts to load (Google Fonts download)
    page.wait_for_load_state("networkidle", timeout=30000)
    # Extra grace period for font swap
    page.wait_for_timeout(1500)
    page.screenshot(path=OUT, full_page=False, omit_background=False)
    browser.close()

print(f"Wrote {OUT}")
