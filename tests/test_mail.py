"""Tests for mail module (mocked Graph API)."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mail import send_mail


def test_send_mail_calls_graph(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 202
    mock_resp.text = ""
    with patch("mail.requests.post", return_value=mock_resp) as m:
        with patch("mail.msal.ConfidentialClientApplication") as msal_mock:
            msal_mock.return_value.acquire_token_for_client.return_value = {
                "access_token": "fake-token"
            }
            send_mail(
                sender="a@eneva.com.br",
                recipients=["b@eneva.com.br"],
                subject="Test",
                body_html="<p>hi</p>",
                attachments={},
                tenant_id="t", client_id="c", client_secret="s",
            )
            assert m.called
            call = m.call_args
            assert "sendMail" in call.args[0]
            assert call.kwargs["json"]["message"]["subject"] == "Test"


def test_send_mail_raises_on_error(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "bad request"
    with patch("mail.requests.post", return_value=mock_resp):
        with patch("mail.msal.ConfidentialClientApplication") as msal_mock:
            msal_mock.return_value.acquire_token_for_client.return_value = {
                "access_token": "fake-token"
            }
            try:
                send_mail("a@e.com", ["b@e.com"], "s", "b", {}, "t", "c", "s")
                assert False, "should raise"
            except RuntimeError:
                pass
