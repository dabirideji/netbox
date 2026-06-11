"""Check sample persistence."""

from __future__ import annotations

from typing import Any

from netbox.core.models import MonitorConfig, Target
from netbox.storage.constants import STATUS_SEVERITY
from netbox.monitor.summary import latency_warn_ms_for, status_for_result


class SampleStoreMixin:
    """Persist one sampling tick across legacy and generalized result tables."""

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
