"""Input validation for CLI, bind address, and target configuration."""

from __future__ import annotations

import ipaddress
import re

from netbox.models import Scope, Target

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)
LABEL_RE = re.compile(r"^[\w .@()/_-]{1,48}$", re.UNICODE)
HOST_BIND_ALLOWLIST = {"127.0.0.1", "localhost", "0.0.0.0"}
VALID_SCOPES: set[str] = {"gateway", "external"}


def validate_port(value: int) -> int:
    """Validate a TCP port number."""

    if not 1 <= value <= 65_535:
        raise ValueError("port must be between 1 and 65535")
    return value


def validate_bind_host(value: str, allowed_hosts: list[str] | None = None) -> str:
    """Restrict bind hosts to explicit local/development-safe values."""

    hosts = set(allowed_hosts or HOST_BIND_ALLOWLIST)
    if value not in hosts:
        raise ValueError(f"host must be one of {', '.join(sorted(hosts))}")
    return value


def validate_host(value: str) -> str:
    """Validate a target host as an IP address or DNS name."""

    host = value.strip()
    if not host or len(host) > 253 or any(char.isspace() for char in host):
        raise ValueError("target host is invalid")

    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass

    if DOMAIN_RE.match(host):
        return host.rstrip(".")

    raise ValueError(f"invalid target host: {value}")


def validate_label(value: str) -> str:
    """Validate a compact display label for a target."""

    label = value.strip()
    if not LABEL_RE.match(label):
        raise ValueError("target label may only contain letters, numbers, spaces, dots, @, (), /, _, and -")
    return label


def validate_scope(value: str) -> Scope:
    """Validate the target scope used for diagnosis logic."""

    scope = value.strip().lower()
    if scope not in VALID_SCOPES:
        raise ValueError("target scope must be gateway or external")
    return scope  # type: ignore[return-value]


def parse_target_arg(value: str, index: int) -> Target:
    """Parse `host:label:scope` CLI input into a target model."""

    parts = value.split(":")
    host = validate_host(parts[0])
    label = validate_label(parts[1]) if len(parts) > 1 and parts[1] else host
    scope = validate_scope(parts[2]) if len(parts) > 2 and parts[2] else "external"
    return Target(slug(f"{label}-{host}-{index}"), host, label, scope)


def slug(value: str) -> str:
    """Return a stable lowercase identifier for a target."""

    slugged = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slugged or "target"
