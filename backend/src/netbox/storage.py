"""SQLite persistence for monitor targets, check results, and incidents."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from netbox.models import MonitorConfig, Target
from netbox.summary import latency_warn_ms_for, status_for_result
from netbox.targets import normalize_target_payload, target_to_api

SCHEMA = """
CREATE TABLE IF NOT EXISTS ping_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  checked_at INTEGER NOT NULL,
  target_id TEXT NOT NULL,
  host TEXT NOT NULL,
  label TEXT NOT NULL,
  scope TEXT NOT NULL,
  ok INTEGER NOT NULL,
  latency_ms REAL,
  error TEXT,
  status TEXT NOT NULL,
  severity INTEGER NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_ping_results_checked_at ON ping_results (checked_at);
CREATE INDEX IF NOT EXISTS idx_ping_results_target_checked ON ping_results (target_id, checked_at);

CREATE TABLE IF NOT EXISTS monitor_targets (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  host TEXT NOT NULL,
  scope TEXT NOT NULL,
  target_type TEXT NOT NULL,
  protocol TEXT NOT NULL,
  group_name TEXT NOT NULL,
  environment TEXT NOT NULL,
  enabled INTEGER NOT NULL,
  interval_ms INTEGER NOT NULL,
  timeout_ms INTEGER NOT NULL,
  config_json TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_monitor_targets_enabled ON monitor_targets (enabled);

CREATE TABLE IF NOT EXISTS check_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  checked_at INTEGER NOT NULL,
  target_id TEXT NOT NULL,
  host TEXT NOT NULL,
  label TEXT NOT NULL,
  scope TEXT NOT NULL,
  target_type TEXT NOT NULL,
  protocol TEXT NOT NULL,
  ok INTEGER NOT NULL,
  latency_ms REAL,
  error TEXT,
  status TEXT NOT NULL,
  severity INTEGER NOT NULL,
  duration_ms INTEGER,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_check_results_checked_at ON check_results (checked_at);
CREATE INDEX IF NOT EXISTS idx_check_results_target_checked ON check_results (target_id, checked_at);

CREATE TABLE IF NOT EXISTS status_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_at INTEGER NOT NULL,
  target_id TEXT NOT NULL,
  target_label TEXT NOT NULL,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000),
  UNIQUE(event_at, target_id, from_status, to_status)
);

CREATE INDEX IF NOT EXISTS idx_status_events_event_at ON status_events (event_at);

CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_id TEXT NOT NULL,
  target_label TEXT NOT NULL,
  opened_at INTEGER NOT NULL,
  resolved_at INTEGER,
  status TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_incidents_target_status ON incidents (target_id, status);
CREATE INDEX IF NOT EXISTS idx_incidents_opened_at ON incidents (opened_at);

CREATE TABLE IF NOT EXISTS speed_tests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tested_at INTEGER NOT NULL,
  provider TEXT NOT NULL,
  status TEXT NOT NULL,
  download_mbps REAL,
  upload_mbps REAL,
  latency_ms REAL,
  jitter_ms REAL,
  packet_loss_pct REAL,
  retransmission_pct REAL,
  duration_ms INTEGER,
  server_name TEXT,
  server_location TEXT,
  server_host TEXT,
  error TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);

CREATE INDEX IF NOT EXISTS idx_speed_tests_tested_at ON speed_tests (tested_at);

CREATE TABLE IF NOT EXISTS ui_preferences (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  data TEXT NOT NULL DEFAULT '{}',
  updated_at INTEGER NOT NULL DEFAULT (unixepoch() * 1000)
);
"""

STATUS_SEVERITY = {
    "operational": 0,
    "degraded": 1,
    "down": 2,
    "unknown": 0,
}

DEFAULT_STORAGE_CONFIG: dict[str, Any] = {
    "autoPrune": True,
    "limits": {
        "maxDatabaseBytes": 52_428_800,
        "maxIncidents": 10_000,
        "maxPingSamples": 100_000,
        "maxSpeedTests": 500,
    },
}

STORAGE_CLEAR_SCOPES = frozenset({"incidents", "ping", "speedTests", "all"})


def _merge_preferences(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Shallow-merge top-level keys and deep-merge nested JSON objects."""

    merged = {**current}
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


