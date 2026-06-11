from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

from netbox.alerts.email_template import build_alert_email, build_alert_email_html
from netbox.alerts.smtp_client import send_alert_email


def sample_event(**overrides: object) -> dict[str, object]:
    payload = {
        "at": 1_700_000_000_000,
        "targetId": "api-1",
        "targetLabel": "Example API",
        "from": "operational",
        "to": "down",
        "message": "Example API changed from operational to down",
    }
    payload.update(overrides)
    return payload


def test_build_alert_email_uses_reminder_subject_for_ongoing_alerts() -> None:
    subject, plain, html_body = build_alert_email(sample_event(reminder=True))

    assert subject == "[Netbox] Example API still down"
    assert "Netbox ongoing alert" in plain
    assert "Ongoing alert" in html_body


def test_build_alert_email_returns_subject_plain_and_html() -> None:
    subject, plain, html_body = build_alert_email(sample_event())

    assert subject == "[Netbox] Example API is down"
    assert "Netbox status alert" in plain
    assert "Example API" in plain
    assert "Previous status: Operational (operational)" in plain
    assert "Current status: Down (down)" in plain
    assert "Example API changed from operational to down" in plain

    assert "<!DOCTYPE html>" in html_body
    assert "Status alert" in html_body
    assert "Example API" in html_body
    assert "Down" in html_body
    assert "#ef4444" in html_body
    assert "Observed" in html_body
    assert "Sent by Netbox" in html_body


def test_build_alert_email_html_escapes_unsafe_content() -> None:
    html_body = build_alert_email_html(
        label='<script>alert("x")</script>',
        from_status="operational",
        to_status="degraded",
        message='He said "check <b>logs</b>"',
        observed_at="Jun 10, 2026 · 12:00:00",
    )

    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
    assert "He said &quot;check &lt;b&gt;logs&lt;/b&gt;&quot;" in html_body


def test_send_alert_email_attaches_html_alternative() -> None:
    settings = {
        "configured": True,
        "host": "smtp.example.com",
        "port": 587,
        "username": "alerts",
        "fromEmail": "alerts@example.com",
        "fromName": "Netbox",
        "useTls": True,
    }
    sent: list[EmailMessage] = []

    class FakeSMTP:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeSMTP:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def starttls(self, *_args: object, **_kwargs: object) -> None:
            return None

        def login(self, *_args: object, **_kwargs: object) -> None:
            return None

        def send_message(self, message: EmailMessage) -> None:
            sent.append(message)

    with patch("netbox.alerts.smtp_client.smtplib.SMTP", FakeSMTP):
        send_alert_email(
            settings,
            password="secret",
            to_email="ops@example.com",
            subject="[Netbox] API is down",
            body="plain fallback",
            html_body="<p>html body</p>",
        )

    assert len(sent) == 1
    message = sent[0]
    parts = list(message.walk())
    plain_part = next(part for part in parts if part.get_content_type() == "text/plain")
    html_part = next(part for part in parts if part.get_content_type() == "text/html")
    assert plain_part.get_content().strip() == "plain fallback"
    assert html_part.get_content().strip() == "<p>html body</p>"


def test_send_alert_email_uses_ssl_transport_on_port_465() -> None:
    settings = {
        "configured": True,
        "host": "smtp.example.com",
        "port": 465,
        "username": "alerts",
        "fromEmail": "alerts@example.com",
        "fromName": "Netbox",
        "useTls": True,
    }
    ssl_client = MagicMock()
    ssl_client.__enter__.return_value = ssl_client

    with patch("netbox.alerts.smtp_client.smtplib.SMTP_SSL", return_value=ssl_client) as smtp_ssl:
        send_alert_email(
            settings,
            password="secret",
            to_email="ops@example.com",
            subject="[Netbox] API is down",
            body="plain fallback",
            html_body="<p>html body</p>",
        )

    smtp_ssl.assert_called_once()
