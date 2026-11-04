"""Configuração do job: lê tasks.yml e secrets via gcp-lib (SecretManager)."""

import os
import json
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "eva-prj-prd-preco-gas-gnl-s9"


def load_tasks() -> dict:
    path = ROOT / "tasks.yml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_task(task_id: str) -> dict:
    tasks = load_tasks()["tasks"]
    for t in tasks:
        if t["id"] == task_id:
            return t
    raise ValueError(f"Task '{task_id}' not found in tasks.yml")


def get_url(task: dict) -> str:
    """URL da página: override via env APP_URL (deploy) ou default do tasks.yml (local)."""
    return os.environ.get("APP_URL", task.get("url", ""))


# SecretManager instance (lazy, reutilizado)
_sm = None


def _get_sm():
    global _sm
    if _sm is not None:
        return _sm
    try:
        from gcp.secret_manager import SecretManager
        _sm = SecretManager(project_id=PROJECT_ID, config_file_path=str(ROOT / "config.yml"))
        _sm.load_secrets()
    except Exception as e:
        print(f"[config] SecretManager failed: {e}")
        _sm = None
    return _sm


def secret(name: str, attr: str | None = None) -> str:
    """Lê secret do env (local) ou via gcp-lib SecretManager (prod)."""
    # 1. env (local)
    val = os.environ.get(name)
    if val:
        return val
    # 2. gcp-lib SecretManager
    sm = _get_sm()
    if sm is not None:
        key = attr or name.lower()
        v = getattr(sm, key, None)
        if v:
            return v
    raise RuntimeError(f"Secret '{name}' not found in env nor SecretManager")


def get_sender(task: dict) -> str:
    return task.get("sender") or (_ for _ in ()).throw(ValueError("task missing 'sender'"))


def get_recipients(task: dict) -> list[str]:
    r = task.get("recipients")
    if isinstance(r, list):
        return [str(x).strip() for x in r if str(x).strip()]
    if isinstance(r, str):
        return [x.strip() for x in r.split(",") if x.strip()]
    raise ValueError("task missing 'recipients'")


def get_body_formats(task: dict) -> list[str]:
    return task.get("body_formats", [])


def get_attachment_formats(task: dict) -> list[str]:
    return task.get("attachment_formats", [])


def get_body_text_before(task: dict) -> str:
    return task.get("body_text_before", "Segue a página {id} referente a {date}.")


def get_body_text_after(task: dict) -> str:
    return task.get("body_text_after", "")


DEFAULT_RENDER = {
    "wait_selector": "",
    "wait_end_selector": "",
    "wait_end_timeout": 15000,
    "extra_seconds": 3,
    "viewport_width": 1920,
    "viewport_height": 4000,
    "scroll_steps": 10,
    "scroll_step_px": 500,
    "device_scale_factor": 1,
    "wait_for_chart": False,
    "chart_timeout": 30000,
    "dismiss_dialog_text": "",
}


def get_render_config(task: dict) -> dict:
    cfg = dict(DEFAULT_RENDER)
    cfg.update(task.get("render") or {})
    return cfg
