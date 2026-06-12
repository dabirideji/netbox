"""HTML and plain-text templates for target status alert emails."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

STATUS_META: dict[str, dict[str, str]] = {
    "operational": {
        "label": "Operational",
        "color": "#22c55e",
        "background": "#dcfce7",
    },
    "degraded": {
        "label": "Degraded",
        "color": "#ca8a04",
        "background": "#fef9c3",
    },
    "down": {
        "label": "Down",
        "color": "#ef4444",
        "background": "#fee2e2",
    },
    "unknown": {
        "label": "Unknown",
        "color": "#71717a",
        "background": "#f4f4f5",
    },
}


def status_meta(status: str) -> dict[str, str]:
    """Return display metadata for one monitor status."""

    return STATUS_META.get(status, STATUS_META["unknown"])


def format_alert_datetime(timestamp_ms: int | None) -> str:
    """Format one epoch-ms timestamp for alert emails."""

    if timestamp_ms is None:
        return "-"
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%b %d, %Y · %H:%M:%S")


def build_alert_email(event: dict[str, Any]) -> tuple[str, str, str]:
    """Build subject, plain-text body, and HTML body for one status alert."""

    label = str(event["targetLabel"])
    from_status = str(event["from"])
    to_status = str(event["to"])
    message = str(event.get("message") or "")
    observed_at = format_alert_datetime(event.get("at"))

    reminder = bool(event.get("reminder"))
    subject = (
        f"[Netbox] {label} still {to_status}"
        if reminder
        else f"[Netbox] {label} is {to_status}"
    )
    plain = build_alert_email_plain(
        label=label,
        from_status=from_status,
        to_status=to_status,
        message=message,
        observed_at=observed_at,
        reminder=reminder,
    )
    html_body = build_alert_email_html(
        label=label,
        from_status=from_status,
        to_status=to_status,
        message=message,
        observed_at=observed_at,
        reminder=reminder,
    )
    return subject, plain, html_body


def build_alert_email_plain(
    *,
    label: str,
    from_status: str,
    to_status: str,
    message: str,
    observed_at: str,
    reminder: bool = False,
) -> str:
    """Render the plain-text fallback body for one alert email."""

    from_label = status_meta(from_status)["label"]
    to_label = status_meta(to_status)["label"]
    headline = "Netbox ongoing alert" if reminder else "Netbox status alert"
    lines = [
        headline,
        "",
        f"Target: {label}",
        f"Previous status: {from_label} ({from_status})",
        f"Current status: {to_label} ({to_status})",
        f"Observed: {observed_at}",
        "",
        "Message:",
        message or "-",
        "",
        "-",
        "Sent by Netbox",
    ]
    return "\n".join(lines)


def build_alert_email_html(
    *,
    label: str,
    from_status: str,
    to_status: str,
    message: str,
    observed_at: str,
    reminder: bool = False,
) -> str:
    """Render the HTML body for one alert email."""

    headline = "Ongoing alert" if reminder else "Status alert"
    to_meta = status_meta(to_status)
    from_meta = status_meta(from_status)
    safe_label = html.escape(label)
    safe_message = html.escape(message or "-")
    safe_observed_at = html.escape(observed_at)
    safe_from = html.escape(from_meta["label"])
    safe_to = html.escape(to_meta["label"])
    safe_from_key = html.escape(from_status)
    safe_to_key = html.escape(to_status)

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(f"{label} is {to_status}")}</title>
  </head>
  <body style="margin:0;padding:0;background:#fafafa;color:#18181b;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fafafa;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid rgba(0,0,0,0.08);border-radius:8px;overflow:hidden;">
            <tr>
              <td style="padding:20px 24px 16px;border-bottom:1px solid rgba(0,0,0,0.05);">
                <p style="margin:0 0 4px;font-size:11px;line-height:1.4;letter-spacing:0.08em;text-transform:uppercase;color:#71717a;">Netbox</p>
                <h1 style="margin:0;font-size:20px;line-height:1.3;font-weight:600;color:#18181b;">{html.escape(headline)}</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 24px 8px;">
                <p style="margin:0 0 10px;font-size:13px;line-height:1.5;color:#71717a;">Target</p>
                <p style="margin:0 0 16px;font-size:18px;line-height:1.35;font-weight:600;color:#18181b;">{safe_label}</p>
                <span style="display:inline-block;padding:6px 12px;border-radius:8px;background:{to_meta['background']};color:{to_meta['color']};font-size:13px;font-weight:700;line-height:1;text-transform:capitalize;">{safe_to}</span>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 24px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
                  <tr>
                    <td style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.05);width:38%;font-size:12px;line-height:1.4;color:#71717a;vertical-align:top;">Previous</td>
                    <td style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.05);font-size:13px;line-height:1.45;color:#18181b;vertical-align:top;">
                      <span style="color:{from_meta['color']};font-weight:600;">{safe_from}</span>
                      <span style="color:#a1a1aa;"> ({safe_from_key})</span>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.05);font-size:12px;line-height:1.4;color:#71717a;vertical-align:top;">Current</td>
                    <td style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.05);font-size:13px;line-height:1.45;color:#18181b;vertical-align:top;">
                      <span style="color:{to_meta['color']};font-weight:600;">{safe_to}</span>
                      <span style="color:#a1a1aa;"> ({safe_to_key})</span>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.05);font-size:12px;line-height:1.4;color:#71717a;vertical-align:top;">Observed</td>
                    <td style="padding:10px 0;border-top:1px solid rgba(0,0,0,0.05);font-size:13px;line-height:1.45;color:#18181b;vertical-align:top;">{safe_observed_at}</td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:0 24px 24px;">
                <div style="padding:14px 16px;border-radius:8px;background:#f4f4f5;border:1px solid rgba(0,0,0,0.05);">
                  <p style="margin:0 0 6px;font-size:11px;line-height:1.4;letter-spacing:0.06em;text-transform:uppercase;color:#71717a;">Message</p>
                  <p style="margin:0;font-size:14px;line-height:1.55;color:#18181b;white-space:pre-wrap;">{safe_message}</p>
                </div>
              </td>
            </tr>
          </table>
          <p style="margin:16px 0 0;font-size:12px;line-height:1.5;color:#a1a1aa;">Sent by Netbox</p>
        </td>
      </tr>
    </table>
  </body>
</html>"""
