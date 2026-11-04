"""Renderização headless de uma página Streamlit via Playwright."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def render_page(url: str, wait_selector: str = "", extra_seconds: int = 3,
                formats: list[str] | None = None,
                render_config: dict | None = None) -> dict:
    formats = formats or ["png"]
    rc = render_config or {}
    viewport_w = rc.get("viewport_width", 1920)
    viewport_h = rc.get("viewport_height", 4000)
    wait_end_selector = rc.get("wait_end_selector", "")
    wait_end_timeout = rc.get("wait_end_timeout", 15000)
    scroll_steps = rc.get("scroll_steps", 10)
    scroll_step_px = rc.get("scroll_step_px", 500)
    extra = rc.get("extra_seconds", extra_seconds)

    out_dir = Path(os.environ.get("OUTPUT_DIR", "/tmp"))
    out_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = url.rstrip("/").split("/")[-1] or "page"
    base = out_dir / f"{safe}_{stamp}"

    results = {"url": url, "files": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": viewport_w, "height": viewport_h})
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=120000)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=60000)

        # Espera por seletor de fim (opcional, timeout curto)
        if wait_end_selector:
            try:
                page.wait_for_selector(wait_end_selector, timeout=wait_end_timeout)
            except Exception:
                pass  # continua mesmo se não aparecer

        # Scroll incremental para disparar lazy loading
        for _ in range(scroll_steps):
            page.evaluate(f"window.scrollBy(0, {scroll_step_px})")
            page.wait_for_timeout(300)
        page.wait_for_timeout(2000)

        # Voltar ao topo
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # Espera extra configurável
        page.wait_for_timeout(extra * 1000)

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
