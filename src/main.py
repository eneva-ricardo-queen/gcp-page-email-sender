"""Entry point do job: renderiza a página da tarefa e envia por e-mail."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (get_task, get_sender, get_recipients, secret, get_url,
                    get_body_formats, get_attachment_formats,
                    get_body_text_before, get_body_text_after,
                    get_render_config)
from render import render_page
from mail import send_mail


def _build_body(task: dict, date_str: str, files: dict) -> str:
    before = get_body_text_before(task).format(id=task["id"], date=date_str)
    after = get_body_text_after(task).format(id=task["id"], date=date_str)
    body_formats = get_body_formats(task)

    parts = [f"<p>{before}</p>"]
    for fmt in body_formats:
        if fmt not in files:
            continue
        path = files[fmt]
        if fmt == "png":
            parts.append(f'<p><img src="cid:inline_{fmt}" style="max-width:100%;height:auto;" alt="screenshot" /></p>')
        elif fmt == "html":
            html_content = Path(path).read_text(encoding="utf-8")
            if len(html_content) > 100000:
                html_content = html_content[:100000] + "\n<!-- truncado -->"
            parts.append(f'<details><summary>HTML completo da página</summary><pre style="white-space:pre-wrap;font-size:12px;">{html_content}</pre></details>')
    if after:
        parts.append(f"<p>{after}</p>")
    return "\n".join(parts)


def _build_attachments(task: dict, files: dict) -> list[dict]:
    body_formats = get_body_formats(task)
    attachment_formats = get_attachment_formats(task)
    attachments = []
    seen = set()
    for fmt in body_formats:
        if fmt in files and files[fmt] not in seen:
            attachments.append({"path": files[fmt], "inline": True, "content_id": f"inline_{fmt}", "name": Path(files[fmt]).name})
            seen.add(files[fmt])
    for fmt in attachment_formats:
        if fmt in files and files[fmt] not in seen:
            attachments.append({"path": files[fmt], "inline": False, "name": Path(files[fmt]).name})
            seen.add(files[fmt])
    return attachments


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="ID da tarefa em tasks.yml")
    args = parser.parse_args()

    task = get_task(args.task)
    url = get_url(task)
    formats = task.get("formats", ["png"])
    render_config = get_render_config(task)
    subject_tpl = task.get("subject_template", "{id} — {date}")
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"[{task['id']}] rendering {url}")
    result = render_page(url, formats, render_config=render_config)
    files = result["files"]
    print(f"[{task['id']}] captured: {files}")

    body_html = _build_body(task, date_str, files)
    attachments = _build_attachments(task, files)

    sender = get_sender(task)
    recipients = get_recipients(task)
    subject = subject_tpl.format(id=task["id"], date=date_str)

    tenant_id = secret("prod_PORTFOLIO_TENANT_ID", attr="tenant_id")
    client_id = secret("prod_PORTFOLIO_CLIENT_ID", attr="client_id")
    client_secret = secret("prod_PORTFOLIO_CLIENT_SECRET", attr="client_secret")

    send_mail(sender, recipients, subject, body_html, attachments,
              tenant_id, client_id, client_secret)
    print(f"[{task['id']}] e-mail enviado para {recipients}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
