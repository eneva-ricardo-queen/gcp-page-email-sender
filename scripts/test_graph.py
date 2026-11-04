"""Teste local da autenticação Graph e envio de e-mail (sem anexo)."""

import sys
from pathlib import Path
import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-pep-dashboard")

from config import get_task, get_sender, get_recipients, secret

task = get_task("rdo-futura")
sender = get_sender(task)
recipients = get_recipients(task)

tenant_id = secret("prod_PORTFOLIO_TENANT_ID", attr="tenant_id")
client_id = secret("prod_PORTFOLIO_CLIENT_ID", attr="client_id")
client_secret = secret("prod_PORTFOLIO_CLIENT_SECRET", attr="client_secret")

print("sender:", sender)
print("recipients:", recipients)

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

auth = gac.GraphAuth(cfg)
token = auth.get_access_token()
print("Token OK:", token[:20] + "...")

mailing = gac.MailingClient(cfg, remetente=sender)
payload = {
    "message": {
        "subject": f"Teste page-email-sender — {datetime.date.today()}",
        "body": {"contentType": "HTML", "content": "<p>Teste de envio do job page-email-sender.</p>"},
        "toRecipients": [{"emailAddress": {"address": r}} for r in recipients],
        "attachments": [],
    },
    "saveToSentItems": True,
}
resp = mailing.send_email(payload)
print("sendMail status:", resp.status_code)
print("OK")
