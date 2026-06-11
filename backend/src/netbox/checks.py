"""Protocol executors for configurable target checks."""

from __future__ import annotations

import socket
import ssl
import urllib.error
import urllib.request

from netbox.models import PingResult, Target
from netbox.ping import ping_target
from netbox.timeutils import now_ms

DEFAULT_HTTP_HEADERS = {
    "User-Agent": "NetboxMonitor/1.0 (+local uptime check)",
    "Accept": "text/html,application/json,*/*;q=0.8",
}


def run_check(target: Target) -> PingResult:
    """Run the configured protocol check for one target."""

    if target.protocol in {"http", "https"}:
        return run_http_check(target)
    if target.protocol == "tcp":
        return run_tcp_check(target)
    if target.protocol == "dns":
        return run_dns_check(target)
    return with_protocol(ping_target(target, target.timeout_ms), target)


def run_http_check(target: Target) -> PingResult:
    """Check an HTTP/S endpoint for status, latency, and optional keyword."""

    started = now_ms()
    config = target.config
    request = urllib.request.Request(
        str(config["url"]),
        method=str(config.get("method", "GET")),
        headers=build_http_headers(config),
    )
    expected_status = int(config.get("expectedStatus", 200))
    keyword = str(config.get("keyword", ""))

    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=target.timeout_ms / 1000, context=context) as response:
            body = response.read(256_000) if keyword else b""
            latency_ms = now_ms() - started
            status_ok = response.status == expected_status
            keyword_ok = not keyword or keyword.encode("utf-8") in body
            ok = status_ok and keyword_ok
            error = None if ok else http_error(status_ok, keyword_ok, response.status, keyword)
    except urllib.error.HTTPError as error_response:
        latency_ms = now_ms() - started
        ok = False
        error = f"http {error_response.code}"
    except (urllib.error.URLError, TimeoutError) as exc:
        latency_ms = None
        ok = False
        error = normalize_error(exc)

    return result(target, ok, latency_ms if ok else None, started, error)


def run_tcp_check(target: Target) -> PingResult:
    """Check whether a TCP host:port accepts connections."""

    started = now_ms()
    config = target.config
    try:
        with socket.create_connection((str(config["host"]), int(config["port"])), timeout=target.timeout_ms / 1000):
            latency_ms = now_ms() - started
            return result(target, True, float(latency_ms), started, None)
    except OSError as exc:
        return result(target, False, None, started, normalize_error(exc))


def run_dns_check(target: Target) -> PingResult:
    """Resolve a DNS record and optionally match an expected value."""

    started = now_ms()
    config = target.config
    try:
        values = resolve_dns(
            str(config["name"]),
            str(config.get("recordType", "A")),
            target.timeout_ms / 1000,
        )
        expected = str(config.get("expectedValue", "")).strip()
        ok = bool(values) and (not expected or expected in values)
        latency_ms = now_ms() - started
        error = None if ok else f"expected {expected} not found"
        return result(target, ok, float(latency_ms) if ok else None, started, error)
    except Exception as exc:
        return result(target, False, None, started, normalize_error(exc))


def resolve_dns(name: str, record_type: str, timeout_seconds: float) -> list[str]:
    """Resolve DNS answers behind a small test seam."""

    import dns.resolver  # type: ignore[import-not-found]

    answers = dns.resolver.resolve(name, record_type, lifetime=timeout_seconds)
    return [answer.to_text().strip('"') for answer in answers]


def result(target: Target, ok: bool, latency_ms: float | None, started: int, error: str | None) -> PingResult:
    """Build a normalized check result."""

    return PingResult(
        id=target.id,
        host=target.host,
        label=target.label,
        scope=target.scope,
        ok=ok,
        latency_ms=latency_ms,
        checked_at=now_ms(),
        duration_ms=now_ms() - started,
        error=error,
        type=target.type,
        protocol=target.protocol,
    )


def with_protocol(ping_result: PingResult, target: Target) -> PingResult:
    """Attach generic target metadata to a legacy ping result."""

    return PingResult(
        id=ping_result.id,
        host=ping_result.host,
        label=ping_result.label,
        scope=ping_result.scope,
        ok=ping_result.ok,
        latency_ms=ping_result.latency_ms,
        checked_at=ping_result.checked_at,
        duration_ms=ping_result.duration_ms,
        error=ping_result.error,
        type=target.type,
        protocol=target.protocol,
    )


def http_error(status_ok: bool, keyword_ok: bool, status: int, keyword: str) -> str:
    """Return a compact HTTP check error."""

    if not status_ok:
        return f"http {status}"
    if not keyword_ok:
        return f"keyword not found: {keyword}"
    return "http check failed"


def build_http_headers(config: dict[str, object]) -> dict[str, str]:
    """Merge default browser-like headers with target-specific overrides."""

    headers = dict(DEFAULT_HTTP_HEADERS)
    raw_headers = config.get("headers", {})
    if isinstance(raw_headers, dict):
        headers.update({str(key): str(value) for key, value in raw_headers.items()})
    return headers


def normalize_error(error: BaseException) -> str:
    """Normalize network exceptions for stable UI output."""

    message = str(error).strip()
    if not message:
        return error.__class__.__name__
    return message[:160]
