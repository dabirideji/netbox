"""Alert and SMTP configuration normalization."""

from __future__ import annotations

from typing import Any

SMTP_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "resend": {
        "host": "smtp.resend.com",
        "port": 587,
        "username": "resend",
        "useTls": True,
    },
    "custom": {
        "host": "",
        "port": 587,
        "username": "",
        "useTls": True,
    },
}

DEFAULT_TARGET_ALERT: dict[str, Any] = {
    "enabled": False,
    "notification": True,
    "sound": True,
    "email": False,
    "emailTo": "",
    "onDegraded": True,
    "onDown": True,
    "cooldownMs": 300_000,
}


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("cooldownMs must be an integer") from None
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"cooldownMs must be between {minimum} and {maximum}")
    return parsed


def normalize_target_alert_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and normalize one target alert rules payload."""

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("alert payload must be a JSON object")

    email = _bool(payload.get("email"), DEFAULT_TARGET_ALERT["email"])
    email_to = str(payload.get("emailTo") or "").strip()
    if email and not email_to:
        raise ValueError("emailTo is required when email alerts are enabled")

    return {
        "enabled": _bool(payload.get("enabled"), DEFAULT_TARGET_ALERT["enabled"]),
        "notification": _bool(payload.get("notification"), DEFAULT_TARGET_ALERT["notification"]),
        "sound": _bool(payload.get("sound"), DEFAULT_TARGET_ALERT["sound"]),
        "email": email,
        "emailTo": email_to,
        "onDegraded": _bool(payload.get("onDegraded"), DEFAULT_TARGET_ALERT["onDegraded"]),
        "onDown": _bool(payload.get("onDown"), DEFAULT_TARGET_ALERT["onDown"]),
        "cooldownMs": _int(
            payload.get("cooldownMs"),
            DEFAULT_TARGET_ALERT["cooldownMs"],
            minimum=30_000,
            maximum=3_600_000,
        ),
    }


def normalize_smtp_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and normalize SMTP provider settings."""

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("smtp payload must be a JSON object")

    provider = str(payload.get("provider") or "custom").strip().lower()
    if provider not in SMTP_PROVIDER_PRESETS:
        raise ValueError("provider must be resend or custom")

    preset = SMTP_PROVIDER_PRESETS[provider]
    host = str(payload.get("host") or preset["host"]).strip()
    port_raw = payload.get("port", preset["port"])
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        raise ValueError("port must be an integer") from None
    if port < 1 or port > 65_535:
        raise ValueError("port must be between 1 and 65535")

    username = str(payload.get("username") if payload.get("username") is not None else preset["username"]).strip()
    from_email = str(payload.get("fromEmail") or "").strip()
    from_name = str(payload.get("fromName") or "Netbox").strip() or "Netbox"
    use_tls = _bool(payload.get("useTls"), bool(preset["useTls"]))
    password = payload.get("password")
    if password is not None and not isinstance(password, str):
        raise ValueError("password must be a string")

    if provider == "custom" and not host:
        raise ValueError("host is required for custom SMTP providers")
    if not from_email:
        raise ValueError("fromEmail is required")

    return {
        "provider": provider,
        "host": host,
        "port": port,
        "username": username,
        "fromEmail": from_email,
        "fromName": from_name,
        "useTls": use_tls,
        "password": password,
    }


def target_alert_to_api(target_id: str, rules: dict[str, Any], *, smtp_configured: bool) -> dict[str, Any]:
    """Serialize target alert rules for the API."""

    return {
        "targetId": target_id,
        "enabled": bool(rules["enabled"]),
        "notification": bool(rules["notification"]),
        "sound": bool(rules["sound"]),
        "email": bool(rules["email"]),
        "emailTo": str(rules.get("emailTo") or ""),
        "onDegraded": bool(rules["onDegraded"]),
        "onDown": bool(rules["onDown"]),
        "cooldownMs": int(rules["cooldownMs"]),
        "smtpConfigured": smtp_configured,
    }


def smtp_settings_to_api(settings: dict[str, Any]) -> dict[str, Any]:
    """Serialize SMTP settings without exposing the stored password."""

    return {
        "provider": settings["provider"],
        "host": settings["host"],
        "port": int(settings["port"]),
        "username": settings["username"],
        "fromEmail": settings["fromEmail"],
        "fromName": settings["fromName"],
        "useTls": bool(settings["useTls"]),
        "configured": bool(settings["configured"]),
        "hasPassword": bool(settings.get("hasPassword")),
    }
