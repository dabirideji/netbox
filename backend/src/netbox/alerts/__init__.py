"""Alert rules, SMTP delivery, and notification dispatch."""

from netbox.alerts.dispatcher import dispatch_ongoing_alerts, dispatch_target_alerts
from netbox.alerts.models import (
    DEFAULT_TARGET_ALERT,
    SMTP_PROVIDER_PRESETS,
    normalize_smtp_payload,
    normalize_target_alert_payload,
    smtp_settings_to_api,
    target_alert_to_api,
)

__all__ = [
    "DEFAULT_TARGET_ALERT",
    "SMTP_PROVIDER_PRESETS",
    "dispatch_ongoing_alerts",
    "dispatch_target_alerts",
    "normalize_smtp_payload",
    "normalize_target_alert_payload",
    "smtp_settings_to_api",
    "target_alert_to_api",
]
