"""Lightweight SQLite schema migrations for existing monitor databases."""

from __future__ import annotations

import sqlite3


def migrate_alert_tables(connection: sqlite3.Connection) -> None:
    """Upgrade alert tables created before newer alert columns were added."""

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    }
    if "target_alerts" not in tables:
        return

    columns = {row[1] for row in connection.execute("PRAGMA table_info(target_alerts)")}
    if "email_to" not in columns:
        connection.execute(
            "ALTER TABLE target_alerts ADD COLUMN email_to TEXT NOT NULL DEFAULT ''",
        )


def migrate_platform_settings(connection: sqlite3.Connection) -> None:
    """Add persisted platform-wide settings."""

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    }
    if "platform_settings" in tables:
        return

    connection.executescript(
        """
        CREATE TABLE platform_settings (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          data TEXT NOT NULL DEFAULT '{}',
          updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
        );
        """
    )


def migrate_alert_dispatch_state(connection: sqlite3.Connection) -> None:
    """Add persisted server-side alert scheduling state."""

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    }
    if "alert_dispatch_state" in tables:
        return

    connection.executescript(
        """
        CREATE TABLE alert_dispatch_state (
          target_id TEXT NOT NULL,
          channel TEXT NOT NULL,
          last_sent_at INTEGER NOT NULL,
          next_due_at INTEGER NOT NULL,
          updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000),
          PRIMARY KEY (target_id, channel),
          FOREIGN KEY (target_id) REFERENCES monitor_targets(id) ON DELETE CASCADE
        );

        CREATE INDEX idx_alert_dispatch_next_due ON alert_dispatch_state (next_due_at);
        """
    )


def migrate_monitor_targets_is_favorite(connection: sqlite3.Connection) -> None:
    """Add live-check favorites when upgrading older databases."""

    columns = {row[1] for row in connection.execute("PRAGMA table_info(monitor_targets)")}
    if "is_favorite" in columns:
        return

    connection.execute("ALTER TABLE monitor_targets ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0")


def migrate_monitor_targets_sort_order(connection: sqlite3.Connection) -> None:
    """Add persisted target ordering when upgrading older databases."""

    columns = {row[1] for row in connection.execute("PRAGMA table_info(monitor_targets)")}
    if "sort_order" in columns:
        return

    connection.execute("ALTER TABLE monitor_targets ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
    rows = connection.execute(
        """
        SELECT id
        FROM monitor_targets
        ORDER BY group_name COLLATE NOCASE, label COLLATE NOCASE, id COLLATE NOCASE
        """
    ).fetchall()
    for index, row in enumerate(rows):
        connection.execute(
            "UPDATE monitor_targets SET sort_order = ? WHERE id = ?",
            (index, row["id"]),
        )
