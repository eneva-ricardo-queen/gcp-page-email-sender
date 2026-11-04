"""Envio de e-mail via Microsoft Graph API (client credentials)."""

import base64
import os
from pathlib import Path

import msal
import requests


GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"


def _token(tenant_id: str, client_id: str, client_secret: str) -> str:
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=[GRAPH_SCOPE])
    if "access_token" not in result:
        raise RuntimeError(f"Graph auth failed: {result.get('error_description')}")
    return result["access_token"]


def send_mail(sender: str, recipients: list[str], subject: str,
              body_html: str, attachments: dict[str, str],
              tenant_id: str, client_id: str, client_secret: str) -> None:
    token = _token(tenant_id, client_id, client_secret)
    atts = []
    for name, path in attachments.items():
        data = Path(path).read_bytes()
        atts.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": Path(path).name,
            "contentType": "application/octet-stream",
            "contentBytes": base64.b64encode(data).decode("ascii"),
        })

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": r}} for r in recipients],
            "attachments": atts,
        },
        "saveToSentItems": True,
    }
    url = f"{GRAPH_ENDPOINT}/users/{sender}/sendMail"
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=120)
    if resp.status_code not in (200, 202):
        raise RuntimeError(f"sendMail failed: {resp.status_code} {resp.text}")
