"""Dispatch configured alerts when monitor status events occur."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from netbox.alerts.schedule import (
    AlertDispatchStore,
    channel_is_due,
    mark_channel_sent,
)
from netbox.alerts.smtp_client import build_alert_email, send_alert_email
from netbox.util.timeutils import now_ms


def should_alert_for_status(rules: dict[str, Any], status: str) -> bool:
    """Return whether one monitor status should trigger configured alerts."""

    if not rules.get("enabled"):
        return False
    if status == "degraded":
        return bool(rules.get("onDegraded"))
    if status == "down":
        return bool(rules.get("onDown"))
    return False


def should_trigger_alert(rules: dict[str, Any], to_status: str) -> bool:
    """Return whether one status transition should trigger configured alerts."""

    return should_alert_for_status(rules, to_status)


def reminder_event_from_target(target: dict[str, Any], observed_at: int) -> dict[str, Any]:
    """Build a synthetic status event for ongoing alert reminders."""

    status = str(target["currentStatus"])
    label = str(target["label"])
    return {
        "at": observed_at,
        "targetId": target["id"],
        "targetLabel": label,
        "from": status,
        "to": status,
        "message": f"{label} is still {status}",
        "reminder": True,
    }


def dispatch_target_alerts(
    events: list[dict[str, Any]],
    *,
    get_rules: Callable[[str], dict[str, Any]],
    smtp_settings: dict[str, Any] | None,
    smtp_password: str | None,
    dispatch_store: AlertDispatchStore,
    broadcast: Callable[[dict[str, Any]], None],
) -> None:
    """Evaluate new status transitions and emit alert notifications immediately."""

    if not events:
        return

    now = now_ms()
    for event in events:
        target_id = str(event["targetId"])
        if event["to"] == "operational":
            dispatch_store.clear_target(target_id)
            continue

        rules = get_rules(target_id)
        if not should_trigger_alert(rules, event["to"]):
            continue

        _dispatch_alert_channels(
            event,
            rules,
            now=now,
            smtp_settings=smtp_settings,
            smtp_password=smtp_password,
            dispatch_store=dispatch_store,
            broadcast=broadcast,
            enforce_interval=False,
        )


def dispatch_ongoing_alerts(
    summary: dict[str, Any],
    *,
    get_rules: Callable[[str], dict[str, Any]],
    smtp_settings: dict[str, Any] | None,
    smtp_password: str | None,
    dispatch_store: AlertDispatchStore,
    broadcast: Callable[[dict[str, Any]], None],
) -> None:
    """Re-send alerts while targets remain degraded or down."""

    now = now_ms()
    for target in summary.get("targets", []):
        target_id = str(target["id"])
        status = str(target["currentStatus"])
        if status == "operational":
            dispatch_store.clear_target(target_id)
            continue

        rules = get_rules(target_id)
        if not should_alert_for_status(rules, status):
            continue

        event = reminder_event_from_target(target, now)
        _dispatch_alert_channels(
            event,
            rules,
            now=now,
            smtp_settings=smtp_settings,
            smtp_password=smtp_password,
            dispatch_store=dispatch_store,
            broadcast=broadcast,
            enforce_interval=True,
        )


def _dispatch_alert_channels(
    event: dict[str, Any],
    rules: dict[str, Any],
    *,
    now: int,
    smtp_settings: dict[str, Any] | None,
    smtp_password: str | None,
    dispatch_store: AlertDispatchStore,
    broadcast: Callable[[dict[str, Any]], None],
    enforce_interval: bool,
) -> None:
    target_id = str(event["targetId"])
    channels: list[tuple[str, bool]] = [
        ("notification", bool(rules.get("notification"))),
        ("sound", bool(rules.get("sound"))),
        ("email", bool(rules.get("email"))),
    ]

    for channel, enabled in channels:
        if not enabled:
            continue
        if not channel_is_due(
            dispatch_store,
            target_id,
            channel,
            now,
            enforce_interval=enforce_interval,
        ):
            continue

        if channel == "email":
            if not smtp_settings or not smtp_settings.get("configured") or not smtp_password:
                continue
            recipient = str(rules.get("emailTo") or "").strip()
            if not recipient:
                continue
            subject, body, html_body = build_alert_email(event)
            threading.Thread(
                target=_send_email_safe,
                args=(smtp_settings, smtp_password, recipient, subject, body, html_body),
                daemon=True,
            ).start()
            mark_channel_sent(dispatch_store, target_id, channel, now=now, rules=rules)
            continue

        broadcast(
            {
                "type": "alert",
                "alert": {
                    "targetId": event["targetId"],
                    "targetLabel": event["targetLabel"],
                    "from": event["from"],
                    "to": event["to"],
                    "message": event["message"],
                    "channel": channel,
                    "at": event["at"],
                    "reminder": bool(event.get("reminder")),
                },
            }
        )
        mark_channel_sent(dispatch_store, target_id, channel, now=now, rules=rules)


def _send_email_safe(
    settings: dict[str, Any],
    password: str,
    recipient: str,
    subject: str,
    body: str,
    html_body: str,
) -> None:
    try:
        send_alert_email(
            settings,
            password=password,
            to_email=recipient,
            subject=subject,
            body=body,
            html_body=html_body,
        )
    except Exception:
        return
