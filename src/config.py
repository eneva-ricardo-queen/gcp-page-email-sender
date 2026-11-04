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
            ["gcloud", "secrets", "versions", "access", "latest", f"--secret={secret_id}", f"--project={PROJECT_ID}"],
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
    """Lê secret do env ou via gcloud CLI (usando config.yml para mapear attr->secret_id)."""
    # 1. env
    val = os.environ.get(name)
    if val:
        return val
    # 2. gcloud CLI direto (name como secret_id)
    v = _gcloud_secret(name)
    if v:
        return v
    # 3. mapear attr -> secret_id
    if attr:
        sid = _secret_id_for(attr)
        if sid:
            v = _gcloud_secret(sid)
            if v:
                return v
    # 4. mapear name.lower() -> secret_id
    sid = _secret_id_for(name.lower())
    if sid:
        v = _gcloud_secret(sid)
        if v:
            return v
    raise RuntimeError(f"Secret '{name}' not found in env nor gcloud")


def parse_recipients(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("["):
        return json.loads(raw)
    return [x.strip() for x in raw.split(",") if x.strip()]
