"""Thread-safe monitor state, persistence coordination, and SSE fanout."""

from __future__ import annotations

import json
import math
import queue
import threading
from typing import Any

from netbox.models import MonitorConfig, NetworkIdentity, Target
from netbox.speed import ONE_DAY_MS, normalize_speed_test, speed_policy
from netbox.storage import DEFAULT_STORAGE_CONFIG, StatusStore
from netbox.summary import capture_events, summarize
from netbox.timeutils import now_ms


class MonitorState:
    """Owns in-memory samples, persisted history access, and live clients."""

    def __init__(
        self,
        config: MonitorConfig,
        targets: list[Target],
        network: NetworkIdentity,
        started_at: int,
        store: StatusStore | None = None,
    ) -> None:
        self.config = config
        self.targets = targets
        self.network = network
        self.started_at = started_at
        self.store = store
        self.samples: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = store.recent_events(50)["events"] if store else []
        self.last_summary: dict[str, Any] | None = None
        self.clients: set[queue.Queue[str]] = set()
        self.lock = threading.RLock()
        self.stopping = threading.Event()

    def add_client(self) -> queue.Queue[str]:
        """Register an SSE client and immediately send the latest snapshot."""

        client: queue.Queue[str] = queue.Queue()
        with self.lock:
            self.clients.add(client)
            if self.last_summary:
                client.put(sse_payload({"type": "status", "summary": self.last_summary}))
        return client

    def remove_client(self, client: queue.Queue[str]) -> None:
        """Unregister an SSE client queue."""

        with self.lock:
            self.clients.discard(client)

    def broadcast(self, payload: dict[str, Any]) -> None:
        """Push one serialized SSE payload to all connected clients."""

        message = sse_payload(payload)
        with self.lock:
            clients = list(self.clients)
        for client in clients:
            client.put(message)

    def append_sample(self, sample: dict[str, Any]) -> dict[str, Any]:
        """Persist a sample, update summaries/events, and broadcast changes."""

        with self.lock:
            self.samples.append(sample)
            if self.store:
                self.store.record_sample(sample, self.config)
            max_samples = (
                math.ceil(self.config.duration_ms / self.config.interval_ms) + 10
                if self.config.duration_ms is not None
                else self.config.retention_points
            )
            if len(self.samples) > max_samples:
                self.samples = self.samples[-max_samples:]

            summary = self._summarize()
            event_count = len(self.events)
            capture_events(self.last_summary, summary, sample, self.events, self.broadcast)
            if self.store:
                self.store.record_events(self.events[event_count:])
            summary = self._summarize()
            self.last_summary = summary

        self.broadcast({"type": "status", "summary": summary})
        return summary

    def snapshot(self) -> dict[str, Any]:
        """Return the latest summary, creating an empty one if needed."""

        with self.lock:
            return self.last_summary or self._summarize()

    def history(
        self,
        points: int,
        from_ms: int | None = None,
        to_ms: int | None = None,
    ) -> dict[str, Any]:
        """Return persisted overview history for the requested time range."""

        if not self.store:
            return {"from": from_ms, "to": to_ms, "points": []}
        return self.store.history_overview(points, from_ms, to_ms)

    def persisted_events(
        self,
        limit: int,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return newest-first incident events with pagination metadata."""

        if not self.store:
            events = list(reversed(self.events))[offset : offset + limit]
            return {
                "from": from_ms,
                "to": to_ms,
                "limit": limit,
                "offset": offset,
                "total": len(self.events),
                "events": events,
            }
        return self.store.recent_events(limit, from_ms, to_ms, offset)

    def target_history(
        self,
        points: int,
        from_ms: int | None = None,
        to_ms: int | None = None,
    ) -> dict[str, Any]:
        """Return persisted per-target history for mini trend charts."""

        if not self.store:
            return {"from": from_ms, "to": to_ms, "targets": []}
        return self.store.target_history(points, from_ms, to_ms)

    def speed_tests(
        self,
        limit: int,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return speed-test history and current run policy."""

        policy = self.speed_test_policy()
        if not self.store:
            return {
                "from": from_ms,
                "to": to_ms,
                "limit": limit,
                "offset": offset,
                "total": 0,
                "stats": {
                    "avgDownloadMbps": None,
                    "avgUploadMbps": None,
                    "minLatencyMs": None,
                    "totalRuns": 0,
                    "completedRuns": 0,
                },
                "policy": policy,
                "tests": [],
            }

        result = self.store.recent_speed_tests(limit, from_ms, to_ms, offset)
        result["policy"] = policy
        return result

    def preferences(self) -> dict[str, Any]:
        """Return persisted UI preferences."""

        if not self.store:
            return {"data": {}}
        return {"data": self.store.get_preferences()}

    def update_preferences(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Merge UI preference updates into storage."""

        if not self.store:
            raise ValueError("preference storage is unavailable")
        data = self.store.update_preferences(payload)
        return {"data": data}

    def storage_stats(self) -> dict[str, Any]:
        """Return configured storage limits and current usage."""

        if not self.store:
            return empty_storage_stats(self.config.storage_config)
        return self.store.storage_stats()

    def clear_storage(self, scope: str) -> dict[str, Any]:
        """Manually clear one persisted log scope."""

        if not self.store:
            raise ValueError("log storage is unavailable")

        result = self.store.clear_storage(scope)
        if scope in {"incidents", "all"}:
            with self.lock:
                self.events = []
                if self.last_summary:
                    self.last_summary = {**self.last_summary, "events": []}
        return result

    def record_speed_test(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate, persist, and broadcast one browser-run speed test."""

        if not self.store:
            raise ValueError("speed test storage is unavailable")
        if not bool(self.config.speed_config.get("enabled", True)):
            raise ValueError("speed tests are disabled")

        normalized = normalize_speed_test(payload)
        with self.lock:
            test = self.store.record_speed_test(normalized)

        self.broadcast({"type": "speedTest", "test": test})
        return {"test": test, "policy": self.speed_test_policy()}

    def speed_test_policy(self) -> dict[str, Any]:
        """Return speed-test provider policy with local run limits."""

        current_time = now_ms()
        if not self.store:
            return speed_policy(self.config.speed_config, None, 0, current_time)

        latest = self.store.latest_speed_test()
        runs_last_day = self.store.count_speed_tests_since(current_time - ONE_DAY_MS)
        return speed_policy(self.config.speed_config, latest, runs_last_day, current_time)

    def _summarize(self) -> dict[str, Any]:
        """Build a summary from the currently retained in-memory samples."""

        return summarize(self.samples, self.targets, self.config, self.events, self.network, self.started_at)


def sse_payload(payload: dict[str, Any]) -> str:
    """Serialize a payload using the SSE `data:` frame format."""

    return f"data: {json.dumps(payload)}\n\n"


def empty_storage_stats(storage_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return zero usage stats using configured or default limits."""

    limits = DEFAULT_STORAGE_CONFIG["limits"].copy()
    config = storage_config or {}
    configured_limits = config.get("limits") if isinstance(config.get("limits"), dict) else {}
    for key in limits:
        if key in configured_limits:
            limits[key] = int(configured_limits[key])

    usage = {
        "databaseBytes": 0,
        "incidents": 0,
        "pingSamples": 0,
        "speedTests": 0,
    }
    return {
        "autoPrune": bool(config.get("autoPrune", DEFAULT_STORAGE_CONFIG["autoPrune"])),
        "limits": limits,
        "usage": usage,
        "percentUsed": {
            "database": 0.0,
            "incidents": 0.0,
            "pingSamples": 0.0,
            "speedTests": 0.0,
        },
    }
