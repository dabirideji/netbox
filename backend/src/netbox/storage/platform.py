"""Platform-wide settings persistence."""

from __future__ import annotations

import json
from typing import Any

from netbox.alerts.platform import (
    DEFAULT_PLATFORM_SETTINGS,
    merge_platform_settings,
    normalize_platform_settings_payload,
)


class PlatformStoreMixin:
    """Read and write persisted platform settings."""

    def get_platform_settings(self) -> dict[str, Any]:
        """Return stored platform settings merged with defaults."""

        with self.lock:
            row = self.connection.execute(
                "SELECT data FROM platform_settings WHERE id = 1",
            ).fetchone()

        if row is None:
            return dict(DEFAULT_PLATFORM_SETTINGS)

        try:
            data = json.loads(row["data"])
        except json.JSONDecodeError:
            return dict(DEFAULT_PLATFORM_SETTINGS)

        if not isinstance(data, dict):
            return dict(DEFAULT_PLATFORM_SETTINGS)

        return merge_platform_settings({}, data)

    def update_platform_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge platform settings updates into storage."""

        if not isinstance(updates, dict):
            raise ValueError("platform settings payload must be a JSON object")

        current = self.get_platform_settings()
        merged = merge_platform_settings(current, updates)
        encoded = json.dumps(merged)
        with self.lock:
            self.connection.execute(
                """
                INSERT INTO platform_settings (id, data, updated_at)
                VALUES (1, ?, unixepoch() * 1000)
                ON CONFLICT(id) DO UPDATE SET
                  data = excluded.data,
                  updated_at = excluded.updated_at
                """,
                (encoded,),
            )
            self.connection.commit()

        return merged
