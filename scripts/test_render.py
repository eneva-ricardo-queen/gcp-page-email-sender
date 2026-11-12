"""Teste local do render (Playwright). Requer chromium instalado."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print(f"Playwright not available: {e}")
    raise SystemExit(0)

from src.render import render_page

url = "https://www.google.com"  # troque pela URL da RDO quando acessível
print(f"Rendering {url} ...")
try:
    render_config = {"extra_seconds": 2}
    result = render_page(url, formats=["png"], render_config=render_config)
    print("Captured:", result["files"])
except Exception as e:
    print(f"Render failed: {e}")
    print("Chromium may not be installed. Run: playwright install chromium")
    print("Ou use a imagem Docker mcr.microsoft.com/playwright/python")
