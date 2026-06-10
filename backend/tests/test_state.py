from netbox.models import MonitorConfig, NetworkIdentity, Target
from netbox.state import MonitorState
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
