import subprocess

import pytest

from netbox.models import Target
from netbox.ping import normalize_ping_error, parse_latency, ping_command, ping_target


def test_parse_latency_unix_output() -> None:
    output = "64 bytes from 1.1.1.1: icmp_seq=0 ttl=64 time=12.345 ms"
    assert parse_latency(output) == 12.345


def test_parse_latency_windows_output() -> None:
    output = "Minimum = 10ms, Maximum = 12ms, Average = 11ms"
    assert parse_latency(output) == 11


def test_normalize_ping_error() -> None:
    assert normalize_ping_error("100.0% packet loss") == "packet loss"
    assert normalize_ping_error("cannot resolve example") == "dns/resolve failed"
    assert normalize_ping_error("Request timeout for icmp_seq") == "timeout"


def test_ping_command_uses_argument_list() -> None:
    command = ping_command("1.1.1.1", 900)
    assert command[0] == "ping"
    assert "1.1.1.1" in command


def test_ping_target_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["ping"], 0, stdout="time=7.5 ms", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = ping_target(Target("loopback", "127.0.0.1", "Loopback", "gateway"), 900)

    assert result.ok is True
    assert result.latency_ms == 7.5


def test_ping_target_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(["ping"], 1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = ping_target(Target("loopback", "127.0.0.1", "Loopback", "gateway"), 900)

    assert result.ok is False
    assert result.error == "timeout"
