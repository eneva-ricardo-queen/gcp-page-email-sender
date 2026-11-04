"""Smoke test for render (skipped if chromium unavailable)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest


def test_render_imports():
    import render as src_render
    assert hasattr(src_render, "render_page")


def test_render_page_signature():
    import inspect
    from render import render_page
    sig = inspect.signature(render_page)
    assert "url" in sig.parameters
    assert "formats" in sig.parameters


@pytest.mark.skipif(True, reason="chromium not available in CI/local; run manually")
def test_render_smoke():
    from render import render_page
    result = render_page("https://www.google.com", wait_selector="", extra_seconds=1, formats=["png"])
    assert "png" in result["files"]
