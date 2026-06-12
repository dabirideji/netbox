import threading
import time
from pathlib import Path

from netbox.core.models import MonitorConfig, NetworkIdentity, PingResult, Target
from netbox.monitor.scheduler import TargetScheduler
from netbox.monitor.state import MonitorState
from netbox.storage import StatusStore
from netbox.util.timeutils import now_ms


def config(db_path: str = ":memory:") -> MonitorConfig:
    return MonitorConfig(
        duration_ms=None,
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
        db_path=db_path,
    )


def test_scheduler_skips_disabled_targets() -> None:
    enabled = Target("up", "127.0.0.1", "Up", "gateway", interval_ms=250)
    disabled = Target("paused", "1.1.1.1", "Paused", "external", enabled=False, interval_ms=250)
    state = MonitorState(config(), [enabled, disabled], NetworkIdentity("Test", None, None, None), now_ms())
    calls: list[str] = []

    def checker(target: Target) -> PingResult:
        calls.append(target.id)
        return PingResult(target.id, target.host, target.label, target.scope, True, 1.0, now_ms(), 1, None)

    def stop_after_first(_summary: dict[str, object]) -> None:
        state.stopping.set()

    scheduler = TargetScheduler(state, max_workers=1, jitter_ratio=0, checker=checker)
    scheduler.run(now_ms() + 1_000, stop_after_first)

    assert calls == ["up"]


def test_scheduler_drains_checks_before_store_close(tmp_path: Path) -> None:
    target = Target("up", "127.0.0.1", "Up", "gateway", interval_ms=50)
    store = StatusStore(tmp_path / "status.sqlite3")
    store.seed_targets([target])
    state = MonitorState(
        config(str(tmp_path / "status.sqlite3")),
        [target],
        NetworkIdentity("Test", "wifi", "en0", "Wi-Fi"),
        now_ms(),
        store,
    )
    started = threading.Event()

    def checker(check_target: Target) -> PingResult:
        started.set()
        time.sleep(0.05)
        return PingResult(
            check_target.id,
            check_target.host,
            check_target.label,
            check_target.scope,
            True,
            1.0,
            now_ms(),
            1,
            None,
        )

    scheduler = TargetScheduler(state, max_workers=1, jitter_ratio=0, checker=checker)
    worker = threading.Thread(target=lambda: scheduler.run(now_ms() + 10_000, None))
    worker.start()
    assert started.wait(1)
    state.stopping.set()
    worker.join(2)
    assert not worker.is_alive()
    store.close()


def test_summarize_ignores_closed_store(tmp_path: Path) -> None:
    target = Target("up", "127.0.0.1", "Up", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    store.seed_targets([target])
    state = MonitorState(
        config(str(tmp_path / "status.sqlite3")),
        [target],
        NetworkIdentity("Test", "wifi", "en0", "Wi-Fi"),
        now_ms(),
        store,
    )

    store.close()

    summary = state._summarize()

    assert summary["targets"][0]["id"] == "up"


def test_scheduler_jitter_stays_within_ratio() -> None:
    target = Target("up", "127.0.0.1", "Up", "gateway", interval_ms=1_000)
    state = MonitorState(config(), [target], NetworkIdentity("Test", None, None, None), now_ms())
    scheduler = TargetScheduler(state, jitter_ratio=0.1)

    values = [scheduler._jitter_ms(target) for _ in range(50)]

    assert min(values) >= 0
    assert max(values) <= 100


def test_state_check_now_persists_result(monkeypatch, tmp_path: Path) -> None:
    target = Target("up", "127.0.0.1", "Up", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    store.seed_targets([target])
    state = MonitorState(
        config(str(tmp_path / "status.sqlite3")),
        [target],
        NetworkIdentity("Test", None, None, None),
        0,
        store,
    )

    def fake_run_check(check_target: Target) -> PingResult:
        return PingResult(
            check_target.id,
            check_target.host,
            check_target.label,
            check_target.scope,
            True,
            2.5,
            1_000,
            2,
            None,
        )

    monkeypatch.setattr("netbox.monitor.state.run_check", fake_run_check)

    try:
        response = state.check_now(target.id)
        results = store.target_results(target.id, limit=10)
    finally:
        store.close()

    assert response["result"]["ok"] is True
    assert results["total"] == 1


def test_state_preview_target_check_does_not_persist(monkeypatch, tmp_path: Path) -> None:
    target = Target("up", "127.0.0.1", "Up", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    store.seed_targets([target])
    state = MonitorState(
        config(str(tmp_path / "status.sqlite3")),
        [target],
        NetworkIdentity("Test", None, None, None),
        0,
        store,
    )

    def fake_run_check(check_target: Target) -> PingResult:
        return PingResult(
            check_target.id,
            check_target.host,
            check_target.label,
            check_target.scope,
            True,
            4.2,
            2_000,
            3,
            None,
        )

    monkeypatch.setattr("netbox.monitor.state.run_check", fake_run_check)

    try:
        response = state.preview_target_check(
            {
                "label": "Preview DNS",
                "type": "dns",
                "protocol": "dns",
                "scope": "external",
                "config": {"name": "example.com", "recordType": "A"},
            }
        )
        results = store.target_results(target.id, limit=10)
    finally:
        store.close()

    assert response["preview"] is True
    assert response["result"]["ok"] is True
    assert response["status"] == "operational"
    assert results["total"] == 0
