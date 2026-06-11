"""Historical check result reads and aggregations."""

from __future__ import annotations

from typing import Any

from netbox.storage.config import build_time_filter
from netbox.storage.rows import check_result_from_row


class HistoryStoreMixin:
    """Overview and per-target history queries."""

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
            ],
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
