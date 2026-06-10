"""Shared data models for monitor configuration, targets, and ping results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["operational", "degraded", "down", "unknown"]
Scope = Literal["gateway", "external"]


@dataclass(frozen=True)
class Target:
    """A network endpoint checked by the monitor."""

    id: str
    host: str
    label: str
    scope: Scope


@dataclass(frozen=True)
class NetworkIdentity:
    """Best-effort description of the active local network."""

    name: str
    ssid: str | None
    interface: str | None
    service: str | None


@dataclass(frozen=True)
class MonitorConfig:
    """Validated runtime settings used by the monitor loop and API server."""

    duration_ms: int | None
    interval_ms: int
    timeout_ms: int
    port: int
    host: str
    latency_warn_ms: float
    failures_to_degrade: int
    failures_to_down: int
    high_latency_to_degrade: int
    recent_window: int
    history_points: int
    retention_points: int
    no_clear: bool
    wifi_name: str
    db_path: str
    target_args: list[str] = field(default_factory=list)
    default_target_args: list[str] = field(default_factory=list)
    security_headers: dict[str, str] = field(default_factory=dict)
    speed_config: dict[str, object] = field(default_factory=dict)
    storage_config: dict[str, object] = field(default_factory=dict)
    static_dir: str | None = None


@dataclass(frozen=True)
class PingResult:
    """Normalized result from one ping check against one target."""

    id: str
    host: str
    label: str
    scope: Scope
    ok: bool
    latency_ms: float | None
    checked_at: int
    duration_ms: int
    error: str | None

    def to_dict(self) -> dict[str, object]:
        """Return the JSON/API representation used by state and storage."""

        return {
            "id": self.id,
            "host": self.host,
            "label": self.label,
            "scope": self.scope,
            "ok": self.ok,
            "latencyMs": self.latency_ms,
            "checkedAt": self.checked_at,
            "durationMs": self.duration_ms,
            "error": self.error,
        }
