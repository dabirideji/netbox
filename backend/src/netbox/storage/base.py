"""SQLite connection lifecycle and low-level table helpers."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from netbox.storage.config import normalize_storage_config
from netbox.storage.migrations import (
    migrate_alert_dispatch_state,
    migrate_alert_tables,
    migrate_monitor_targets_is_favorite,
    migrate_monitor_targets_sort_order,
    migrate_platform_settings,
    migrate_speed_tests_network,
    migrate_storage_settings,
)
from netbox.storage.settings import merge_storage_settings
from netbox.storage.schema import SCHEMA


class StoreBase:
    """Shared SQLite connection, lock, and schema initialization."""

    path: Path
    storage_config: dict[str, Any]
    connection: sqlite3.Connection
    lock: threading.RLock

    def __init__(self, db_path: str | Path, storage_config: dict[str, Any] | None = None) -> None:
        is_memory = str(db_path) == ":memory:"
        self.path = Path(":memory:") if is_memory else Path(db_path).expanduser().resolve()
        self.storage_config = normalize_storage_config(storage_config)
        if not is_memory:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._closed = False
        self.connection = self._open_connection(is_memory)
        self._initialize_connection(is_memory)

    def _open_connection(self, is_memory: bool) -> sqlite3.Connection:
        last_error: sqlite3.OperationalError | None = None

        for attempt in range(6):
            try:
                connection = sqlite3.connect(
                    ":memory:" if is_memory else self.path,
                    timeout=5,
                    check_same_thread=False,
                )
                connection.row_factory = sqlite3.Row
                return connection
            except sqlite3.OperationalError as error:
                last_error = error
                if "locked" not in str(error).lower() or attempt == 5:
                    raise
                time.sleep(0.15 * (attempt + 1))

        if last_error is not None:
            raise last_error
        raise sqlite3.OperationalError("database is locked")

    def _initialize_connection(self, is_memory: bool) -> None:
        last_error: sqlite3.OperationalError | None = None

        for attempt in range(6):
            try:
                with self.lock:
                    self.connection.execute("PRAGMA busy_timeout = 5000")
                    self.connection.execute("PRAGMA foreign_keys = ON")
                    if not is_memory:
                        self.connection.execute("PRAGMA journal_mode = WAL")
                    self.connection.executescript(SCHEMA)
                    migrate_monitor_targets_sort_order(self.connection)
                    migrate_monitor_targets_is_favorite(self.connection)
                    migrate_alert_tables(self.connection)
                    migrate_alert_dispatch_state(self.connection)
                    migrate_platform_settings(self.connection)
                    migrate_storage_settings(self.connection)
                    migrate_speed_tests_network(self.connection)
                    persisted = self.connection.execute(
                        "SELECT data FROM storage_settings WHERE id = 1",
                    ).fetchone()
                    if persisted is not None:
                        try:
                            data = json.loads(persisted["data"])
                            if isinstance(data, dict):
                                self.storage_config = merge_storage_settings(self.storage_config, data)
                        except json.JSONDecodeError:
                            pass
                    self.connection.commit()
                return
            except sqlite3.OperationalError as error:
                last_error = error
                if "locked" not in str(error).lower() or attempt == 5:
                    raise
                with self.lock:
                    self.connection.close()
                self.connection = self._open_connection(is_memory)
                time.sleep(0.15 * (attempt + 1))

        if last_error is not None:
            raise last_error

    def database_bytes(self) -> int:
        """Return the current SQLite database size in bytes."""

        with self.lock:
            if str(self.path) == ":memory:":
                page_count = self.connection.execute("PRAGMA page_count").fetchone()[0]
                page_size = self.connection.execute("PRAGMA page_size").fetchone()[0]
                return int(page_count) * int(page_size)
            if self.path.is_file():
                return self.path.stat().st_size
        return 0

    def _table_count(self, table: str) -> int:
        row = self.connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
        return int(row["total"])

    def _delete_oldest_rows(self, table: str, order_by: str, delete_count: int) -> int:
        if delete_count <= 0:
            return 0

        cursor = self.connection.execute(
            f"""
            DELETE FROM {table}
            WHERE rowid IN (
              SELECT rowid
              FROM {table}
              ORDER BY {order_by}
              LIMIT ?
            )
            """,
            (delete_count,),
        )
        return cursor.rowcount

    def _prune_table_to_limit(self, table: str, order_by: str, max_rows: int) -> int:
        total = self._table_count(table)
        if total <= max_rows:
            return 0
        return self._delete_oldest_rows(table, order_by, total - max_rows)

    @property
    def closed(self) -> bool:
        """Return whether the store connection has been closed."""

        return self._closed

    def close(self) -> None:
        """Close the underlying SQLite connection."""

        with self.lock:
            if self._closed:
                return
            self._closed = True
            self.connection.close()
