"""Persisted storage retention settings."""

from __future__ import annotations

import json
from typing import Any

from netbox.storage.settings import merge_storage_settings, storage_settings_to_api
from netbox.util.json_schema import validate_json_schema


class StorageSettingsStoreMixin:
    """Read and write persisted storage retention settings."""

    def get_storage_settings(self) -> dict[str, Any]:
        """Return the active storage configuration."""

        return storage_settings_to_api(self.storage_config)

    def update_storage_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge storage settings updates, persist them, and enforce new limits."""

        if not isinstance(updates, dict):
            raise ValueError("storage settings payload must be a JSON object")

        validate_json_schema("storage-settings.patch", updates)

        merged = merge_storage_settings(self.storage_config, updates)
        encoded = json.dumps(merged)
        with self.lock:
            self.storage_config = merged
            self.connection.execute(
                """
                INSERT INTO storage_settings (id, data, updated_at)
                VALUES (1, ?, unixepoch() * 1000)
                ON CONFLICT(id) DO UPDATE SET
                  data = excluded.data,
                  updated_at = excluded.updated_at
                """,
                (encoded,),
            )
            self.connection.commit()
            self.enforce_limits()

        return storage_settings_to_api(merged)

    def _load_persisted_storage_settings(self) -> dict[str, Any] | None:
        """Return stored storage settings when present."""

        row = self.connection.execute(
            "SELECT data FROM storage_settings WHERE id = 1",
        ).fetchone()
        if row is None:
            return None

        try:
            data = json.loads(row["data"])
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        return merge_storage_settings({}, data)
