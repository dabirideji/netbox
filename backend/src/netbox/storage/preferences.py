"""UI preference persistence."""

from __future__ import annotations

import json
from typing import Any

from netbox.storage.config import merge_preferences


class PreferenceStoreMixin:
    """Dashboard UI preference reads and writes."""

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
            merged = merge_preferences(current, updates)
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
