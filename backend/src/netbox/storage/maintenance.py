"""Storage pruning, clearing, and usage statistics."""

from __future__ import annotations

from typing import Any

from netbox.storage.config import percent_used
from netbox.storage.constants import STORAGE_CLEAR_SCOPES


class MaintenanceStoreMixin:
    """Auto-prune, manual clear, and storage usage reporting."""

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
