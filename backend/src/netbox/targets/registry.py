"""Target validation, normalization, and seed helpers for configurable monitoring."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse, urlunparse

from netbox.core.models import Target, TargetProtocol, TargetType
from netbox.util.timeutils import parse_duration
from netbox.util.http_headers import validate_http_headers
from netbox.util.validation import slug, validate_host, validate_label, validate_port, validate_scope

VALID_TARGET_TYPES: set[str] = {"website", "api", "host", "port", "dns"}
VALID_PROTOCOLS: set[str] = {"http", "https", "tcp", "icmp", "dns"}
VALID_DNS_RECORDS = {"A", "AAAA", "CNAME", "MX", "TXT", "NS"}
GROUP_RE = re.compile(r"^[\w .@()/_-]{1,64}$", re.UNICODE)
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

DEFAULT_INTERVAL_MS_BY_PROTOCOL: dict[TargetProtocol, int] = {
    "icmp": 1_000,
    "dns": 5_000,
    "http": 5_000,
    "https": 5_000,
    "tcp": 5_000,
}

DEFAULT_TIMEOUT_MS_BY_PROTOCOL: dict[TargetProtocol, int] = {
    "icmp": 900,
    "dns": 3_000,
    "http": 10_000,
    "https": 10_000,
    "tcp": 5_000,
}


def normalize_target_payload(
    payload: dict[str, Any],
    *,
    existing: Target | None = None,
    index: int = 0,
) -> Target:
    """Validate a target CRUD payload into a Target model."""

    merged = existing.to_dict() if existing else {}
    merged.update(payload)

    protocol = normalize_protocol(str(merged.get("protocol", "icmp")))
    target_type = normalize_target_type(str(merged.get("type", infer_type(protocol))))
    raw_config = merged.get("config", {})
    config = normalize_config(protocol, raw_config if isinstance(raw_config, dict) else {}, merged)
    config = merge_monitoring_config(config, raw_config if isinstance(raw_config, dict) else {})
    host = validate_host(str(merged.get("host") or default_host(protocol, config)))
    label = validate_label(str(merged.get("label") or host))
    scope = validate_scope(str(merged.get("scope", "external")))
    group = validate_group(str(merged.get("group", "Default")))
    environment = validate_group(str(merged.get("environment", "local")))
    interval_ms = normalize_duration_ms(
        merged.get("intervalMs", default_interval_ms(protocol)),
        "intervalMs",
        1_000,
        86_400_000,
    )
    timeout_ms = normalize_duration_ms(
        merged.get("timeoutMs", default_timeout_ms(protocol)),
        "timeoutMs",
        100,
        120_000,
    )
    enabled = bool(merged.get("enabled", True))
    target_id = str(merged.get("id") or slug(f"{label}-{host}-{index}"))[:80]

    return Target(
        id=target_id,
        host=host,
        label=label,
        scope=scope,
        type=target_type,
        protocol=protocol,
        group=group,
        environment=environment,
        enabled=enabled,
        interval_ms=interval_ms,
        timeout_ms=timeout_ms,
        config=config,
    )


def target_from_seed(seed: Target | dict[str, Any], interval_ms: int, timeout_ms: int) -> Target:
    """Convert legacy or structured config seeds into database-managed targets."""

    payload = seed.to_dict() if isinstance(seed, Target) else dict(seed)
    protocol = normalize_protocol(str(payload.get("protocol", "icmp")))
    payload.setdefault("intervalMs", default_interval_ms(protocol))
    payload.setdefault("timeoutMs", default_timeout_ms(protocol))
    return normalize_target_payload(payload)


def default_interval_ms(protocol: TargetProtocol) -> int:
    """Return the default check interval for one protocol."""

    return DEFAULT_INTERVAL_MS_BY_PROTOCOL[protocol]


def default_timeout_ms(protocol: TargetProtocol) -> int:
    """Return the default check timeout for one protocol."""

    return DEFAULT_TIMEOUT_MS_BY_PROTOCOL[protocol]


def normalize_protocol(value: str) -> TargetProtocol:
    """Validate a target protocol."""

    protocol = value.strip().lower()
    if protocol not in VALID_PROTOCOLS:
        raise ValueError("protocol must be one of dns, http, https, icmp, tcp")
    return protocol  # type: ignore[return-value]


def normalize_target_type(value: str) -> TargetType:
    """Validate a target type."""

    target_type = value.strip().lower()
    if target_type not in VALID_TARGET_TYPES:
        raise ValueError("type must be one of website, api, host, port, dns")
    return target_type  # type: ignore[return-value]


def infer_type(protocol: TargetProtocol) -> TargetType:
    """Infer a display target type from a protocol."""

    return {
        "http": "website",
        "https": "website",
        "tcp": "port",
        "icmp": "host",
        "dns": "dns",
    }[protocol]  # type: ignore[return-value]


def normalize_config(protocol: TargetProtocol, raw_config: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate protocol-specific target config."""

    config = dict(raw_config) if isinstance(raw_config, dict) else {}
    if protocol in {"http", "https"}:
        url = str(config.get("url") or payload.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            scheme = "https" if protocol == "https" else "http"
            host = str(payload.get("host") or config.get("host") or "").strip()
            if not host:
                raise ValueError("HTTP targets require a url or host")
            url = f"{scheme}://{host}"
        url = normalize_api_health_url(url, str(payload.get("type", infer_type(protocol))))
        if len(url) > 2_048:
            raise ValueError("url must be at most 2048 characters")

        method = str(config.get("method", "GET")).strip().upper()
        if method not in {"GET", "HEAD", "POST"}:
            raise ValueError("HTTP method must be GET, HEAD, or POST")

        headers = config.get("headers", {})
        normalized_headers = validate_http_headers(headers)

        expected_status = int(config.get("expectedStatus", 200))
        if expected_status < 100 or expected_status > 599:
            raise ValueError("expectedStatus must be between 100 and 599")

        keyword = config.get("keyword")
        if keyword is not None and (not isinstance(keyword, str) or len(keyword) > 200):
            raise ValueError("keyword must be a string up to 200 characters")

        return {
            "url": url,
            "method": method,
            "headers": normalized_headers,
            "expectedStatus": expected_status,
            "keyword": keyword or "",
        }

    if protocol == "tcp":
        host = validate_host(str(config.get("host") or payload.get("host") or ""))
        port = validate_port(int(config.get("port") or payload.get("port") or 0))
        return {"host": host, "port": port}

    if protocol == "icmp":
        host = validate_host(str(config.get("host") or payload.get("host") or ""))
        return {"host": host}

    name = validate_host(str(config.get("name") or payload.get("host") or ""))
    record_type = str(config.get("recordType", "A")).strip().upper()
    if record_type not in VALID_DNS_RECORDS:
        raise ValueError("recordType must be one of A, AAAA, CNAME, MX, TXT, NS")
    expected_value = str(config.get("expectedValue", "")).strip()
    return {"name": name, "recordType": record_type, "expectedValue": expected_value}


def normalize_api_health_url(url: str, target_type: str) -> str:
    """Default API monitors to /health when only the service origin is provided."""

    if target_type.strip().lower() != "api":
        return url

    parsed = urlparse(url)
    if parsed.path not in ("", "/"):
        return url

    return urlunparse(parsed._replace(path="/health"))


def default_host(protocol: TargetProtocol, config: dict[str, Any]) -> str:
    """Derive the target host field from protocol config."""

    if protocol in {"http", "https"}:
        return urlparse(str(config["url"])).hostname or ""
    if protocol == "dns":
        return str(config["name"])
    return str(config["host"])


def validate_group(value: str) -> str:
    """Validate a compact group or environment label."""

    cleaned = value.strip()
    if not GROUP_RE.match(cleaned):
        raise ValueError("group and environment may only contain letters, numbers, spaces, dots, @, (), /, _, and -")
    return cleaned


def normalize_duration_ms(value: Any, name: str, min_value: int, max_value: int) -> int:
    """Normalize an integer or duration string to bounded milliseconds."""

    parsed = parse_duration(value) if isinstance(value, str) else int(value)
    if parsed < min_value or parsed > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}ms")
    return parsed


