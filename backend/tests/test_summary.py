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


def test_summarize_keeps_https_website_operational_at_expected_latency() -> None:
    website = Target(
        "jobbox-website",
        "getjobbox.com",
        "Jobbox",
        "external",
        type="website",
        protocol="https",
        config={"url": "https://getjobbox.com", "expectedStatus": 200},
    )
    samples = [
        {"checkedAt": 1_000, "results": [result(website, True, 850)]},
        {"checkedAt": 2_000, "results": [result(website, True, 920, 2_000)]},
        {"checkedAt": 3_000, "results": [result(website, True, 780, 3_000)]},
    ]

    summary = summarize(
        samples,
        [website],
        config(),
        [],
        NetworkIdentity("Office WiFi", "Office WiFi", "en0", "Wi-Fi"),
        0,
    )

    assert summary["targets"][0]["currentStatus"] == "operational"
    assert summary["targets"][0]["history"][-1]["status"] == "operational"
    assert summary["targets"][0]["reachabilityOnly"] is True
    assert summary["targets"][0]["latencyWarnMs"] is None


def test_reachability_target_is_down_on_failure_not_degraded() -> None:
    website = Target(
        "jobbox-website",
        "getjobbox.com",
        "Jobbox",
        "external",
        type="website",
        protocol="https",
        config={"url": "https://getjobbox.com", "expectedStatus": 200},
    )
    samples = [
        {"checkedAt": 1_000, "results": [result(website, True, 850)]},
        {"checkedAt": 2_000, "results": [result(website, False, None, 2_000)]},
    ]

    summary = summarize(
        samples,
        [website],
        config(),
        [],
        NetworkIdentity("Office WiFi", "Office WiFi", "en0", "Wi-Fi"),
        0,
    )

    assert summary["targets"][0]["currentStatus"] == "down"
    assert summary["targets"][0]["history"][-1]["status"] == "down"


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
