"""Renderização headless de uma página Streamlit via Playwright."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def _setup_page(browser, viewport: dict):
    context = browser.new_context(viewport=viewport)
    return context.new_page()


def _wait_for_content(page, wait_selector: str, wait_end_selector: str, wait_end_timeout: int):
    if wait_selector:
        page.wait_for_selector(wait_selector, timeout=60000)
    if wait_end_selector:
        try:
            page.wait_for_selector(wait_end_selector, timeout=wait_end_timeout)
        except Exception:
            pass


def _scroll_to_load(page, steps: int, step_px: int):
    for _ in range(steps):
        page.evaluate(f"window.scrollBy(0, {step_px})")
        page.wait_for_timeout(300)
    page.wait_for_timeout(2000)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)


def _capture(page, base: Path, formats: list[str]) -> dict[str, str]:
    files = {}
    if "png" in formats:
        page.screenshot(path=f"{base}.png", full_page=True)
        files["png"] = f"{base}.png"
    if "pdf" in formats:
        page.pdf(path=f"{base}.pdf", format="A4", print_background=True)
        files["pdf"] = f"{base}.pdf"
    if "html" in formats:
        Path(f"{base}.html").write_text(page.content(), encoding="utf-8")
        files["html"] = f"{base}.html"
    return files


def render_page(url: str, formats: list[str] | None = None,
                render_config: dict | None = None) -> dict:
    formats = formats or ["png"]
    rc = render_config or {}
    viewport = {
        "width": rc.get("viewport_width", 1920),
        "height": rc.get("viewport_height", 4000),
    }
    wait_selector = rc.get("wait_selector", "")
    wait_end_selector = rc.get("wait_end_selector", "")
    wait_end_timeout = rc.get("wait_end_timeout", 15000)
    scroll_steps = rc.get("scroll_steps", 10)
    scroll_step_px = rc.get("scroll_step_px", 500)
    extra = rc.get("extra_seconds", 3)

    out_dir = Path(os.environ.get("OUTPUT_DIR", "/tmp"))
    out_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = url.rstrip("/").split("/")[-1] or "page"
    base = out_dir / f"{safe}_{stamp}"

    results = {"url": url, "files": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = _setup_page(browser, viewport)
        page.goto(url, wait_until="networkidle", timeout=120000)
        _wait_for_content(page, wait_selector, wait_end_selector, wait_end_timeout)
        _scroll_to_load(page, scroll_steps, scroll_step_px)
        page.wait_for_timeout(extra * 1000)
        results["files"] = _capture(page, base, formats)
        browser.close()
    return results
