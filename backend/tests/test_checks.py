import socket
import urllib.request

import pytest

from netbox.core.models import PingResult, Target
from netbox.probes import checks


def test_http_check_matches_status_and_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    class FakeResponse:
        status = 200

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _limit: int) -> bytes:
            return b'{"status":"ok"}'

    def fake_urlopen(request: urllib.request.Request, *_args: object, **_kwargs: object) -> FakeResponse:
        captured["user_agent"] = request.headers.get("User-agent", "")
        captured["accept"] = request.headers.get("Accept", "")
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    target = Target(
        "api",
        "example.com",
        "Example API",
        "external",
        type="api",
        protocol="https",
        config={"url": "https://example.com/health", "expectedStatus": 200, "keyword": "ok"},
    )

    result = checks.run_http_check(target)

    assert result.ok is True
    assert result.protocol == "https"
    assert captured["user_agent"] == checks.DEFAULT_HTTP_HEADERS["User-Agent"]
    assert captured["accept"] == checks.DEFAULT_HTTP_HEADERS["Accept"]


def test_tcp_check_uses_configured_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSocket:
        def __enter__(self) -> "FakeSocket":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    seen: dict[str, object] = {}

    def fake_create_connection(address: tuple[str, int], timeout: float) -> FakeSocket:
        seen["address"] = address
        seen["timeout"] = timeout
        return FakeSocket()

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    target = Target(
        "tcp",
        "example.com:443",
        "TLS Port",
        "external",
        type="port",
        protocol="tcp",
        config={"host": "example.com", "port": 443},
    )

    result = checks.run_tcp_check(target)

    assert result.ok is True
    assert seen["address"] == ("example.com", 443)
    assert seen["timeout"] == 0.9


def test_dns_check_matches_expected_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks, "resolve_dns", lambda *_args: ["1.1.1.1"])
    target = Target(
        "dns",
        "example.com",
        "DNS",
        "external",
        type="dns",
        protocol="dns",
        config={"name": "example.com", "recordType": "A", "expectedValue": "1.1.1.1"},
    )

    result = checks.run_dns_check(target)

    assert result.ok is True
    assert result.protocol == "dns"


def test_run_check_delegates_icmp_to_safe_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_ping(target: Target, timeout_ms: int) -> PingResult:
        assert timeout_ms == 900
        return PingResult(target.id, target.host, target.label, target.scope, True, 1.5, 1_000, 2, None)

    monkeypatch.setattr(checks, "ping_target", fake_ping)
    target = Target("gateway", "127.0.0.1", "Gateway", "gateway", protocol="icmp")

    result = checks.run_check(target)

    assert result.ok is True
    assert result.protocol == "icmp"