def merge_monitoring_config(config: dict[str, Any], raw_config: dict[str, Any]) -> dict[str, Any]:
    """Preserve optional monitoring thresholds stored alongside protocol config."""

    merged = dict(config)
    if "latencyWarnMs" in raw_config:
        merged["latencyWarnMs"] = normalize_duration_ms(raw_config["latencyWarnMs"], "latencyWarnMs", 100, 120_000)
    if "color" in raw_config:
        normalized_color = normalize_target_color(raw_config["color"])
        if normalized_color:
            merged["color"] = normalized_color
        else:
            merged.pop("color", None)
    return merged


def normalize_target_color(value: Any) -> str | None:
    """Validate an optional chart color stored in target config."""

    if value is None or value == "":
        return None
    cleaned = str(value).strip()
    if not HEX_COLOR_RE.match(cleaned):
        raise ValueError("color must be a 6-digit hex value like #38bdf8")
    return cleaned.lower()


def target_to_api(target: Target) -> dict[str, Any]:
    """Return one target API object."""

    return target.to_dict()


def repair_api_health_targets(targets: list[Target]) -> list[Target]:
    """Re-normalize stored API targets so bare origins use /health."""

    repaired: list[Target] = []
    for target in targets:
        if target.type != "api" or target.protocol not in {"http", "https"}:
            continue
        normalized = normalize_target_payload(target.to_dict(), existing=target)
        if normalized.config.get("url") != target.config.get("url"):
            repaired.append(normalized)
    return repaired


def gateway_host_sync_payload(existing: Target | None, gateway: str) -> dict[str, Any] | None:
    """Return a partial target update when the detected default gateway changes."""

    if existing is None or existing.host == gateway:
        return None
    return {"host": gateway, "config": {**existing.config, "host": gateway}}
