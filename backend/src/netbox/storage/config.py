"""Storage configuration helpers and SQL utilities."""

from __future__ import annotations

from typing import Any

from netbox.storage.constants import DEFAULT_STORAGE_CONFIG


def merge_preferences(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Shallow-merge top-level keys and deep-merge nested JSON objects."""

    merged = {**current}
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


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
