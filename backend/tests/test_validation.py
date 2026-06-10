import pytest

from netbox.validation import (
    parse_target_arg,
    validate_bind_host,
    validate_host,
    validate_port,
)


def test_parse_target_arg_validates_and_normalizes() -> None:
    target = parse_target_arg("192.168.1.1:Router:gateway", 0)

    assert target.host == "192.168.1.1"
    assert target.label == "Router"
    assert target.scope == "gateway"
    assert target.id == "router-192-168-1-1-0"


def test_validate_host_accepts_domains_and_ips() -> None:
    assert validate_host("1.1.1.1") == "1.1.1.1"
    assert validate_host("example.com") == "example.com"


def test_validate_host_rejects_command_like_input() -> None:
    with pytest.raises(ValueError):
        validate_host("1.1.1.1; rm -rf /")


def test_validate_scope_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        parse_target_arg("1.1.1.1:DNS:internal", 0)


def test_validate_port_and_bind_host() -> None:
    assert validate_port(4177) == 4177
    assert validate_bind_host("127.0.0.1") == "127.0.0.1"

    with pytest.raises(ValueError):
        validate_port(70_000)

    with pytest.raises(ValueError):
        validate_bind_host("example.com")
