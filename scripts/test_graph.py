"""Teste local da autenticação Graph e envio de e-mail (sem anexo)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-pep-dashboard")
sys.path.insert(0, "/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-pep-dashboard")

from src.config import secret

# Reusa o padrão do projeto (GraphAuth)
import importlib.util
spec = importlib.util.spec_from_file_location("gac", "/home/ricardoqueen/repos/Eneva-Preco-Gas-GNL/gcp-pep-dashboard/src/volumes_realizados_gn_curtoprazo/sharepoint_connection/graph_api_connection.py")
gac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gac)

tenant_id = secret("prod_PORTFOLIO_TENANT_ID", attr="tenant_id")
client_id = secret("prod_PORTFOLIO_CLIENT_ID", attr="client_id")
client_secret = secret("prod_PORTFOLIO_CLIENT_SECRET", attr="client_secret")
sender = secret("prod_RDO_SENDER", attr="rdo_sender")
recipients_raw = secret("prod_RDO_RECIPIENTS", attr="rdo_recipients")

print("tenant_id:", tenant_id[:8] + "...")
print("client_id:", client_id[:8] + "...")
print("sender:", sender)
print("recipients raw:", recipients_raw)

# Config fake com os atributos necessários
class Cfg:
    pass
cfg = Cfg()
cfg.tenant_id = tenant_id
cfg.client_id = client_id
cfg.client_secret = client_secret
cfg.sharepoint_site_id = secret("prod_PORTFOLIO_SHAREPOINT_SITE_ID", attr="sharepoint_site_id")

# Testa auth
auth = gac.GraphAuth(cfg)
token = auth.get_access_token()
print("Token obtido:", token[:20] + "...")

# Testa envio
import datetime
from src.config import parse_recipients
recipients = parse_recipients(recipients_raw)
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
