"""Configuração do job: lê tasks.yml e secrets do ambiente/Secret Manager."""

import os
import json
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def secret(name: str) -> str:
    """Lê secret do env (local) ou do Secret Manager (prod)."""
    val = os.environ.get(name)
    if val:
        return val
    # Fallback: tenta Secret Manager via gcp-lib (se disponível)
    try:
        from gcp_lib.secrets import get_secret  # type: ignore
        return get_secret(name)
    except Exception:
        raise RuntimeError(f"Secret '{name}' not found in env nor Secret Manager")


def parse_recipients(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("["):
        return json.loads(raw)
    return [x.strip() for x in raw.split(",") if x.strip()]
