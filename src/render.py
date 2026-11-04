"""Renderização headless de uma página Streamlit via Playwright."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def render_page(url: str, wait_selector: str, extra_seconds: int = 3,
                formats: list[str] | None = None) -> dict:
    formats = formats or ["png"]
    out_dir = Path(os.environ.get("OUTPUT_DIR", "/tmp"))
    out_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = url.rstrip("/").split("/")[-1] or "page"
    base = out_dir / f"{safe}_{stamp}"

    results = {"url": url, "files": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=120000)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=60000)
        page.wait_for_timeout(extra_seconds * 1000)

        if "png" in formats:
            png = f"{base}.png"
            page.screenshot(path=png, full_page=True)
            results["files"]["png"] = png
        if "pdf" in formats:
            pdf = f"{base}.pdf"
            page.pdf(path=pdf, format="A4", print_background=True)
            results["files"]["pdf"] = pdf
        if "html" in formats:
            html = f"{base}.html"
            Path(html).write_text(page.content(), encoding="utf-8")
            results["files"]["html"] = html

        browser.close()
    return results