class StatusStore:
    """Small thread-safe SQLite gateway for monitor history data."""

    def __init__(self, db_path: str | Path, storage_config: dict[str, Any] | None = None) -> None:
        is_memory = str(db_path) == ":memory:"
        self.path = Path(":memory:") if is_memory else Path(db_path).expanduser().resolve()
        self.storage_config = normalize_storage_config(storage_config)
        if not is_memory:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(
            ":memory:" if is_memory else self.path,
            timeout=5,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.connection.execute("PRAGMA busy_timeout = 5000")
            self.connection.execute("PRAGMA foreign_keys = ON")
            if not is_memory:
                self.connection.execute("PRAGMA journal_mode = WAL")
            self.connection.executescript(SCHEMA)
            self.connection.commit()

    def record_sample(self, sample: dict[str, Any], config: MonitorConfig) -> None:
        """Store all target results for one sampling tick."""

        rows = []
        check_rows = []
        for result in sample["results"]:
            target = self._target_for_result(result)
            status = status_for_result(result, latency_warn_ms_for(target, config), target)
            rows.append(
                (
                    sample["checkedAt"],
                    result["id"],
                    result["host"],
                    result["label"],
                    result["scope"],
                    1 if result["ok"] else 0,
                    result["latencyMs"],
                    result["error"],
                    status,
                    STATUS_SEVERITY[status],
                )
            )
            check_rows.append(
                (
                    result.get("checkedAt", sample["checkedAt"]),
                    result["id"],
                    result["host"],
                    result["label"],
                    result["scope"],
                    result.get("type", "host"),
                    result.get("protocol", "icmp"),
                    1 if result["ok"] else 0,
                    result["latencyMs"],
                    result["error"],
                    status,
                    STATUS_SEVERITY[status],
                    result.get("durationMs"),
                )
            )

        with self.lock:
            self.connection.executemany(
                """
                INSERT INTO ping_results (
                  checked_at, target_id, host, label, scope, ok, latency_ms, error, status, severity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self.connection.executemany(
                """
                INSERT INTO check_results (
                  checked_at, target_id, host, label, scope, target_type, protocol,
                  ok, latency_ms, error, status, severity, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                check_rows,
            )
            self.connection.commit()
            if self.storage_config["autoPrune"]:
                self.enforce_limits()

    def _target_for_result(self, result: dict[str, Any]) -> Target:
        """Resolve the configured target for a check result, with a safe ICMP fallback."""

        stored = self.get_target(result["id"])
        if stored is not None:
            return stored
        return Target(
            id=result["id"],
            host=result["host"],
            label=result["label"],
            scope=result["scope"],
            type=result.get("type", "host"),
            protocol=result.get("protocol", "icmp"),
        )

    def seed_targets(self, targets: list[Target]) -> None:
        """Insert configured defaults only when a target id is not already stored."""

        with self.lock:
            for target in targets:
                self._upsert_target(target, insert_only=True)
            self.connection.commit()

    def refresh_configured_seeds(self, targets: list[Target]) -> None:
        """Apply updated bundled seed settings to targets that already exist."""

        with self.lock:
            for target in targets:
                if self.get_target(target.id) is None:
                    continue
                self._upsert_target(target)
            self.connection.commit()

    def list_targets(self, enabled_only: bool = False) -> list[Target]:
        """Return all database-managed targets in stable display order."""

        where_sql = "WHERE enabled = 1" if enabled_only else ""
        with self.lock:
            rows = self.connection.execute(
                f"""
                SELECT *
                FROM monitor_targets
                {where_sql}
                ORDER BY group_name COLLATE NOCASE, label COLLATE NOCASE, id COLLATE NOCASE
                """
            ).fetchall()
        return [target_from_row(row) for row in rows]

    def get_target(self, target_id: str) -> Target | None:
        """Return one target by id."""

        with self.lock:
            row = self.connection.execute(
                "SELECT * FROM monitor_targets WHERE id = ?",
                (target_id,),
            ).fetchone()
        return target_from_row(row) if row else None

    def create_target(self, payload: dict[str, Any]) -> Target:
        """Validate and persist a new target."""

        target = normalize_target_payload(payload, index=self._target_count())
        with self.lock:
            target = self._with_unique_target_id(target)
            self._upsert_target(target)
            self.connection.commit()
        return target

    def update_target(self, target_id: str, payload: dict[str, Any]) -> Target:
        """Validate and persist partial target updates."""

        with self.lock:
            existing = self.get_target(target_id)
            if not existing:
                raise ValueError("target was not found")
            target = normalize_target_payload({**payload, "id": target_id}, existing=existing)
            self._upsert_target(target)
            self.connection.commit()
        return target

    def delete_target(self, target_id: str) -> bool:
        """Delete a target configuration while keeping historical results."""

        with self.lock:
            cursor = self.connection.execute("DELETE FROM monitor_targets WHERE id = ?", (target_id,))
            self.connection.commit()
        return cursor.rowcount > 0

    def target_results(
        self,
        target_id: str,
        limit: int,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return newest-first check result history for one target."""

        safe_limit = max(1, min(limit, 1_000))
        safe_offset = max(0, offset)
        time_sql, time_params = build_time_filter("checked_at", from_ms, to_ms, prefix="AND")
        params = (target_id, *time_params)
        with self.lock:
            total = self.connection.execute(
                f"SELECT COUNT(*) AS total FROM check_results WHERE target_id = ? {time_sql}",
                params,
            ).fetchone()["total"]
            rows = self.connection.execute(
                f"""
                SELECT *
                FROM check_results
                WHERE target_id = ?
                {time_sql}
                ORDER BY checked_at DESC
                LIMIT ? OFFSET ?
                """,
                (*params, safe_limit, safe_offset),
            ).fetchall()
        return {
            "targetId": target_id,
            "from": from_ms,
            "to": to_ms,
            "limit": safe_limit,
            "offset": safe_offset,
            "total": total,
            "results": [check_result_from_row(row) for row in rows],
        }

    def record_incident_events(self, events: list[dict[str, Any]]) -> None:
        """Open or resolve durable incident windows from status transition events."""

        if not events:
            return

        with self.lock:
            for event in events:
                target_id = event["targetId"]
                target_label = event["targetLabel"]
                to_status = event["to"]
                if to_status == "operational":
                    self.connection.execute(
                        """
                        UPDATE incidents
                        SET resolved_at = ?, status = 'resolved', message = ?
                        WHERE id = (
                          SELECT id
                          FROM incidents
                          WHERE target_id = ? AND status = 'open'
                          ORDER BY opened_at DESC
                          LIMIT 1
                        )
                        """,
                        (event["at"], event["message"], target_id),
                    )
                    continue

                open_row = self.connection.execute(
                    """
                    SELECT id
                    FROM incidents
                    WHERE target_id = ? AND status = 'open'
                    ORDER BY opened_at DESC
                    LIMIT 1
                    """,
                    (target_id,),
                ).fetchone()
                if open_row:
                    self.connection.execute(
                        """
                        UPDATE incidents
                        SET target_label = ?, message = ?
                        WHERE id = ?
                        """,
                        (target_label, event["message"], open_row["id"]),
                    )
                else:
                    self.connection.execute(
                        """
                        INSERT INTO incidents (
                          target_id, target_label, opened_at, status, message
                        ) VALUES (?, ?, ?, 'open', ?)
                        """,
                        (target_id, target_label, event["at"], event["message"]),
                    )
            self.connection.commit()

    def recent_incidents(
        self,
        limit: int = 50,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return durable incident windows with pagination metadata."""

        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, offset)
        where_sql, where_params = build_time_filter("opened_at", from_ms, to_ms)
        with self.lock:
            total = self.connection.execute(
                f"SELECT COUNT(*) AS total FROM incidents {where_sql}",
                where_params,
            ).fetchone()["total"]
            rows = self.connection.execute(
                f"""
                SELECT *
                FROM incidents
                {where_sql}
                ORDER BY opened_at DESC
                LIMIT ? OFFSET ?
                """,
                (*where_params, safe_limit, safe_offset),
            ).fetchall()
        return {
            "from": from_ms,
            "to": to_ms,
            "limit": safe_limit,
            "offset": safe_offset,
            "total": total,
            "incidents": [incident_from_row(row) for row in rows],
        }

    def _target_count(self) -> int:
        """Return the number of configured targets."""

        with self.lock:
            return int(self.connection.execute("SELECT COUNT(*) AS total FROM monitor_targets").fetchone()["total"])

    def _with_unique_target_id(self, target: Target) -> Target:
        """Append a numeric suffix when a generated target id already exists."""

        if not self.get_target(target.id):
            return target

        base_id = target.id[:72].rstrip("-") or "target"
        suffix = 2
        while self.get_target(f"{base_id}-{suffix}"):
            suffix += 1
        return Target(
            id=f"{base_id}-{suffix}",
            host=target.host,
            label=target.label,
            scope=target.scope,
            type=target.type,
            protocol=target.protocol,
            group=target.group,
            environment=target.environment,
            enabled=target.enabled,
            interval_ms=target.interval_ms,
            timeout_ms=target.timeout_ms,
            config=target.config,
        )

    def _upsert_target(self, target: Target, insert_only: bool = False) -> None:
        """Insert or replace a target row."""

        payload = target_to_api(target)
        params = (
            payload["id"],
            payload["label"],
            payload["host"],
            payload["scope"],
            payload["type"],
            payload["protocol"],
            payload["group"],
            payload["environment"],
            1 if payload["enabled"] else 0,
            payload["intervalMs"],
            payload["timeoutMs"],
            json.dumps(payload["config"], sort_keys=True),
        )
        if insert_only:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO monitor_targets (
                  id, label, host, scope, target_type, protocol, group_name, environment,
                  enabled, interval_ms, timeout_ms, config_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )
            return

        self.connection.execute(
            """
            INSERT INTO monitor_targets (
              id, label, host, scope, target_type, protocol, group_name, environment,
              enabled, interval_ms, timeout_ms, config_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              label = excluded.label,
              host = excluded.host,
              scope = excluded.scope,
              target_type = excluded.target_type,
              protocol = excluded.protocol,
              group_name = excluded.group_name,
              environment = excluded.environment,
              enabled = excluded.enabled,
              interval_ms = excluded.interval_ms,
              timeout_ms = excluded.timeout_ms,
              config_json = excluded.config_json,
              updated_at = unixepoch() * 1000
            """,
            params,
        )

    def history_overview(
        self,
        points: int = 360,
        from_ms: int | None = None,
        to_ms: int | None = None,
    ) -> dict[str, Any]:
        """Return aggregated severity, latency, and loss points over time."""

        limit = max(1, min(points, 2_000))
        where_sql, where_params = build_time_filter("checked_at", from_ms, to_ms)
        with self.lock:
            rows = self.connection.execute(
                f"""
                SELECT
                  checked_at,
                  MAX(severity) AS severity,
                  AVG(CASE WHEN ok = 1 THEN latency_ms END) AS avg_latency_ms,
                  SUM(CASE WHEN ok = 0 THEN 1 ELSE 0 END) AS failures,
                  COUNT(*) AS total
                FROM (
                  SELECT *
                  FROM check_results
                  WHERE checked_at IN (
                    SELECT DISTINCT checked_at
                    FROM check_results
                    {where_sql}
                    ORDER BY checked_at DESC
                    LIMIT ?
                  )
                )
                GROUP BY checked_at
                ORDER BY checked_at ASC
                """,
                (*where_params, limit),
            ).fetchall()

        return {
            "from": from_ms,
            "to": to_ms,
            "points": [
                {
                    "at": row["checked_at"],
                    "severity": row["severity"],
                    "avgLatencyMs": row["avg_latency_ms"],
                    "failurePct": (row["failures"] / row["total"]) * 100 if row["total"] else 0,
                }
                for row in rows
            ]
        }

    def target_history(
        self,
        points: int = 360,
        from_ms: int | None = None,
        to_ms: int | None = None,
    ) -> dict[str, Any]:
        """Return persisted status points grouped by target."""

        limit = max(1, min(points, 2_000))
        where_sql, where_params = build_time_filter("checked_at", from_ms, to_ms)
        with self.lock:
            rows = self.connection.execute(
                f"""
                SELECT
                  checked_at,
                  target_id,
                  host,
                  label,
                  scope,
                  target_type,
                  protocol,
                  ok,
                  latency_ms,
                  error,
                  status,
                  severity
                FROM check_results
                WHERE checked_at IN (
                  SELECT DISTINCT checked_at
                  FROM check_results
                  {where_sql}
                  ORDER BY checked_at DESC
                  LIMIT ?
                )
                ORDER BY target_id ASC, checked_at ASC
                """,
                (*where_params, limit),
            ).fetchall()

        targets: dict[str, dict[str, Any]] = {}
        for row in rows:
            target = targets.setdefault(
                row["target_id"],
                {
                    "id": row["target_id"],
                    "host": row["host"],
                    "label": row["label"],
                    "scope": row["scope"],
                    "type": row["target_type"],
                    "protocol": row["protocol"],
                    "points": [],
                },
            )
            target["points"].append(
                {
                    "at": row["checked_at"],
                    "severity": row["severity"],
                    "status": row["status"],
                    "ok": bool(row["ok"]),
                    "latencyMs": row["latency_ms"],
                    "error": row["error"],
                }
            )

        return {"from": from_ms, "to": to_ms, "targets": list(targets.values())}

    def record_events(self, events: list[dict[str, Any]]) -> None:
        """Persist incident events, ignoring duplicates from repeated summaries."""

        if not events:
            return

        rows = [
            (
                event["at"],
                event["targetId"],
                event["targetLabel"],
                event["from"],
                event["to"],
                event["message"],
            )
            for event in events
        ]

        with self.lock:
            self.connection.executemany(
                """
                INSERT OR IGNORE INTO status_events (
                  event_at, target_id, target_label, from_status, to_status, message
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self.connection.commit()
            if self.storage_config["autoPrune"]:
                self.enforce_limits()

    def recent_events(
        self,
        limit: int = 50,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return paginated incident events ordered newest first."""

        bounded_limit = max(1, min(limit, 500))
        bounded_offset = max(0, offset)
        where_sql, where_params = build_time_filter("event_at", from_ms, to_ms)
        with self.lock:
            total = self.connection.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM status_events
                {where_sql}
                """,
                where_params,
            ).fetchone()["total"]
            rows = self.connection.execute(
                f"""
                SELECT event_at, target_id, target_label, from_status, to_status, message
                FROM status_events
                {where_sql}
                ORDER BY event_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (*where_params, bounded_limit, bounded_offset),
            ).fetchall()

        return {
            "from": from_ms,
            "to": to_ms,
            "limit": bounded_limit,
            "offset": bounded_offset,
            "total": total,
            "events": [
                {
                    "at": row["event_at"],
                    "targetId": row["target_id"],
                    "targetLabel": row["target_label"],
                    "from": row["from_status"],
                    "to": row["to_status"],
                    "message": row["message"],
                }
                for row in rows
            ],
        }

    def record_speed_test(self, test: dict[str, Any]) -> dict[str, Any]:
        """Persist one active speed-test result and return the stored row."""

        with self.lock:
            cursor = self.connection.execute(
                """
                INSERT INTO speed_tests (
                  tested_at,
                  provider,
                  status,
                  download_mbps,
                  upload_mbps,
                  latency_ms,
                  jitter_ms,
                  packet_loss_pct,
                  retransmission_pct,
                  duration_ms,
                  server_name,
                  server_location,
                  server_host,
                  error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test["testedAt"],
                    test["provider"],
                    test["status"],
                    test["downloadMbps"],
                    test["uploadMbps"],
                    test["latencyMs"],
                    test["jitterMs"],
                    test["packetLossPct"],
                    test["retransmissionPct"],
                    test["durationMs"],
                    test["serverName"],
                    test["serverLocation"],
                    test["serverHost"],
                    test["error"],
                ),
            )
            self.connection.commit()
            row = self.connection.execute(
                """
                SELECT
                  id,
                  tested_at,
                  provider,
                  status,
                  download_mbps,
                  upload_mbps,
                  latency_ms,
                  jitter_ms,
                  packet_loss_pct,
                  retransmission_pct,
                  duration_ms,
                  server_name,
                  server_location,
                  server_host,
                  error
                FROM speed_tests
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

        if self.storage_config["autoPrune"]:
            self.enforce_limits()

        return speed_test_from_row(row)

    def recent_speed_tests(
        self,
        limit: int = 20,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return paginated speed-test runs ordered newest first."""

        bounded_limit = max(1, min(limit, 100))
        bounded_offset = max(0, offset)
        where_sql, where_params = build_time_filter("tested_at", from_ms, to_ms)
        with self.lock:
            total = self.connection.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM speed_tests
                {where_sql}
                """,
                where_params,
            ).fetchone()["total"]
            rows = self.connection.execute(
                f"""
                SELECT
                  id,
                  tested_at,
                  provider,
                  status,
                  download_mbps,
                  upload_mbps,
                  latency_ms,
                  jitter_ms,
                  packet_loss_pct,
                  retransmission_pct,
                  duration_ms,
                  server_name,
                  server_location,
                  server_host,
                  error
                FROM speed_tests
                {where_sql}
                ORDER BY tested_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (*where_params, bounded_limit, bounded_offset),
            ).fetchall()
            stats = self.connection.execute(
                f"""
                SELECT
                  AVG(download_mbps) AS avg_download_mbps,
                  AVG(upload_mbps) AS avg_upload_mbps,
                  MIN(latency_ms) AS min_latency_ms,
                  COUNT(*) AS total_runs,
                  COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_runs
                FROM speed_tests
                {where_sql}
                """,
                where_params,
            ).fetchone()

        return {
            "from": from_ms,
            "to": to_ms,
            "limit": bounded_limit,
            "offset": bounded_offset,
            "total": total,
            "stats": {
                "avgDownloadMbps": stats["avg_download_mbps"],
                "avgUploadMbps": stats["avg_upload_mbps"],
                "minLatencyMs": stats["min_latency_ms"],
                "totalRuns": stats["total_runs"],
                "completedRuns": stats["completed_runs"],
            },
            "tests": [speed_test_from_row(row) for row in rows],
        }

    def count_speed_tests_since(self, since_ms: int) -> int:
        """Count active speed-test attempts from a lower-bound timestamp."""

        with self.lock:
            row = self.connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM speed_tests
                WHERE tested_at >= ?
                """,
                (since_ms,),
            ).fetchone()
        return int(row["total"])

    def latest_speed_test(self) -> dict[str, Any] | None:
        """Return the newest stored speed-test run, if any."""

        with self.lock:
            row = self.connection.execute(
                """
                SELECT
                  id,
                  tested_at,
                  provider,
                  status,
                  download_mbps,
                  upload_mbps,
                  latency_ms,
                  jitter_ms,
                  packet_loss_pct,
                  retransmission_pct,
                  duration_ms,
                  server_name,
                  server_location,
                  server_host,
                  error
                FROM speed_tests
                ORDER BY tested_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        return speed_test_from_row(row) if row else None

    def get_preferences(self) -> dict[str, Any]:
        """Return persisted UI preference values."""

        with self.lock:
            row = self.connection.execute(
                "SELECT data FROM ui_preferences WHERE id = 1",
            ).fetchone()

        if row is None:
            return {}

        try:
            data = json.loads(row["data"])
        except json.JSONDecodeError:
            return {}

        return data if isinstance(data, dict) else {}

    def update_preferences(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge UI preference updates into the stored JSON blob."""

        if not isinstance(updates, dict):
            raise ValueError("preferences payload must be a JSON object")

        with self.lock:
            current = self.get_preferences()
            merged = _merge_preferences(current, updates)
            encoded = json.dumps(merged)
            self.connection.execute(
                """
                INSERT INTO ui_preferences (id, data, updated_at)
                VALUES (1, ?, unixepoch() * 1000)
                ON CONFLICT(id) DO UPDATE SET
                  data = excluded.data,
                  updated_at = excluded.updated_at
                """,
                (encoded,),
            )
            self.connection.commit()

        return merged

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

    def enforce_limits(self) -> dict[str, int]:
        """Delete oldest rows when table counts or database size exceed configured limits."""

        with self.lock:
            limits = self.storage_config["limits"]
            deleted = {
                "incidents": self._prune_table_to_limit(
                    "status_events",
                    "event_at ASC, id ASC",
                    limits["maxIncidents"],
                ),
                "pingSamples": self._prune_table_to_limit(
                    "ping_results",
                    "checked_at ASC, id ASC",
                    limits["maxPingSamples"],
                ),
                "speedTests": self._prune_table_to_limit(
                    "speed_tests",
                    "tested_at ASC, id ASC",
                    limits["maxSpeedTests"],
                ),
            }
            deleted["incidents"] += self._prune_table_to_limit(
                "incidents",
                "opened_at ASC, id ASC",
                limits["maxIncidents"],
            )
            deleted["pingSamples"] += self._prune_table_to_limit(
                "check_results",
                "checked_at ASC, id ASC",
                limits["maxPingSamples"],
            )

            max_bytes = limits["maxDatabaseBytes"]
            iterations = 0
            while self.database_bytes() > max_bytes and iterations < 20:
                iterations += 1
                batch_deleted = self._delete_oldest_rows("check_results", "checked_at ASC, id ASC", 5_000)
                if batch_deleted:
                    deleted["pingSamples"] += batch_deleted
                    self.connection.commit()
                    continue

                batch_deleted = self._delete_oldest_rows("ping_results", "checked_at ASC, id ASC", 5_000)
                if batch_deleted:
                    deleted["pingSamples"] += batch_deleted
                    self.connection.commit()
                    continue

                batch_deleted = self._delete_oldest_rows("speed_tests", "tested_at ASC, id ASC", 100)
                if batch_deleted:
                    deleted["speedTests"] += batch_deleted
                    self.connection.commit()
                    continue

                batch_deleted = self._delete_oldest_rows("status_events", "event_at ASC, id ASC", 100)
                if batch_deleted:
                    deleted["incidents"] += batch_deleted
                    self.connection.commit()
                    continue

                batch_deleted = self._delete_oldest_rows("incidents", "opened_at ASC, id ASC", 100)
                if batch_deleted:
                    deleted["incidents"] += batch_deleted
                    self.connection.commit()
                    continue
                break

            self.connection.commit()
            return deleted

    def storage_stats(self) -> dict[str, Any]:
        """Return configured limits and current persisted log usage."""

        limits = self.storage_config["limits"]
        with self.lock:
            usage = {
                "databaseBytes": self.database_bytes(),
                "incidents": self._table_count("status_events"),
                "pingSamples": self._table_count("check_results"),
                "speedTests": self._table_count("speed_tests"),
            }

        return {
            "autoPrune": self.storage_config["autoPrune"],
            "limits": limits,
            "usage": usage,
            "percentUsed": {
                "database": percent_used(usage["databaseBytes"], limits["maxDatabaseBytes"]),
                "incidents": percent_used(usage["incidents"], limits["maxIncidents"]),
                "pingSamples": percent_used(usage["pingSamples"], limits["maxPingSamples"]),
                "speedTests": percent_used(usage["speedTests"], limits["maxSpeedTests"]),
            },
        }

    def clear_storage(self, scope: str) -> dict[str, Any]:
        """Manually delete persisted log rows for one scope."""

        if scope not in STORAGE_CLEAR_SCOPES:
            raise ValueError("scope must be one of incidents, ping, speedTests, or all")

        deleted = {"incidents": 0, "pingSamples": 0, "speedTests": 0}
        with self.lock:
            if scope in {"incidents", "all"}:
                deleted["incidents"] = self._table_count("status_events") + self._table_count("incidents")
                self.connection.execute("DELETE FROM status_events")
                self.connection.execute("DELETE FROM incidents")
            if scope in {"ping", "all"}:
                deleted["pingSamples"] = self._table_count("ping_results") + self._table_count("check_results")
                self.connection.execute("DELETE FROM ping_results")
                self.connection.execute("DELETE FROM check_results")
            if scope in {"speedTests", "all"}:
                deleted["speedTests"] = self._table_count("speed_tests")
                self.connection.execute("DELETE FROM speed_tests")
            self.connection.commit()
            if str(self.path) != ":memory:":
                self.connection.execute("VACUUM")

        return {"deleted": deleted, "stats": self.storage_stats()}

    def close(self) -> None:
        """Close the underlying SQLite connection."""

        with self.lock:
            self.connection.close()


def build_time_filter(
    column: str,
    from_ms: int | None,
    to_ms: int | None,
    prefix: str = "WHERE",
) -> tuple[str, list[int]]:
    """Build a parameterized SQL time filter for an epoch-ms column."""

    clauses = []
    params = []
    if from_ms is not None:
        clauses.append(f"{column} >= ?")
        params.append(from_ms)
    if to_ms is not None:
        clauses.append(f"{column} <= ?")
        params.append(to_ms)
    return (f"{prefix} {' AND '.join(clauses)}", params) if clauses else ("", params)


def normalize_storage_config(storage_config: dict[str, Any] | None) -> dict[str, Any]:
    """Merge partial storage config with safe defaults."""

    base = DEFAULT_STORAGE_CONFIG.copy()
    base["limits"] = DEFAULT_STORAGE_CONFIG["limits"].copy()
    if not storage_config:
        return base

    base["autoPrune"] = bool(storage_config.get("autoPrune", base["autoPrune"]))
    limits = storage_config.get("limits")
    if isinstance(limits, dict):
        for key in base["limits"]:
            if key in limits:
                base["limits"][key] = int(limits[key])
    return base


def percent_used(used: int, limit: int) -> float:
    """Return a 0-100 usage percentage for one storage limit."""

    if limit <= 0:
        return 0.0
    return round(min(100.0, (used / limit) * 100), 1)


def target_from_row(row: sqlite3.Row) -> Target:
    """Convert one SQLite target row into the domain model."""

    try:
        config = json.loads(row["config_json"])
    except json.JSONDecodeError:
        config = {}
    if not isinstance(config, dict):
        config = {}

    return Target(
        id=row["id"],
        host=row["host"],
        label=row["label"],
        scope=row["scope"],
        type=row["target_type"],
        protocol=row["protocol"],
        group=row["group_name"],
        environment=row["environment"],
        enabled=bool(row["enabled"]),
        interval_ms=int(row["interval_ms"]),
        timeout_ms=int(row["timeout_ms"]),
        config=config,
    )


def check_result_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one generalized check-result row to the public API shape."""

    return {
        "id": row["id"],
        "checkedAt": row["checked_at"],
        "targetId": row["target_id"],
        "host": row["host"],
        "label": row["label"],
        "scope": row["scope"],
        "type": row["target_type"],
        "protocol": row["protocol"],
        "ok": bool(row["ok"]),
        "latencyMs": row["latency_ms"],
        "error": row["error"],
        "status": row["status"],
        "severity": row["severity"],
        "durationMs": row["duration_ms"],
    }


def incident_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one incident row to the public API shape."""

    return {
        "id": row["id"],
        "targetId": row["target_id"],
        "targetLabel": row["target_label"],
        "openedAt": row["opened_at"],
        "resolvedAt": row["resolved_at"],
        "status": row["status"],
        "message": row["message"],
    }


def speed_test_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one SQLite speed-test row to the public API shape."""

    return {
        "id": row["id"],
        "testedAt": row["tested_at"],
        "provider": row["provider"],
        "status": row["status"],
        "downloadMbps": row["download_mbps"],
        "uploadMbps": row["upload_mbps"],
        "latencyMs": row["latency_ms"],
        "jitterMs": row["jitter_ms"],
        "packetLossPct": row["packet_loss_pct"],
        "retransmissionPct": row["retransmission_pct"],
        "durationMs": row["duration_ms"],
        "serverName": row["server_name"],
        "serverLocation": row["server_location"],
        "serverHost": row["server_host"],
        "error": row["error"],
    }
