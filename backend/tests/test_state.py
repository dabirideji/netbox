from netbox.core.models import MonitorConfig, NetworkIdentity, Target
from netbox.monitor.state import MonitorState
from netbox.storage import StatusStore


def config() -> MonitorConfig:
    return MonitorConfig(
        duration_ms=10_000,
        interval_ms=1_000,
        timeout_ms=900,
        port=4177,
        host="127.0.0.1",
        latency_warn_ms=100,
        failures_to_degrade=1,
        failures_to_down=2,
        high_latency_to_degrade=1,
        recent_window=5,
        history_points=5,
        retention_points=10,
        no_clear=True,
        wifi_name="",
        db_path=":memory:",
    )


def sample(target: Target, ok: bool, latency: float | None, checked_at: int) -> dict[str, object]:
    return {
        "checkedAt": checked_at,
        "results": [
            {
                "id": target.id,
                "host": target.host,
                "label": target.label,
                "scope": target.scope,
                "ok": ok,
                "latencyMs": latency,
                "checkedAt": checked_at,
                "durationMs": 10,
                "error": None if ok else "timeout",
            }
        ],
    }


def test_state_appends_samples_and_broadcasts_status() -> None:
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)
    client = state.add_client()

    summary = state.append_sample(sample(target, True, 5, 1_000))

    assert summary["sampleCount"] == 1
    assert "status" in client.get_nowait()


def test_state_captures_status_change_events() -> None:
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)

    state.append_sample(sample(target, True, 5, 1_000))
    summary = state.append_sample(sample(target, False, None, 2_000))

    assert summary["events"][0]["targetLabel"] == "Loopback"
    assert summary["events"][0]["to"] == "degraded"


def test_state_sync_detected_network_updates_ssid(monkeypatch) -> None:
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(
        config(),
        [target],
        NetworkIdentity("Home", "Home", "en0", "Wi-Fi"),
        0,
    )
    state.append_sample(sample(target, True, 5, 1_000))

    monkeypatch.setattr(
        "netbox.monitor.state.detect_network_identity",
        lambda _override="": NetworkIdentity("Office", "Office", "en0", "Wi-Fi"),
    )

    assert state.sync_detected_network() is True
    assert state.snapshot()["network"]["ssid"] == "Office"


def test_state_refresh_network_identity_applies_interface_and_name() -> None:
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(
        config(),
        [target],
        NetworkIdentity("Home", "Home", "en0", "Wi-Fi"),
        0,
    )
    state.append_sample(sample(target, True, 5, 1_000))

    payload = state.refresh_network_identity("Office WiFi", "en0")

    assert payload["network"]["ssid"] == "Office WiFi"
    assert payload["network"]["interface"] == "en0"
    assert state.snapshot()["network"]["ssid"] == "Office WiFi"


def test_state_refresh_network_identity_applies_interface(monkeypatch) -> None:
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(
        config(),
        [target],
        NetworkIdentity("Wi-Fi (en0)", None, "en0", "Wi-Fi"),
        0,
    )
    state.append_sample(sample(target, True, 5, 1_000))

    monkeypatch.setattr(
        "netbox.monitor.state.detect_network_identity_for_interface",
        lambda interface, override="": NetworkIdentity("Office", "Office", interface, "Wi-Fi"),
    )

    payload = state.refresh_network_identity(interface="en0")

    assert payload["network"]["ssid"] == "Office"


def test_state_refresh_network_identity_applies_wifi_name() -> None:
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(
        config(),
        [target],
        NetworkIdentity("Wi-Fi (en0)", None, "en0", "Wi-Fi"),
        0,
    )
    state.append_sample(sample(target, True, 5, 1_000))

    payload = state.refresh_network_identity("Office WiFi")

    assert payload["network"]["ssid"] == "Office WiFi"
    assert state.snapshot()["network"]["ssid"] == "Office WiFi"


def test_state_persists_and_hydrates_status_events(tmp_path) -> None:
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)

    state.append_sample(sample(target, True, 5, 1_000))
    state.append_sample(sample(target, False, None, 2_000))
    store.close()

    next_store = StatusStore(tmp_path / "status.sqlite3")
    try:
        next_state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, next_store)
        snapshot = next_state.snapshot()
    finally:
        next_store.close()

    assert snapshot["events"][0]["targetLabel"] == "Loopback"
    assert snapshot["events"][0]["to"] == "degraded"


def test_snapshot_hydrates_last_reading_after_restart_without_memory_samples(tmp_path) -> None:
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    state.append_sample(sample(target, True, 23.5, 1_000))
    store.close()

    restarted_store = StatusStore(tmp_path / "status.sqlite3")
    try:
        restarted = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, restarted_store)
        snapshot = restarted.snapshot()
    finally:
        restarted_store.close()

    gateway_summary = snapshot["targets"][0]
    assert gateway_summary["lastLatencyMs"] == 23.5
    assert gateway_summary["lastCheckedAt"] == 1_000
    assert gateway_summary["lastOk"] is True
