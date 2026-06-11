"""Storage retention settings normalization and merge helpers."""

from __future__ import annotations

from typing import Any

from netbox.storage.constants import DEFAULT_STORAGE_CONFIG
from netbox.storage.config import normalize_storage_config


def merge_storage_settings(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge storage settings updates into the active configuration."""

    merged = {
        "autoPrune": bool(current.get("autoPrune", DEFAULT_STORAGE_CONFIG["autoPrune"])),
        "limits": {**current["limits"]},
    }

    if "autoPrune" in updates:
        merged["autoPrune"] = bool(updates["autoPrune"])

    limits = updates.get("limits")
    if isinstance(limits, dict):
        for key in merged["limits"]:
            if key in limits:
                merged["limits"][key] = int(limits[key])

    return normalize_storage_config(merged)


def storage_settings_to_api(config: dict[str, Any]) -> dict[str, Any]:
    """Serialize storage settings for the API."""

    limits = config["limits"]
    return {
        "autoPrune": bool(config["autoPrune"]),
        "limits": {
            "maxDatabaseBytes": int(limits["maxDatabaseBytes"]),
            "maxIncidents": int(limits["maxIncidents"]),
            "maxPingSamples": int(limits["maxPingSamples"]),
            "maxSpeedTests": int(limits["maxSpeedTests"]),
        },
    }
