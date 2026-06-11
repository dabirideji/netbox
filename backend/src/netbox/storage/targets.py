"""Monitor target CRUD persistence."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from netbox.core.models import Target
from netbox.storage.rows import target_from_row
from netbox.targets import normalize_target_payload, target_to_api


class TargetStoreMixin:
    """Target configuration reads and writes."""

    def seed_targets(self, targets: list[Target]) -> None:
        """Insert configured defaults only when a target id is not already stored."""

        with self.lock:
            next_order = self._next_sort_order()
            inserted = 0
            for target in targets:
                if self.get_target(target.id) is not None:
                    self._upsert_target(target, insert_only=True)
                    continue
                ordered = replace(target, sort_order=next_order + inserted)
                self._upsert_target(ordered, insert_only=True)
                inserted += 1
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
                ORDER BY sort_order ASC, id COLLATE NOCASE
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
        target = replace(target, sort_order=self._next_sort_order())
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
            target = replace(target, sort_order=existing.sort_order, is_favorite=existing.is_favorite)
            self._upsert_target(target)
            self.connection.commit()
        return target

    def set_target_favorite(self, target_id: str, favorite: bool) -> Target:
        """Persist whether a target is pinned to the top of live checks."""

        with self.lock:
            existing = self.get_target(target_id)
            if not existing:
                raise ValueError("target was not found")
            self.connection.execute(
                """
                UPDATE monitor_targets
                SET is_favorite = ?, updated_at = unixepoch() * 1000
                WHERE id = ?
                """,
                (1 if favorite else 0, target_id),
            )
            self.connection.commit()
        updated = self.get_target(target_id)
        if not updated:
            raise ValueError("target was not found")
        return updated

    def reorder_targets(self, order: list[str]) -> list[Target]:
        """Persist a new display order for all configured targets."""

        with self.lock:
            current = self.list_targets()
            current_ids = {target.id for target in current}
            ordered_ids = list(dict.fromkeys(order))
            if set(ordered_ids) != current_ids:
                raise ValueError("order must include every configured target exactly once")

            for index, target_id in enumerate(ordered_ids):
                self.connection.execute(
                    """
                    UPDATE monitor_targets
                    SET sort_order = ?, updated_at = unixepoch() * 1000
                    WHERE id = ?
                    """,
                    (index, target_id),
                )
            self.connection.commit()
        return self.list_targets()

    def delete_target(self, target_id: str) -> bool:
        """Delete a target configuration while keeping historical results."""

        with self.lock:
            cursor = self.connection.execute("DELETE FROM monitor_targets WHERE id = ?", (target_id,))
            self.connection.commit()
        return cursor.rowcount > 0

    def _target_count(self) -> int:
        """Return the number of configured targets."""

        with self.lock:
            return int(self.connection.execute("SELECT COUNT(*) AS total FROM monitor_targets").fetchone()["total"])

    def _next_sort_order(self) -> int:
        """Return the next available sort index."""

        with self.lock:
            row = self.connection.execute("SELECT COALESCE(MAX(sort_order), -1) AS max_order FROM monitor_targets").fetchone()
        return int(row["max_order"]) + 1

    def _with_unique_target_id(self, target: Target) -> Target:
        """Append a numeric suffix when a generated target id already exists."""

        if not self.get_target(target.id):
            return target

        base_id = target.id[:72].rstrip("-") or "target"
        suffix = 2
        while self.get_target(f"{base_id}-{suffix}"):
            suffix += 1
        return replace(
            target,
            id=f"{base_id}-{suffix}",
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
            payload["sortOrder"],
            1 if payload["isFavorite"] else 0,
        )
        if insert_only:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO monitor_targets (
                  id, label, host, scope, target_type, protocol, group_name, environment,
                  enabled, interval_ms, timeout_ms, config_json, sort_order, is_favorite
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )
            return

        self.connection.execute(
            """
            INSERT INTO monitor_targets (
              id, label, host, scope, target_type, protocol, group_name, environment,
              enabled, interval_ms, timeout_ms, config_json, sort_order, is_favorite
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
