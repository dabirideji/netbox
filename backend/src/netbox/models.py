"""Shared data models for monitor configuration, targets, and ping results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Scope = Literal["gateway", "external"]
TargetType = Literal["website", "api", "host", "port", "dns"]
TargetProtocol = Literal["http", "https", "tcp", "icmp", "dns"]


@dataclass(frozen=True)
class Target:
    """A network endpoint checked by the monitor."""

    id: str
    host: str
    label: str
    scope: Scope
    type: TargetType = "host"
    protocol: TargetProtocol = "icmp"
    group: str = "Default"
    environment: str = "local"
    enabled: bool = True
    interval_ms: int = 1_000
    timeout_ms: int = 900
    config: dict[str, Any] = field(default_factory=dict)
    sort_order: int = 0
    is_favorite: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return the API representation used by CRUD endpoints."""

        return {
            "id": self.id,
            "host": self.host,
            "label": self.label,
            "scope": self.scope,
            "type": self.type,
            "protocol": self.protocol,
            "group": self.group,
            "environment": self.environment,
            "enabled": self.enabled,
            "intervalMs": self.interval_ms,
            "timeoutMs": self.timeout_ms,
            "config": self.config,
            "sortOrder": self.sort_order,
            "isFavorite": self.is_favorite,
        }


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
    default_target_seeds: list[dict[str, Any]] = field(default_factory=list)
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
    type: TargetType = "host"
    protocol: TargetProtocol = "icmp"

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
            "type": self.type,
            "protocol": self.protocol,
        }
