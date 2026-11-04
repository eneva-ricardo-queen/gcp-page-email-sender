"""Renderização headless de uma página Streamlit via Playwright."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

from config import DEFAULT_RENDER


def _setup_page(browser, viewport: dict, device_scale_factor: int = 1):
    context = browser.new_context(viewport=viewport, device_scale_factor=device_scale_factor)
    return context.new_page()


def _wait_for_content(page, wait_selector: str, wait_end_selector: str, wait_end_timeout: int,
                      wait_for_chart: bool = False, chart_timeout: int = 30000):
    if wait_selector:
        page.wait_for_selector(wait_selector, timeout=60000)
    if wait_end_selector:
        try:
            page.wait_for_selector(wait_end_selector, timeout=wait_end_timeout)
        except Exception:
            pass
    if wait_for_chart:
        try:
            page.wait_for_selector("canvas, .plotly-graph-div, svg.js-plotly-plot", timeout=chart_timeout)
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
        png_path = files.get("png")
        if not png_path:
            png_path = f"{base}.png"
            page.screenshot(path=png_path, full_page=True)
            files["png"] = png_path
        try:
            from PIL import Image
            img = Image.open(png_path)
            img.save(f"{base}.pdf", "PDF", resolution=100.0)
            files["pdf"] = f"{base}.pdf"
        except Exception:
            page.pdf(path=f"{base}.pdf", format="A4", print_background=True)
            files["pdf"] = f"{base}.pdf"
    if "html" in formats:
        Path(f"{base}.html").write_text(page.content(), encoding="utf-8")
        files["html"] = f"{base}.html"
    return files


def render_page(url: str, formats: list[str] | None = None,
                render_config: dict | None = None) -> dict:
    formats = formats or ["png"]
    rc = {**DEFAULT_RENDER, **(render_config or {})}
    viewport = {"width": rc["viewport_width"], "height": rc["viewport_height"]}

    out_dir = Path(os.environ.get("OUTPUT_DIR", "/tmp"))
    out_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = url.rstrip("/").split("/")[-1] or "page"
    base = out_dir / f"{safe}_{stamp}"

    results = {"url": url, "files": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = _setup_page(browser, viewport, device_scale_factor=rc.get("device_scale_factor", 1))
        page.goto(url, wait_until="networkidle", timeout=120000)
        _wait_for_content(page, rc["wait_selector"], rc["wait_end_selector"], rc["wait_end_timeout"],
                          rc.get("wait_for_chart", False), rc.get("chart_timeout", 30000))
        # Validacao: checa se a pagina renderizou (nao e 404/fallback)
        html = page.content()
        validate_text = rc.get("validate_text", "")
        if validate_text and validate_text not in html:
            raise RuntimeError(f"Page did not render correctly (missing '{validate_text}'): {url}")
        _scroll_to_load(page, rc["scroll_steps"], rc["scroll_step_px"])
        page.wait_for_timeout(rc["extra_seconds"] * 1000)
        results["files"] = _capture(page, base, formats)
        browser.close()
    return results
