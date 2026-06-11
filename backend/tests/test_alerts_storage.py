import sqlite3
from pathlib import Path

from netbox.storage import StatusStore
from netbox.storage.migrations import migrate_alert_dispatch_state


def test_migrate_alert_tables_adds_email_to_column(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE target_alerts (
          target_id TEXT PRIMARY KEY,
          enabled INTEGER NOT NULL DEFAULT 0,
          notification INTEGER NOT NULL DEFAULT 1,
          sound INTEGER NOT NULL DEFAULT 1,
          email INTEGER NOT NULL DEFAULT 0,
          on_degraded INTEGER NOT NULL DEFAULT 1,
          on_down INTEGER NOT NULL DEFAULT 1,
          cooldown_ms INTEGER NOT NULL DEFAULT 300000,
          updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
        );
        """
    )
    connection.commit()
    connection.close()

    store = StatusStore(db_path)
    columns = {
        row[1] for row in store.connection.execute("PRAGMA table_info(target_alerts)").fetchall()
    }
    assert "email_to" in columns
    assert store.get_target_alert("missing-target")["emailTo"] == ""


def test_smtp_settings_encrypt_password(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")

    settings = store.update_smtp_settings(
        {
            "provider": "resend",
            "fromEmail": "alerts@example.com",
            "password": "re_secret_key",
        }
    )

    assert settings["configured"] is True
    assert settings["hasPassword"] is True
    assert store.get_smtp_password() == "re_secret_key"

    public = store.get_smtp_settings()
    assert "password" not in public


def test_target_alert_persists_rules(tmp_path: Path) -> None:
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
    store.update_smtp_settings(
        {
            "provider": "resend",
            "fromEmail": "alerts@example.com",
            "password": "re_secret_key",
        }
    )

    saved = store.update_target_alert(
        "api-1",
        {
            "enabled": True,
            "email": True,
            "emailTo": "ops@example.com",
            "notification": True,
            "sound": False,
        },
    )

    assert saved["email"] is True
    assert saved["emailTo"] == "ops@example.com"
    assert store.get_target_alert("api-1")["sound"] is False


def test_migrate_alert_dispatch_state_creates_table(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE monitor_targets (
          id TEXT PRIMARY KEY,
          label TEXT NOT NULL,
          host TEXT NOT NULL DEFAULT '',
          scope TEXT NOT NULL,
          type TEXT NOT NULL,
          protocol TEXT NOT NULL,
          group_name TEXT NOT NULL DEFAULT 'Default',
          environment TEXT NOT NULL DEFAULT 'prod',
          enabled INTEGER NOT NULL DEFAULT 1,
          interval_ms INTEGER NOT NULL DEFAULT 1000,
          timeout_ms INTEGER NOT NULL DEFAULT 900,
          config_json TEXT NOT NULL DEFAULT '{}',
          sort_order INTEGER NOT NULL DEFAULT 0,
          is_favorite INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    connection.commit()
    migrate_alert_dispatch_state(connection)
    connection.commit()
    tables = {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    connection.close()

    assert "alert_dispatch_state" in tables


def test_alert_dispatch_state_persists_schedule(tmp_path: Path) -> None:
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

    assert store.get_next_due_at("api-1", "sound") is None

    store.mark_channel_sent("api-1", "sound", sent_at=1_000, next_due_at=61_000)
    assert store.get_next_due_at("api-1", "sound") == 61_000

    store.clear_target("api-1")
    assert store.get_next_due_at("api-1", "sound") is None
