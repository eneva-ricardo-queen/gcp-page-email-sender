"""Tests for tasks.yml configuration."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import (load_tasks, get_task, get_sender, get_recipients,
                    get_body_formats, get_attachment_formats, get_render_config,
                    DEFAULT_RENDER)

REQUIRED_FIELDS = {"id", "url", "schedule", "sender", "recipients", "formats"}


def test_tasks_loads():
    data = load_tasks()
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
    assert len(data["tasks"]) >= 1


def test_each_task_has_required_fields():
    for t in load_tasks()["tasks"]:
        missing = REQUIRED_FIELDS - set(t.keys())
        assert not missing, f"task {t.get('id')} missing {missing}"


def test_task_ids_unique():
    ids = [t["id"] for t in load_tasks()["tasks"]]
    assert len(ids) == len(set(ids))


def test_get_task():
    t = get_task("rdo-futura")
    assert t["id"] == "rdo-futura"
    assert t["url"].startswith("https://")


def test_get_sender_recipients():
    t = get_task("rdo-futura")
    assert "@" in get_sender(t)
    assert all("@" in r for r in get_recipients(t))


def test_body_and_attachment_formats():
    t = get_task("rdo-futura")
    assert "png" in get_body_formats(t)
    assert "pdf" in get_attachment_formats(t)


def test_get_render_config():
    t = get_task("rdo-futura")
    rc = get_render_config(t)
    assert rc["viewport_height"] == 2000
    assert rc["wait_end_timeout"] == 30000
    # defaults applied
    assert rc["scroll_steps"] == 10


def test_get_render_config_defaults():
    t = {"id": "x", "url": "https://example.com"}
    rc = get_render_config(t)
    assert rc == DEFAULT_RENDER


def test_get_task_missing_raises():
    try:
        get_task("nonexistent")
        assert False, "should raise"
    except ValueError:
        pass
