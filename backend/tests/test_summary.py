from netbox.models import MonitorConfig, NetworkIdentity, Target
from netbox.summary import summarize


def config() -> MonitorConfig:
    return MonitorConfig(
        duration_ms=120_000,
        interval_ms=1_000,
        timeout_ms=900,
        port=4177,
        host="127.0.0.1",
        latency_warn_ms=150,
        failures_to_degrade=1,
        failures_to_down=3,
        high_latency_to_degrade=2,
        recent_window=5,
        history_points=10,
        retention_points=100,
        no_clear=True,
        wifi_name="",
        db_path=":memory:",
    )


def result(target: Target, ok: bool, latency: float | None, checked_at: int = 1_000) -> dict[str, object]:
    return {
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


def test_summarize_identifies_external_degradation() -> None:
    gateway = Target("gateway", "192.168.1.1", "Gateway", "gateway")
    external = Target("dns", "1.1.1.1", "DNS", "external")
    samples = [
        {"checkedAt": 1_000, "results": [result(gateway, True, 5), result(external, True, 200)]},
        {"checkedAt": 2_000, "results": [result(gateway, True, 5, 2_000), result(external, True, 220, 2_000)]},
    ]

    summary = summarize(
        samples,
        [gateway, external],
        config(),
        [],
        NetworkIdentity("Office WiFi", "Office WiFi", "en0", "Wi-Fi"),
        0,
    )

    assert summary["overallStatus"] == "degraded"
    assert summary["targets"][1]["currentStatus"] == "degraded"
    assert summary["targets"][1]["history"][-1]["status"] == "degraded"


def test_summarize_identifies_gateway_down() -> None:
    gateway = Target("gateway", "192.168.1.1", "Gateway", "gateway")
    samples = [
        {"checkedAt": 1_000, "results": [result(gateway, False, None, 1_000)]},
        {"checkedAt": 2_000, "results": [result(gateway, False, None, 2_000)]},
        {"checkedAt": 3_000, "results": [result(gateway, False, None, 3_000)]},
    ]

    summary = summarize(samples, [gateway], config(), [], NetworkIdentity("LAN", None, "en0", "Wi-Fi"), 0)

    assert summary["overallStatus"] == "down"
    assert "Local gateway is unreachable" in summary["diagnosis"]
