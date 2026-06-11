"""Status events and durable incident windows."""

from __future__ import annotations

from typing import Any

from netbox.storage.config import build_time_filter
from netbox.storage.rows import incident_from_row


class EventStoreMixin:
    """Incident event and window persistence."""

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
