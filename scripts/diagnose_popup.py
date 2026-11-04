"""Diagnóstico: identifica o pop-up 'Page not found' no DOM do Streamlit."""
import sys
from playwright.sync_api import sync_playwright

URL = "https://pep.labs.eneva.com.br/rd-futura"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 2000})
    page.goto(URL, wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(15000)

    # 1) Onde aparece 'Page not found' e o data-testid dos ancestrais
    info = page.evaluate(r"""
    () => {
      const out = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const t = walker.currentNode.textContent.trim();
        if (t.includes('Page not found') || t.includes('not found')) {
          let el = walker.currentNode.parentElement;
          const chain = [];
          while (el && chain.length < 8) {
            const dts = [...el.attributes || []]
              .filter(a => a.name.startsWith('data-testid'))
              .map(a => `${a.name}=${a.value}`);
            chain.push({tag: el.tagName, cls: el.className, testids: dts});
            el = el.parentElement;
          }
          out.push({text: t.slice(0,60), chain});
        }
      }
      return out;
    }
    """)
    print("=== 'Page not found' nodes ===")
    for node in info:
        print(node["text"])
        for c in node["chain"]:
            print(f"   {c['tag']} {c['testids']} cls={c['cls'][:60]!r}")
        print("---")

    # 2) Listar todos os overlays/dialogs/toasts presentes
    overlays = page.evaluate(r"""
    () => {
      const sel = ['[data-testid="stDialog"]','[data-testid="stBottomSheet"]',
                   '[data-testid="stBottomSheetContainer"]','[data-testid="stToast"]',
                   '[data-testid="stOverlay"]','[role="dialog"]'];
      const found = {};
      for (const s of sel) {
        const n = document.querySelectorAll(s);
        if (n.length) found[s] = [...n].map(e => ({
          text: (e.innerText||'').replace(/\s+/g,' ').slice(0,80),
          visible: !!(e.offsetWidth||e.offsetHeight)
        }));
      }
      return found;
    }
    """)
    print("=== overlays/dialogs/toasts ===")
    for k, v in overlays.items():
        print(k, v)

    browser.close()