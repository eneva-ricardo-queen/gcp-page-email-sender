"""Configuração do job: lê tasks.yml e secrets do ambiente/gcloud."""

import os
import json
import subprocess
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


def _gcloud_secret(secret_id: str) -> str | None:
    try:
        out = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest",
             f"--secret={secret_id}", f"--project={PROJECT_ID}"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _secret_id_for(attr: str) -> str | None:
    try:
        cfg = yaml.safe_load(open(ROOT / "config.yml"))
        for sd in cfg.get("secrets", []):
            if sd.get("attr_name") == attr:
                return sd["secret_id"]
    except Exception:
        pass
    return None


def secret(name: str, attr: str | None = None) -> str:
    """Lê secret do env ou via gcloud CLI."""
    val = os.environ.get(name)
    if val:
        return val
    v = _gcloud_secret(name)
    if v:
        return v
    if attr:
        sid = _secret_id_for(attr)
        if sid:
            v = _gcloud_secret(sid)
            if v:
                return v
    sid = _secret_id_for(name.lower())
    if sid:
        v = _gcloud_secret(sid)
        if v:
            return v
    raise RuntimeError(f"Secret '{name}' not found in env nor gcloud")


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
}


def get_render_config(task: dict) -> dict:
    cfg = dict(DEFAULT_RENDER)
    cfg.update(task.get("render") or {})
    return cfg
