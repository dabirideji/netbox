"""SMTP delivery helpers for alert emails."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from netbox.alerts.email_template import build_alert_email


def send_alert_email(
    settings: dict[str, Any],
    *,
    password: str,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> None:
    """Send one alert email through the configured SMTP provider."""

    if not settings.get("configured"):
        raise ValueError("SMTP is not configured")
    if not password:
        raise ValueError("SMTP password is missing")
    if not to_email:
        raise ValueError("Recipient email is required")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings['fromName']} <{settings['fromEmail']}>"
    message["To"] = to_email
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    host = settings["host"]
    port = int(settings["port"])
    username = settings["username"]
    use_tls = bool(settings["useTls"])

    if use_tls and port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as client:
            if username:
                client.login(username, password)
            client.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=20) as client:
        if use_tls:
            client.starttls(context=ssl.create_default_context())
        if username:
            client.login(username, password)
        client.send_message(message)


__all__ = ["build_alert_email", "send_alert_email"]
