"""SQLite row to API model converters."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from netbox.core.models import Target


def target_from_row(row: sqlite3.Row) -> Target:
    """Convert one SQLite target row into the domain model."""

    try:
        config = json.loads(row["config_json"])
    except json.JSONDecodeError:
        config = {}
    if not isinstance(config, dict):
        config = {}

    return Target(
        id=row["id"],
        host=row["host"],
        label=row["label"],
        scope=row["scope"],
        type=row["target_type"],
        protocol=row["protocol"],
        group=row["group_name"],
        environment=row["environment"],
        enabled=bool(row["enabled"]),
        interval_ms=int(row["interval_ms"]),
        timeout_ms=int(row["timeout_ms"]),
        config=config,
        sort_order=int(row["sort_order"]),
        is_favorite=bool(row["is_favorite"]),
    )


def sample_result_from_check_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one check-result row into the in-memory sample result shape."""

    return {
        "id": row["target_id"],
        "host": row["host"],
        "label": row["label"],
        "scope": row["scope"],
        "type": row["target_type"],
        "protocol": row["protocol"],
        "ok": bool(row["ok"]),
        "latencyMs": row["latency_ms"],
        "error": row["error"],
        "checkedAt": row["checked_at"],
        "durationMs": row["duration_ms"],
    }


def check_result_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one generalized check-result row to the public API shape."""

    return {
        "id": row["id"],
        "checkedAt": row["checked_at"],
        "targetId": row["target_id"],
        "host": row["host"],
        "label": row["label"],
        "scope": row["scope"],
        "type": row["target_type"],
        "protocol": row["protocol"],
        "ok": bool(row["ok"]),
        "latencyMs": row["latency_ms"],
        "error": row["error"],
        "status": row["status"],
        "severity": row["severity"],
        "durationMs": row["duration_ms"],
    }


def incident_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one incident row to the public API shape."""

    return {
        "id": row["id"],
        "targetId": row["target_id"],
        "targetLabel": row["target_label"],
        "openedAt": row["opened_at"],
        "resolvedAt": row["resolved_at"],
        "status": row["status"],
        "message": row["message"],
    }


def speed_test_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one SQLite speed-test row to the public API shape."""

    return {
        "id": row["id"],
        "testedAt": row["tested_at"],
        "provider": row["provider"],
        "status": row["status"],
        "downloadMbps": row["download_mbps"],
        "uploadMbps": row["upload_mbps"],
        "latencyMs": row["latency_ms"],
        "jitterMs": row["jitter_ms"],
        "packetLossPct": row["packet_loss_pct"],
        "retransmissionPct": row["retransmission_pct"],
        "durationMs": row["duration_ms"],
        "serverName": row["server_name"],
        "serverLocation": row["server_location"],
        "serverHost": row["server_host"],
        "error": row["error"],
        "networkName": row["network_name"] if "network_name" in row.keys() else None,
        "networkSsid": row["network_ssid"] if "network_ssid" in row.keys() else None,
        "networkInterface": row["network_interface"] if "network_interface" in row.keys() else None,
        "networkService": row["network_service"] if "network_service" in row.keys() else None,
    }
