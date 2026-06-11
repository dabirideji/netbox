"""Validation and policy helpers for browser-run speed tests."""

from __future__ import annotations

from typing import Any

from netbox.core.responses import VALID_SPEED_STATUSES

MAX_LABEL_LENGTH = 120
MAX_ERROR_LENGTH = 240
ONE_DAY_MS = 24 * 60 * 60 * 1000


def normalize_speed_test(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a speed-test payload from the browser client."""

    tested_at = bounded_int(payload.get("testedAt"), "testedAt", 0, 10_000_000_000_000)
    provider = bounded_text(payload.get("provider", "mlab-ndt7"), "provider", 1, 40)
    status = bounded_text(payload.get("status", "completed"), "status", 1, 20)
    if status not in VALID_SPEED_STATUSES:
        raise ValueError("speed test status must be completed or failed")

    return {
        "testedAt": tested_at,
        "provider": provider,
        "status": status,
        "downloadMbps": optional_float(payload.get("downloadMbps"), "downloadMbps", 0, 100_000),
        "uploadMbps": optional_float(payload.get("uploadMbps"), "uploadMbps", 0, 100_000),
        "latencyMs": optional_float(payload.get("latencyMs"), "latencyMs", 0, 60_000),
        "jitterMs": optional_float(payload.get("jitterMs"), "jitterMs", 0, 60_000),
        "packetLossPct": optional_float(payload.get("packetLossPct"), "packetLossPct", 0, 100),
        "retransmissionPct": optional_float(payload.get("retransmissionPct"), "retransmissionPct", 0, 100),
        "durationMs": optional_int(payload.get("durationMs"), "durationMs", 0, 120_000),
        "serverName": optional_text(payload.get("serverName"), "serverName", MAX_LABEL_LENGTH),
        "serverLocation": optional_text(payload.get("serverLocation"), "serverLocation", MAX_LABEL_LENGTH),
        "serverHost": optional_text(payload.get("serverHost"), "serverHost", MAX_LABEL_LENGTH),
        "error": optional_text(payload.get("error"), "error", MAX_ERROR_LENGTH),
    }


def speed_policy(
    config: dict[str, object],
    latest: dict[str, Any] | None,
    runs_last_day: int,
    now_ms: int,
) -> dict[str, Any]:
    """Return UI policy for whether a new active speed test should be offered."""

    enabled = bool(config.get("enabled", True))
    min_interval_ms = max(0, int(config.get("minIntervalMinutes", 0)) * 60 * 1000)
    daily_run_limit = max(0, int(config.get("dailyRunLimit", 0)))
    last_tested_at = int(latest["testedAt"]) if latest else None
    if min_interval_ms > 0 and last_tested_at is not None:
        next_run_at = last_tested_at + min_interval_ms
        blocked_by_interval = now_ms < next_run_at
    else:
        next_run_at = None
        blocked_by_interval = False
    blocked_by_daily_limit = daily_run_limit > 0 and runs_last_day >= daily_run_limit
    can_run = enabled and not blocked_by_interval and not blocked_by_daily_limit

    return {
        "enabled": enabled,
        "provider": str(config.get("provider", "mlab-ndt7")),
        "providerName": str(config.get("providerName", "Measurement Lab NDT7")),
        "privacyUrl": str(config.get("privacyUrl", "https://www.measurementlab.net/privacy/")),
        "dataPolicyUrl": str(config.get("dataPolicyUrl", "https://www.measurementlab.net/privacy/")),
        "metadata": public_metadata(config.get("metadata", {})),
        "minIntervalMs": min_interval_ms,
        "dailyRunLimit": daily_run_limit,
        "runsLast24h": runs_last_day,
        "lastTestedAt": last_tested_at,
        "nextRunAt": next_run_at,
        "canRun": can_run,
    }


def public_metadata(value: object) -> dict[str, str]:
    """Return safe public NDT7 metadata for the browser client."""

    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(item)
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, (str, int, float, bool)) and len(str(key)) <= 64
    }


def optional_float(value: Any, name: str, min_value: float, max_value: float) -> float | None:
    """Return a bounded optional float."""

    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    if parsed < min_value or parsed > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return parsed


def optional_int(value: Any, name: str, min_value: int, max_value: int) -> int | None:
    """Return a bounded optional integer."""

    if value is None or value == "":
        return None
    return bounded_int(value, name, min_value, max_value)


def bounded_int(value: Any, name: str, min_value: int, max_value: int) -> int:
    """Return a required bounded integer."""

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer") from None
    if parsed < min_value or parsed > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return parsed


def bounded_text(value: Any, name: str, min_length: int, max_length: int) -> str:
    """Return a stripped string constrained by length."""

    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    parsed = value.strip()
    if len(parsed) < min_length or len(parsed) > max_length:
        raise ValueError(f"{name} must be between {min_length} and {max_length} characters")
    return parsed


def optional_text(value: Any, name: str, max_length: int) -> str | None:
    """Return a nullable stripped string constrained by length."""

    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    parsed = value.strip()
    if len(parsed) > max_length:
        raise ValueError(f"{name} must be at most {max_length} characters")
    return parsed or None
