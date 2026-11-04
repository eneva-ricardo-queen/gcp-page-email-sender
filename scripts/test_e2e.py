"""Teste E2E: renderiza a página e envia por e-mail (inline + anexo)."""

import sys
from pathlib import Path
import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, "/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-pep-dashboard")

from config import get_task, get_sender, get_recipients, get_url, get_body_formats, get_attachment_formats, get_render_config, secret
from render import render_page
import importlib.util
spec = importlib.util.spec_from_file_location("main_mod", "/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-page-email-sender/src/main.py")
main_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_mod)
_build_body = main_mod._build_body
_build_attachments = main_mod._build_attachments

task = get_task("rd-futura")
sender = get_sender(task)
recipients = get_recipients(task)
url = get_url(task)
render_config = get_render_config(task)

print(f"Rendering {url} ...")
result = render_page(url, task.get("formats", []), render_config=render_config)
files = result["files"]
print("Captured:", files)

date_str = datetime.date.today().strftime("%Y-%m-%d")
body_html = _build_body(task, date_str, files)
attachments = _build_attachments(task, files)

tenant_id = secret("prod_PORTFOLIO_TENANT_ID", attr="tenant_id")
client_id = secret("prod_PORTFOLIO_CLIENT_ID", attr="client_id")
client_secret = secret("prod_PORTFOLIO_CLIENT_SECRET", attr="client_secret")

import importlib.util
spec = importlib.util.spec_from_file_location("gac", "/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-pep-dashboard/src/volumes_realizados_gn_curtoprazo/sharepoint_connection/graph_api_connection.py")
gac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gac)

class Cfg:
    pass
cfg = Cfg()
cfg.tenant_id = tenant_id
cfg.client_id = client_id
cfg.client_secret = client_secret

mailing = gac.MailingClient(cfg, remetente=sender)
payload = {
    "message": {
        "subject": task.get("subject_template", "{id} — {date}").format(id=task["id"], date=date_str) + " (E2E)",
        "body": {"contentType": "HTML", "content": body_html},
        "toRecipients": [{"emailAddress": {"address": r}} for r in recipients],
        "attachments": [],
    },
    "saveToSentItems": True,
}

import base64
graph_atts = []
for att in attachments:
    data = Path(att["path"]).read_bytes()
    entry = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": att["name"],
        "contentType": "application/octet-stream",
        "contentBytes": base64.b64encode(data).decode("ascii"),
    }
    if att.get("inline"):
        entry["isInline"] = True
        entry["contentId"] = att["content_id"]
    graph_atts.append(entry)
payload["message"]["attachments"] = graph_atts

resp = mailing.send_email(payload)
print("sendMail status:", resp.status_code)
print("OK — e-mail enviado!")
