from __future__ import annotations

from pathlib import Path

from netbox.alerts.platform import DEFAULT_PLATFORM_SETTINGS, platform_alert_defaults
from netbox.storage import StatusStore


def test_platform_settings_defaults(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")

    settings = store.get_platform_settings()

    assert settings == DEFAULT_PLATFORM_SETTINGS
    assert store.get_target_alert("missing-target") == platform_alert_defaults(settings)


def test_platform_settings_persist_alert_defaults(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    store.create_target(
        {
            "id": "api-1",
            "label": "API",
            "host": "127.0.0.1",
            "scope": "external",
            "type": "api",
            "protocol": "https",
            "group": "Default",
            "environment": "prod",
            "enabled": True,
            "intervalMs": 1000,
            "timeoutMs": 900,
            "config": {},
        }
    )

    store.update_platform_settings(
        {
            "alerts": {
                "defaultNotification": False,
                "defaultSound": True,
                "defaultEmail": True,
                "defaultEmailTo": "ops@example.com",
                "defaultOnDegraded": False,
                "defaultOnDown": True,
                "defaultCooldownMs": 120_000,
            }
        }
    )

    defaults = store.get_target_alert("api-1")

    assert defaults["notification"] is False
    assert defaults["sound"] is True
    assert defaults["email"] is True
    assert defaults["emailTo"] == "ops@example.com"
    assert defaults["onDegraded"] is False
    assert defaults["onDown"] is True
    assert defaults["cooldownMs"] == 120_000
