"""Speed test result persistence."""

from __future__ import annotations

from typing import Any

from netbox.storage.config import build_time_filter
from netbox.storage.rows import speed_test_from_row


class SpeedTestStoreMixin:
    """Speed test writes and paginated reads."""

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
