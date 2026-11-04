"""Teste E2E: renderiza a página e envia por e-mail (inline + anexo)."""

import sys
from pathlib import Path
import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, "/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-pep-dashboard")

from config import get_task, get_sender, get_recipients, get_body_formats, get_attachment_formats, secret
from render import render_page

task = get_task("rdo-futura")
sender = get_sender(task)
recipients = get_recipients(task)
body_formats = get_body_formats(task)
attachment_formats = get_attachment_formats(task)
url = task["url"]

print(f"Rendering {url} ...")
result = render_page(url, task["wait_selector"], task["wait_extra_seconds"], task.get("formats", []))
files = result["files"]
print("Captured:", files)

# Monta attachments (inline + normal)
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

# Corpo do e-mail
body_parts = [f"<p>Segue a página <b>{task['id']}</b> referente a {datetime.date.today()}.</p>"]
for fmt in body_formats:
    if fmt == "png" and fmt in files:
        body_parts.append(f'<p><img src="cid:inline_{fmt}" style="max-width:100%;height:auto;" alt="screenshot" /></p>')
    elif fmt == "html" and fmt in files:
        body_parts.append(f'<p>HTML completo disponível no anexo.</p>')
body_html = "\n".join(body_parts)

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

mailing = gac.MailingClient(cfg, remetente=get_sender(task))
payload = {
    "message": {
        "subject": f"{task['subject_template'].format(id=task['id'], date=datetime.date.today())} (E2E)",
        "body": {"contentType": "HTML", "content": body_html},
        "toRecipients": [{"emailAddress": {"address": r}} for r in recipients],
        "attachments": [],
    },
    "saveToSentItems": True,
}

# Monta attachments no formato Graph
graph_atts = []
for att in attachments:
    data = Path(att["path"]).read_bytes()
    import base64
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
print("OK — e-mail enviado com inline + anexo!")
