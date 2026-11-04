"""Entry point do job: renderiza a página da tarefa e envia por e-mail."""

import argparse
import base64
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (get_task, get_sender, get_recipients,
                    get_body_formats, get_attachment_formats,
                    get_render_config)
from render import render_page
from mail import send_mail


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="ID da tarefa em tasks.yml")
    args = parser.parse_args()

    task = get_task(args.task)
    url = task["url"]
    formats = task.get("formats", ["png"])
    render_config = get_render_config(task)
    wait_selector = render_config.get("wait_selector", "")
    extra = render_config.get("extra_seconds", 3)
    subject_tpl = task.get("subject_template", "{id} — {date}")
    date_str = datetime.now().strftime("%Y-%m-%d")
    body_formats = get_body_formats(task)
    attachment_formats = get_attachment_formats(task)

    print(f"[{task['id']}] rendering {url}")
    result = render_page(url, wait_selector, extra, formats, render_config=render_config)
    files = result["files"]
    print(f"[{task['id']}] captured: {files}")

    sender = get_sender(task)
    recipients = get_recipients(task)
    subject = subject_tpl.format(id=task["id"], date=date_str)

    # Monta o corpo do e-mail
    body_parts = [f"<p>Segue a página <b>{task['id']}</b> referente a {date_str}.</p>"]
    attachments = []

    # Inline (cid) para body_formats
    for fmt in body_formats:
        if fmt not in files:
            continue
        path = files[fmt]
        cid = f"inline_{fmt}"
        if fmt == "png":
            body_parts.append(f'<p><img src="cid:{cid}" style="max-width:100%;height:auto;" alt="screenshot" /></p>')
        elif fmt == "html":
            # Embute o HTML completo da página no corpo (truncado a 100k para não exceder limite)
            html_content = Path(path).read_text(encoding="utf-8")
            if len(html_content) > 100000:
                html_content = html_content[:100000] + "\n<!-- truncado -->"
            body_parts.append(f'<details><summary>HTML completo da página</summary><pre style="white-space:pre-wrap;font-size:12px;">{html_content}</pre></details>')
        attachments.append({"path": path, "inline": True, "content_id": cid, "name": Path(path).name})

    # Anexos normais para attachment_formats
    for fmt in attachment_formats:
        if fmt not in files:
            continue
        path = files[fmt]
        attachments.append({"path": path, "inline": False, "name": Path(path).name})

    # Se um formato está em ambos (body + attachment), evita duplicar anexo
    # (já adicionado acima como inline; não re-adiciona)
    seen_paths = set()
    unique_attachments = []
    for att in attachments:
        if att["path"] in seen_paths:
            continue
        seen_paths.add(att["path"])
        unique_attachments.append(att)
    attachments = unique_attachments

    body_html = "\n".join(body_parts)

    tenant_id = secret("prod_PORTFOLIO_TENANT_ID", attr="tenant_id")
    client_id = secret("prod_PORTFOLIO_CLIENT_ID", attr="client_id")
    client_secret = secret("prod_PORTFOLIO_CLIENT_SECRET", attr="client_secret")

    send_mail(sender, recipients, subject, body_html, attachments,
              tenant_id, client_id, client_secret)
    print(f"[{task['id']}] e-mail enviado para {recipients}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
