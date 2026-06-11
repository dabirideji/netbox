"""Status aggregation, diagnosis, history bars, and incident event capture."""

from __future__ import annotations

import statistics
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from netbox.models import MonitorConfig, NetworkIdentity, Target
from netbox.responses import Status
from netbox.timeutils import now_ms

HTTPS_LATENCY_WARN_MS = 3_000.0
REACHABILITY_PROTOCOLS = frozenset({"http", "https", "tcp"})


def summarize(
    samples: list[dict[str, Any]],
    targets: list[Target],
    config: MonitorConfig,
    events: list[dict[str, Any]],
    network: NetworkIdentity,
    started_at: int,
) -> dict[str, Any]:
    """Build the API/UI summary from retained samples and target config."""

    target_summaries = []

    for target in targets:
        results = [find_result(sample["results"], target.id) for sample in samples]
        results = [result for result in results if result is not None]
        successful = [result for result in results if result["ok"]]
        failed = len(results) - len(successful)
        latencies = [result["latencyMs"] for result in successful if result["latencyMs"] is not None]
        recent = results[-1] if results else None
        recent_window = results[-config.recent_window :]
        reachability = is_reachability_check(target)
        latency_warn_ms = None if reachability else latency_warn_ms_for(target, config)
        recent_failures = len([result for result in recent_window if not result["ok"]])
        recent_high_latency = 0 if reachability else len(
            [
                result
                for result in recent_window
                if result["ok"]
                and result["latencyMs"] is not None
                and result["latencyMs"] >= latency_warn_ms_for(target, config)
            ]
        )
        current_status = get_current_status(
            recent,
            recent_failures,
            recent_high_latency,
            config,
            target,
        )

        target_summaries.append(
            {
                "id": target.id,
                "host": target.host,
                "label": target.label,
                "scope": target.scope,
                "type": target.type,
                "protocol": target.protocol,
                "group": target.group,
                "environment": target.environment,
                "enabled": target.enabled,
                "isFavorite": target.is_favorite,
                "intervalMs": target.interval_ms,
                "timeoutMs": target.timeout_ms,
                "latencyWarnMs": None if reachability else latency_warn_ms,
                "reachabilityOnly": reachability,
                "config": target.config,
                "currentStatus": current_status,
                "lastOk": bool(recent and recent["ok"]),
                "lastLatencyMs": recent["latencyMs"] if recent else None,
                "lastCheckedAt": recent["checkedAt"] if recent else None,
                "lastError": recent["error"] if recent else None,
                "activeIncident": active_incident_for(target.id, events),
                "samples": len(results),
                "uptimePct": pct(len(successful), len(results)),
                "packetLossPct": pct(failed, len(results)),
                "avgLatencyMs": average(latencies),
                "minLatencyMs": min(latencies) if latencies else None,
                "maxLatencyMs": max(latencies) if latencies else None,
                "jitterMs": jitter(latencies),
                "recentFailures": recent_failures,
                "recentHighLatency": recent_high_latency,
                "history": build_history(results, target, config),
            }
        )

    overall_status, diagnosis = diagnose(target_summaries)

    return {
        "startedAt": started_at,
        "now": now_ms(),
        "endsAt": started_at + config.duration_ms if config.duration_ms is not None else None,
        "intervalMs": config.interval_ms,
        "durationMs": config.duration_ms,
        "overallStatus": overall_status,
        "diagnosis": diagnosis,
        "network": asdict(network),
        "targets": target_summaries,
        "events": events[-50:],
        "sampleCount": len(samples),
        "thresholds": {
            "timeoutMs": config.timeout_ms,
            "latencyWarnMs": config.latency_warn_ms,
            "failuresToDegrade": config.failures_to_degrade,
            "failuresToDown": config.failures_to_down,
            "retentionPoints": config.retention_points,
        },
    }


def diagnose(target_summaries: list[dict[str, Any]]) -> tuple[Status, str]:
    """Classify the incident as local-network or upstream when possible."""

    gateway = next((target for target in target_summaries if target["scope"] == "gateway"), None)
    externals = [target for target in target_summaries if target["scope"] == "external"]
    external_down = bool(externals) and all(target["currentStatus"] == "down" for target in externals)
    external_has_down = any(target["currentStatus"] == "down" for target in externals)
    external_degraded = any(target["currentStatus"] == "degraded" for target in externals)
    gateway_down = bool(gateway and gateway["currentStatus"] == "down")
    gateway_degraded = bool(gateway and gateway["currentStatus"] != "operational")

    if gateway_down:
        return "down", "Local gateway is unreachable. Wi‑Fi/router/local LAN is likely unstable."
    if gateway_degraded:
        return "degraded", "Local gateway is degraded. Watch router/Wi‑Fi latency or packet loss."
    if external_down:
        return "down", "Gateway is reachable, but internet targets are down. ISP/upstream may be unstable."
    if external_has_down:
        return "down", "Gateway is healthy, but one or more internet targets are unreachable."
    if external_degraded:
        return "degraded", "Gateway is healthy, but external targets are degraded. Likely upstream/ISP jitter."
    return "operational", "Local network looks steady."


