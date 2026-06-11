"""Storage constants and default configuration."""

from __future__ import annotations

from typing import Any

from netbox.responses import STATUS_SEVERITY, STORAGE_CLEAR_SCOPE_VALUES

DEFAULT_STORAGE_CONFIG: dict[str, Any] = {
    "autoPrune": True,
    "limits": {
        "maxDatabaseBytes": 52_428_800,
        "maxIncidents": 10_000,
        "maxPingSamples": 100_000,
        "maxSpeedTests": 500,
    },
}

STORAGE_CLEAR_SCOPES = STORAGE_CLEAR_SCOPE_VALUES

__all__ = ["DEFAULT_STORAGE_CONFIG", "STATUS_SEVERITY", "STORAGE_CLEAR_SCOPES"]
