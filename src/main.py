"""Entry point do job: renderiza a página da tarefa e envia por e-mail."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import get_task, secret, parse_recipients
from src.render import render_page
from src.mail import send_mail


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="ID da tarefa em tasks.yml")
    args = parser.parse_args()

    task = get_task(args.task)
    url = task["url"]
    formats = task.get("formats", ["png"])
    wait_selector = task.get("wait_selector", "")
    extra = task.get("wait_extra_seconds", 3)
    subject_tpl = task.get("subject_template", "{id} — {date}")
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"[{task['id']}] rendering {url}")
    result = render_page(url, wait_selector, extra, formats)
    print(f"[{task['id']}] captured: {result['files']}")

    sender = secret(task["sender_secret"])
    recipients = parse_recipients(secret(task["recipients_secret"]))
    subject = subject_tpl.format(id=task["id"], date=date_str)
    body = f"<p>Segue em anexo a página <b>{task['id']}</b> referente a {date_str}.</p>"

    tenant_id = secret("prod_GRAPH_TENANT_ID")
    client_id = secret("prod_GRAPH_CLIENT_ID")
    client_secret = secret("prod_GRAPH_CLIENT_SECRET")

    send_mail(sender, recipients, subject, body, result["files"],
              tenant_id, client_id, client_secret)
    print(f"[{task['id']}] e-mail enviado para {recipients}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