def get_current_status(
    recent: dict[str, Any] | None,
    recent_failures: int,
    recent_high_latency: int,
    config: MonitorConfig,
    target: Target,
) -> Status:
    """Convert recent failures/high-latency counts into a target status."""

    if not recent:
        return "unknown"
    if is_reachability_check(target):
        if recent_failures >= config.failures_to_down:
            return "down"
        return "operational" if recent["ok"] else "down"
    if recent_failures >= config.failures_to_down:
        return "down"
    if recent_failures >= config.failures_to_degrade:
        return "degraded"
    if recent_high_latency >= config.high_latency_to_degrade:
        return "degraded"
    return "operational" if recent["ok"] else "degraded"


def build_history(results: list[dict[str, Any]], target: Target, config: MonitorConfig) -> list[dict[str, Any]]:
    """Build the compact in-memory status history shown beside each target."""

    latency_warn_ms = latency_warn_ms_for(target, config)
    recent_results = results[-config.history_points :]
    return [
        {
            "at": result["checkedAt"],
            "status": status_for_result(result, latency_warn_ms, target),
            "latencyMs": result["latencyMs"],
            "error": result["error"],
        }
        for result in recent_results
    ]


def status_for_result(result: dict[str, Any], latency_warn_ms: float, target: Target) -> Status:
    """Classify a single check result using success and optional latency thresholds."""

    if not result["ok"]:
        return "down"
    if is_reachability_check(target):
        return "operational"
    if result["latencyMs"] is not None and result["latencyMs"] >= latency_warn_ms:
        return "degraded"
    return "operational"


def is_reachability_check(target: Target) -> bool:
    """Return True when a target should only be up or down, never latency-degraded."""

    return target.protocol in REACHABILITY_PROTOCOLS


def latency_warn_ms_for(target: Target, config: MonitorConfig) -> float:
    """Return the latency threshold used to classify one target as degraded."""

    raw = target.config.get("latencyWarnMs")
    if raw is not None:
        return float(raw)
    if target.protocol in {"http", "https"}:
        return HTTPS_LATENCY_WARN_MS
    return config.latency_warn_ms


def capture_events(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    sample: dict[str, Any],
    events: list[dict[str, Any]],
    broadcast: Callable[[dict[str, Any]], None],
) -> None:
    """Detect target status transitions and broadcast incident events."""

    if not previous:
        return

    for target in current["targets"]:
        old_target = next(
            (candidate for candidate in previous["targets"] if candidate["id"] == target["id"]),
            None,
        )
        if not old_target or old_target["currentStatus"] == target["currentStatus"]:
            continue

        event = {
            "at": sample["checkedAt"],
            "targetId": target["id"],
            "targetLabel": target["label"],
            "from": old_target["currentStatus"],
            "to": target["currentStatus"],
            "message": f"{target['label']} changed from {old_target['currentStatus']} to {target['currentStatus']}",
        }
        events.append(event)
        broadcast({"type": "event", "event": event})


def find_result(results: list[dict[str, Any]], target_id: str) -> dict[str, Any] | None:
    """Return the result for one target from a sample result list."""

    return next((result for result in results if result["id"] == target_id), None)


def active_incident_for(target_id: str, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the latest unresolved in-memory incident event for one target."""

    for event in reversed(events):
        if event["targetId"] != target_id:
            continue
        if event["to"] == "operational":
            return None
        return event
    return None


def average(values: list[float]) -> float | None:
    """Return the arithmetic mean for non-empty values."""

    return statistics.fmean(values) if values else None


def jitter(values: list[float]) -> float | None:
    """Return mean absolute delta between consecutive latency values."""

    if len(values) < 2:
        return None
    deltas = [abs(values[index] - values[index - 1]) for index in range(1, len(values))]
    return statistics.fmean(deltas)


def pct(part: int, total: int) -> float:
    """Return `part / total` as a percentage, guarding zero totals."""

    return (part / total) * 100 if total else 0
