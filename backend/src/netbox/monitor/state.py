"""Thread-safe monitor state, persistence coordination, and SSE fanout."""

from __future__ import annotations

import json
import math
import queue
import threading
from dataclasses import asdict
from typing import Any

from netbox.alerts import dispatch_ongoing_alerts, dispatch_target_alerts, smtp_settings_to_api, target_alert_to_api
from netbox.alerts.platform import platform_settings_to_api
from netbox.alerts.smtp_client import build_alert_email, send_alert_email
from netbox.probes.checks import run_check
from netbox.core.models import MonitorConfig, NetworkIdentity, Target
from netbox.probes.network import (
    clean_network_name,
    detect_default_gateway,
    detect_network_identity,
    detect_network_identity_for_interface,
    list_network_interfaces,
    network_identity_should_sync,
)
from netbox.core.responses import monitor_status_severity
from netbox.monitor.speed import ONE_DAY_MS, normalize_speed_test, speed_policy
from netbox.storage import DEFAULT_STORAGE_CONFIG, StatusStore
from netbox.monitor.summary import capture_events, latency_warn_ms_for, status_for_result, summarize
from netbox.targets import gateway_host_sync_payload, normalize_target_payload, target_to_api
from netbox.util.macos import detect_location_client
from netbox.util.timeutils import now_ms


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
            new_events: list[dict[str, Any]] = []
            if self.store:
                new_events = self.events[event_count:]
                self.store.record_events(new_events)
                self.store.record_incident_events(new_events)
                self._dispatch_alerts(new_events)
            summary = self._summarize()
            self.last_summary = summary

        self.broadcast({"type": "status", "summary": summary})
        return summary

    def list_network_interfaces(self) -> dict[str, Any]:
        """Return selectable local network interfaces."""

        return {"interfaces": list_network_interfaces()}

    def refresh_network_identity(
        self,
        wifi_name: str | None = None,
        interface: str | None = None,
    ) -> dict[str, Any]:
        """Re-detect or apply a Wi-Fi name and broadcast an updated status snapshot."""

        with self.lock:
            if wifi_name:
                cleaned = clean_network_name(wifi_name)
                if cleaned:
                    current_interface = interface or self.network.interface
                    current_service = self.network.service
                    if current_interface:
                        detected = detect_network_identity_for_interface(current_interface, cleaned)
                        current_service = detected.service
                    self.network = NetworkIdentity(
                        name=cleaned,
                        ssid=cleaned,
                        interface=current_interface,
                        service=current_service,
                    )
            elif interface:
                self.network = detect_network_identity_for_interface(interface, self.config.wifi_name)
            else:
                self.network = detect_network_identity(self.config.wifi_name)

            summary = (
                {**self.last_summary, "network": asdict(self.network)}
                if self.last_summary
                else self._summarize()
            )
            self.last_summary = summary

        self.broadcast({"type": "status", "summary": summary})
        return {"network": asdict(self.network), "locationClient": detect_location_client()}

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

    def list_targets(self) -> dict[str, Any]:
        """Return all configured monitoring targets."""

        return {"targets": [target_to_api(target) for target in self.current_targets()]}

    def get_target(self, target_id: str) -> dict[str, Any]:
        """Return one configured monitoring target."""

        target = self._require_store().get_target(target_id)
        if not target:
            raise ValueError("target was not found")
        return {"target": target_to_api(target)}

    def create_target(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create one target and broadcast the updated target list."""

        store = self._require_store()
        target = store.create_target(payload)
        self.reload_targets()
        self.broadcast({"type": "targets", **self.list_targets()})
        return {"target": target_to_api(target)}

    def update_target(self, target_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update one target and broadcast the updated target list."""

        store = self._require_store()
        target = store.update_target(target_id, payload)
        self.reload_targets()
        targets_response = self.list_targets()
        with self.lock:
            summary = self._summarize()
            self.last_summary = summary
            self.broadcast({"type": "status", "summary": summary})
        self.broadcast({"type": "targets", **targets_response})
        return {"target": target_to_api(target)}

    def delete_target(self, target_id: str) -> dict[str, Any]:
        """Delete one target and broadcast the updated target list."""

        deleted = self._require_store().delete_target(target_id)
        if not deleted:
            raise ValueError("target was not found")
        self.reload_targets()
        self.broadcast({"type": "targets", **self.list_targets()})
        return {"deleted": True}

    def set_target_favorite(self, target_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Pin or unpin one target at the top of live checks."""

        favorite = payload.get("favorite")
        if not isinstance(favorite, bool):
            raise ValueError("favorite must be a boolean")

        store = self._require_store()
        target = store.set_target_favorite(target_id, favorite)
        self.reload_targets()
        targets_response = self.list_targets()
        self.broadcast({"type": "targets", **targets_response})
        with self.lock:
            summary = self._summarize()
            self.last_summary = summary
            self.broadcast({"type": "status", "summary": summary})
        return {"target": target_to_api(target)}

    def reorder_targets(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist a new target display order and broadcast the updated list."""

        order = payload.get("order")
        if not isinstance(order, list) or not all(isinstance(item, str) for item in order):
            raise ValueError("order must be an array of target ids")

        store = self._require_store()
        store.reorder_targets(order)
        self.reload_targets()
        response = self.list_targets()
        self.broadcast({"type": "targets", **response})
        return response

    def check_now(self, target_id: str) -> dict[str, Any]:
        """Run one immediate check and append it to persisted history."""

        target = self._require_store().get_target(target_id)
        if not target:
            raise ValueError("target was not found")
        result = run_check(target).to_dict()
        summary = self.append_sample({"checkedAt": result["checkedAt"], "results": [result]})
        return {"result": result, "summary": summary}

    def preview_target_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run one immediate check from an unsaved target payload without persisting it."""

        target = normalize_target_payload(payload, index=len(self.current_targets()))
        result = run_check(target).to_dict()
        status = status_for_result(result, latency_warn_ms_for(target, self.config), target)
        return {
            "preview": True,
            "result": result,
            "status": status,
            "severity": monitor_status_severity(status),
        }

    def target_results(
        self,
        target_id: str,
        limit: int,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return persisted check results for one target."""

        if not self._require_store().get_target(target_id):
            raise ValueError("target was not found")
        return self._require_store().target_results(target_id, limit, from_ms, to_ms, offset)

    def incidents(
        self,
        limit: int,
        from_ms: int | None = None,
        to_ms: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return durable incident windows."""

        return self._require_store().recent_incidents(limit, from_ms, to_ms, offset)

    def active_targets(self) -> list[Target]:
        """Return enabled targets for scheduler execution."""

        return [target for target in self.current_targets() if target.enabled]

    def current_targets(self) -> list[Target]:
        """Return the current target list, preferring SQLite when available."""

        if self.store:
            with self.lock:
                self.targets = self.store.list_targets()
        return list(self.targets)

    def reload_targets(self) -> None:
        """Refresh in-memory targets from storage."""

        if self.store:
            with self.lock:
                self.targets = self.store.list_targets()

    def sync_detected_network(self) -> bool:
        """Refresh network identity when the active interface or SSID changes."""

        detected = detect_network_identity(self.config.wifi_name)

        with self.lock:
            if not network_identity_should_sync(self.network, detected):
                return False

            self.network = detected
            summary = (
                {**self.last_summary, "network": asdict(self.network)}
                if self.last_summary
                else self._summarize()
            )
            self.last_summary = summary

        self.broadcast({"type": "status", "summary": summary})
        return True

    def sync_detected_gateway(self) -> bool:
        """Refresh the auto-detected gateway target when the default route changes."""

        if self.config.target_args or not self.store:
            return False

        gateway = detect_default_gateway()
        if not gateway:
            return False

        store = self.store
        existing = store.get_target("gateway")
        sync_payload = gateway_host_sync_payload(existing, gateway)
        if sync_payload is None:
            return False

        self.update_target("gateway", sync_payload)
        return True

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

    def storage_settings(self) -> dict[str, Any]:
        """Return persisted storage retention settings."""

        if not self.store:
            from netbox.storage.config import normalize_storage_config
            from netbox.storage.settings import storage_settings_to_api

            config = normalize_storage_config(self.config.storage_config)
            return {"settings": storage_settings_to_api(config)}
        return {"settings": self.store.get_storage_settings()}

    def update_storage_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist storage retention settings and return updated stats."""

        if not self.store:
            raise ValueError("log storage is unavailable")

        settings = self.store.update_storage_settings(payload)
        return {"settings": settings, "stats": self.store.storage_stats()}

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

    def platform_settings(self) -> dict[str, Any]:
        """Return persisted platform-wide settings."""

        store = self._require_store()
        return {"settings": platform_settings_to_api(store.get_platform_settings())}

    def update_platform_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist platform-wide settings."""

        store = self._require_store()
        settings = store.update_platform_settings(payload)
        return {"settings": platform_settings_to_api(settings)}

    def smtp_settings(self) -> dict[str, Any]:
        """Return configured SMTP settings without exposing stored secrets."""

        store = self._require_store()
        return {"smtp": smtp_settings_to_api(store.get_smtp_settings())}

    def update_smtp_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist SMTP provider settings with encrypted credentials."""

        store = self._require_store()
        settings = store.update_smtp_settings(payload)
        return {"smtp": smtp_settings_to_api(settings)}

    def test_smtp_settings(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send one test email using stored or draft SMTP settings."""

        from netbox.alerts.models import normalize_smtp_payload

        store = self._require_store()
        current = store.get_smtp_settings()
        draft = payload if isinstance(payload, dict) else {}
        merged = {
            "provider": draft.get("provider", current["provider"]),
            "host": draft.get("host", current["host"]),
            "port": draft.get("port", current["port"]),
            "username": draft.get("username", current["username"]),
            "fromEmail": draft.get("fromEmail", current["fromEmail"]),
            "fromName": draft.get("fromName", current["fromName"]),
            "useTls": draft.get("useTls", current["useTls"]),
            "password": draft.get("password"),
        }
        normalized = normalize_smtp_payload(merged)
        password = normalized.get("password") or store.get_smtp_password()
        if not password:
            raise ValueError("password is required")

        settings = {
            "provider": normalized["provider"],
            "host": normalized["host"],
            "port": normalized["port"],
            "username": normalized["username"],
            "fromEmail": normalized["fromEmail"],
            "fromName": normalized["fromName"],
            "useTls": normalized["useTls"],
            "configured": True,
        }

        recipient = str(draft.get("testEmail") or settings["fromEmail"]).strip()
        if not recipient:
            raise ValueError("testEmail is required")

        subject, body, html_body = build_alert_email(
            {
                "targetLabel": "SMTP test",
                "from": "operational",
                "to": "degraded",
                "message": "This is a test alert from Netbox.",
            }
        )
        send_alert_email(
            settings,
            password=password,
            to_email=recipient,
            subject=subject,
            body=body,
            html_body=html_body,
        )
        return {"ok": True, "message": f"Test email sent to {recipient}"}

    def target_alert(self, target_id: str) -> dict[str, Any]:
        """Return alert rules configured for one target."""

        store = self._require_store()
        rules = store.get_target_alert(target_id)
        smtp_configured = store.get_smtp_settings()["configured"]
        return {"alert": target_alert_to_api(target_id, rules, smtp_configured=smtp_configured)}

    def update_target_alert(self, target_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist alert rules for one target."""

        store = self._require_store()
        rules = store.update_target_alert(target_id, payload)
        smtp_configured = store.get_smtp_settings()["configured"]
        return {"alert": target_alert_to_api(target_id, rules, smtp_configured=smtp_configured)}

    def tick_alerts(self) -> None:
        """Evaluate persisted alert schedules on a wall-clock tick."""

        if not self.store:
            return

        with self.lock:
            summary = self.last_summary or self._summarize()

        dispatch_ongoing_alerts(
            summary,
            get_rules=self.store.get_target_alert,
            smtp_settings=self._smtp_settings(),
            smtp_password=self._smtp_password(),
            dispatch_store=self.store,
            broadcast=self.broadcast,
        )

    def _dispatch_alerts(self, events: list[dict[str, Any]]) -> None:
        """Emit configured alert channels for new status transition events."""

        if not self.store or not events:
            return

        dispatch_target_alerts(
            events,
            get_rules=self.store.get_target_alert,
            smtp_settings=self._smtp_settings(),
            smtp_password=self._smtp_password(),
            dispatch_store=self.store,
            broadcast=self.broadcast,
        )

    def _smtp_settings(self) -> dict[str, Any] | None:
        if not self.store:
            return None
        return self.store.get_smtp_settings()

    def _smtp_password(self) -> str:
        settings = self._smtp_settings()
        if not settings or not settings["configured"]:
            return ""
        return self.store.get_smtp_password()

    def _summarize(self) -> dict[str, Any]:
        """Build a summary from the currently retained in-memory samples."""

        persisted_latest = self.store.latest_check_results_by_target() if self.store else None
        return summarize(
            self.samples,
            self.targets,
            self.config,
            self.events,
            self.network,
            self.started_at,
            persisted_latest,
        )

    def _require_store(self) -> StatusStore:
        """Return the persistence gateway or fail for storage-backed APIs."""

        if not self.store:
            raise ValueError("target storage is unavailable")
        return self.store


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
