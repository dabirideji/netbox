"""Platform-wide alert defaults and settings normalization."""

from __future__ import annotations

from typing import Any

from netbox.alerts.models import DEFAULT_TARGET_ALERT, _bool, _int

DEFAULT_PLATFORM_SETTINGS: dict[str, Any] = {
    "alerts": {
        "defaultNotification": DEFAULT_TARGET_ALERT["notification"],
        "defaultSound": DEFAULT_TARGET_ALERT["sound"],
        "defaultEmail": DEFAULT_TARGET_ALERT["email"],
        "defaultEmailTo": DEFAULT_TARGET_ALERT["emailTo"],
        "defaultOnDegraded": DEFAULT_TARGET_ALERT["onDegraded"],
        "defaultOnDown": DEFAULT_TARGET_ALERT["onDown"],
        "defaultCooldownMs": DEFAULT_TARGET_ALERT["cooldownMs"],
    }
}


def normalize_platform_settings_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and normalize platform settings updates."""

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("platform settings payload must be a JSON object")

    alerts_payload = payload.get("alerts")
    if alerts_payload is None:
        return dict(DEFAULT_PLATFORM_SETTINGS)
    if not isinstance(alerts_payload, dict):
        raise ValueError("alerts must be a JSON object")

    defaults = DEFAULT_PLATFORM_SETTINGS["alerts"]
    default_email = _bool(alerts_payload.get("defaultEmail"), defaults["defaultEmail"])
    default_email_to = str(alerts_payload.get("defaultEmailTo") or "").strip()
    if default_email and not default_email_to:
        raise ValueError("defaultEmailTo is required when default email alerts are enabled")

    return {
        "alerts": {
            "defaultNotification": _bool(
                alerts_payload.get("defaultNotification"),
                defaults["defaultNotification"],
            ),
            "defaultSound": _bool(alerts_payload.get("defaultSound"), defaults["defaultSound"]),
            "defaultEmail": default_email,
            "defaultEmailTo": default_email_to,
            "defaultOnDegraded": _bool(
                alerts_payload.get("defaultOnDegraded"),
                defaults["defaultOnDegraded"],
            ),
            "defaultOnDown": _bool(alerts_payload.get("defaultOnDown"), defaults["defaultOnDown"]),
            "defaultCooldownMs": _int(
                alerts_payload.get("defaultCooldownMs"),
                defaults["defaultCooldownMs"],
                minimum=30_000,
                maximum=3_600_000,
            ),
        }
    }


def merge_platform_settings(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge platform settings updates into the stored document."""

    merged = {**DEFAULT_PLATFORM_SETTINGS, **current}
    current_alerts = merged.get("alerts")
    if not isinstance(current_alerts, dict):
        current_alerts = dict(DEFAULT_PLATFORM_SETTINGS["alerts"])
    update_alerts = updates.get("alerts")
    if isinstance(update_alerts, dict):
        merged["alerts"] = {**current_alerts, **update_alerts}
    else:
        merged["alerts"] = current_alerts
    return normalize_platform_settings_payload(merged)


def platform_alert_defaults(settings: dict[str, Any] | None) -> dict[str, Any]:
    """Return target alert defaults derived from platform settings."""

    alerts = DEFAULT_PLATFORM_SETTINGS["alerts"]
    if isinstance(settings, dict):
        stored_alerts = settings.get("alerts")
        if isinstance(stored_alerts, dict):
            alerts = {**alerts, **stored_alerts}

    return {
        "enabled": False,
        "notification": bool(alerts.get("defaultNotification", DEFAULT_TARGET_ALERT["notification"])),
        "sound": bool(alerts.get("defaultSound", DEFAULT_TARGET_ALERT["sound"])),
        "email": bool(alerts.get("defaultEmail", DEFAULT_TARGET_ALERT["email"])),
        "emailTo": str(alerts.get("defaultEmailTo") or ""),
        "onDegraded": bool(alerts.get("defaultOnDegraded", DEFAULT_TARGET_ALERT["onDegraded"])),
        "onDown": bool(alerts.get("defaultOnDown", DEFAULT_TARGET_ALERT["onDown"])),
        "cooldownMs": int(alerts.get("defaultCooldownMs", DEFAULT_TARGET_ALERT["cooldownMs"])),
    }


def platform_settings_to_api(settings: dict[str, Any]) -> dict[str, Any]:
    """Serialize platform settings for the API."""

    alerts = settings["alerts"]
    return {
        "alerts": {
            "defaultNotification": bool(alerts["defaultNotification"]),
            "defaultSound": bool(alerts["defaultSound"]),
            "defaultEmail": bool(alerts["defaultEmail"]),
            "defaultEmailTo": str(alerts.get("defaultEmailTo") or ""),
            "defaultOnDegraded": bool(alerts["defaultOnDegraded"]),
            "defaultOnDown": bool(alerts["defaultOnDown"]),
            "defaultCooldownMs": int(alerts["defaultCooldownMs"]),
        }
    }
