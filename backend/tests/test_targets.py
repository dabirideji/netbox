from netbox.targets import default_interval_ms, default_timeout_ms, normalize_target_payload


def test_default_interval_ms_for_website_protocols() -> None:
    assert default_interval_ms("https") == 5_000
    assert default_interval_ms("http") == 5_000
    assert default_interval_ms("icmp") == 1_000


def test_normalize_target_payload_uses_protocol_defaults() -> None:
    website = normalize_target_payload(
        {
            "label": "Jobbox",
            "protocol": "https",
            "type": "website",
            "scope": "external",
            "config": {"url": "https://getjobbox.com", "expectedStatus": 200},
        }
    )
    ping = normalize_target_payload(
        {
            "label": "DNS",
            "protocol": "icmp",
            "scope": "external",
            "config": {"host": "1.1.1.1"},
        }
    )

    assert website.interval_ms == 5_000
    assert website.timeout_ms == 10_000
    assert ping.interval_ms == 1_000
    assert ping.timeout_ms == 900


def test_normalize_target_payload_respects_explicit_interval() -> None:
    target = normalize_target_payload(
        {
            "label": "Slow site",
            "protocol": "https",
            "type": "website",
            "scope": "external",
            "intervalMs": 30_000,
            "timeoutMs": 15_000,
            "config": {"url": "https://example.com", "expectedStatus": 200},
        }
    )

    assert target.interval_ms == 30_000
    assert target.timeout_ms == 15_000


def test_normalize_target_payload_defaults_api_health_path() -> None:
    target = normalize_target_payload(
        {
            "label": "JobBox API Health",
            "protocol": "https",
            "type": "api",
            "scope": "external",
            "config": {"url": "https://api.getjobbox.com", "expectedStatus": 200},
        }
    )

    assert target.config["url"] == "https://api.getjobbox.com/health"
    assert target.host == "api.getjobbox.com"


def test_normalize_target_payload_keeps_explicit_api_path() -> None:
    target = normalize_target_payload(
        {
            "label": "Custom API",
            "protocol": "https",
            "type": "api",
            "scope": "external",
            "config": {"url": "https://api.example.com/v1/status", "expectedStatus": 200},
        }
    )

    assert target.config["url"] == "https://api.example.com/v1/status"
