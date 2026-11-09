"""Renderização headless de uma página Streamlit via Playwright."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

from config import DEFAULT_RENDER


# Streamlit monta a pagina num scroller proprio (`stMain`) com a ALTURA do
# viewport: o documento nao cresce, entao `full_page=True` captura so a
# viewport e corta o que passa dela (11/2026: a tabela de comentarios + rodape
# da rd-futura passaram de 2000px e sumiram do e-mail). A altura real do
# conteudo e a do scroller.
ST_MAIN_SELECTOR = '[data-testid="stMain"]'
# Teto de dimensao (device px) de um screenshot unico do Chromium.
_MAX_SCREENSHOT_PX = 16384
_FIT_ATTEMPTS = 5


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


def _dismiss_dialogs(page, dialog_text: str):
    """Remove overlays/dialog do Streamlit cujo texto contenha `dialog_text`.

    Usado para fechar o pop-up 'Page not found' que o st.navigation (position
    hidden) às vezes exibe sobre a página já renderizada. Só age se dialog_text
    vier configurado; não remove dialogs legítimos cujo texto não bate.
    """
    if not dialog_text:
        return
    page.evaluate(_DISMISS_JS, dialog_text)


_DISMISS_JS = r"""
(text) => {
  const sels = ['[data-testid="stDialog"]', '[role="dialog"]'];
  for (const s of sels) {
    document.querySelectorAll(s).forEach((el) => {
      if (text && !(el.innerText || '').includes(text)) return;
      el.remove();
    });
  }
  document.querySelectorAll('[data-baseweb="modal"]').forEach((el) => el.remove());
}
"""


def _scroll_to_load(page, steps: int, step_px: int):
    """Percorre o scroller real da pagina e volta ao topo.

    Em pagina Streamlit a janela nao rola: o scroller e o `stMain` (medido em
    11/2026 — `window.scrollBy` era no-op na rd-futura). Quando o `stMain`
    existe, rola ele; nos demais alvos cai para o documento da janela.
    """
    for _ in range(steps):
        page.evaluate(
            """([sel, by]) => {
                const el = document.querySelector(sel) || document.scrollingElement;
                if (el) el.scrollTop += by;
            }""",
            [ST_MAIN_SELECTOR, step_px],
        )
        page.wait_for_timeout(300)
    page.wait_for_timeout(2000)
    page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel) || document.scrollingElement;
            if (el) el.scrollTop = 0;
        }""",
        ST_MAIN_SELECTOR,
    )
    page.wait_for_timeout(500)


def _content_height(page) -> int:
    """Altura real do conteudo: scrollHeight do scroller interno, senao do documento."""
    return page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            return el
                ? el.scrollHeight
                : Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
        }""",
        ST_MAIN_SELECTOR,
    )


def _fit_viewport_to_content(page, viewport: dict, device_scale_factor: int) -> dict:
    """Ajusta a ALTURA do viewport a do conteudo (largura e escala ficam iguais).

    Em vez de viewport fixa — que corta quando a pagina cresce e sobra branco
    quando encolhe — a altura vira a medida do scroller, entao `full_page`
    sai com o rodape incluso e sem espaco vazio. O loop estabiliza reflow
    pos-resize. Recusa (RuntimeError) em vez de capturar cortado se o conteudo
    nao couber num screenshot unico. Retorna a viewport final.
    """
    max_height = max(1, _MAX_SCREENSHOT_PX // max(1, device_scale_factor))
    width, height = viewport["width"], viewport["height"]
    for _ in range(_FIT_ATTEMPTS):
        needed = _content_height(page)
        if needed <= height:
            return {"width": width, "height": height}
        if needed > max_height:
            raise RuntimeError(
                f"conteudo com {needed}px excede {max_height}px (teto de screenshot "
                f"unico em {device_scale_factor}x): capture em partes antes de enviar"
            )
        height = needed
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(300)
    needed = _content_height(page)
    if needed > height:
        raise RuntimeError(
            f"viewport de {height}px nao acomodou o conteudo ({needed}px) apos "
            f"{_FIT_ATTEMPTS} ajustes: recusando captura cortada"
        )
    return {"width": width, "height": height}


def _assert_fits(page) -> None:
    """Falha alto se o scroller interno ainda tem overflow (conteudo fora da captura).

    Roda logo apos o fit e antes do screenshot: se o `stMain` ainda nao coube,
    o `full_page` sairia cortado — melhor o job falhar do que o e-mail chegar
    sem o fim da pagina. Sem `stMain` (pagina normal) nao ha overflow interno:
    o `full_page` captura o documento inteiro por definicao.
    """
    overflow = page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            if (!el) return 0;
            return el.scrollHeight - el.clientHeight;
        }""",
        ST_MAIN_SELECTOR,
    )
    if overflow > 1:  # tolerancia de subpixel
        raise RuntimeError(
            f"scroller interno da pagina com {overflow}px de overflow apos o fit: "
            "capturaria cortada; recusando"
        )


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
        # Fecha overlays 'Page not found' que o st.navigation pode exibir sobre a página
        _dismiss_dialogs(page, rc.get("dismiss_dialog_text", ""))
        # Validacao: checa se a pagina renderizou (nao e 404/fallback)
        html = page.content()
        validate_text = rc.get("validate_text", "")
        if validate_text and validate_text not in html:
            raise RuntimeError(f"Page did not render correctly (missing '{validate_text}'): {url}")
        _scroll_to_load(page, rc["scroll_steps"], rc["scroll_step_px"])
        page.wait_for_timeout(rc["extra_seconds"] * 1000)
        # Ajusta a ALTURA do viewport ao conteudo real (stMain): sem isso o
        # full_page corta no fim da viewport e some o rodape. Largura e escala
        # nao mudam (mesma composicao); so a altura acompanha a pagina.
        results["viewport"] = _fit_viewport_to_content(
            page, viewport, rc.get("device_scale_factor", 1)
        )
        _assert_fits(page)
        results["files"] = _capture(page, base, formats)
        browser.close()
    return results
