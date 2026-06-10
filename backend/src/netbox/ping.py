"""Platform-specific ping execution and output parsing."""

from __future__ import annotations

import math
import platform
import re
import subprocess

from netbox.models import PingResult, Target
from netbox.timeutils import now_ms


def ping_target(target: Target, timeout_ms: int) -> PingResult:
    """Ping one target and normalize success, latency, and error details."""

    started = now_ms()
    command = ping_command(target.host, timeout_ms)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000) + 0.7,
            check=False,
        )
        output = f"{completed.stdout}\n{completed.stderr}"
        latency_ms = parse_latency(output)
        ok = completed.returncode == 0 and latency_ms is not None
        error = None if ok else normalize_ping_error(output)
    except subprocess.TimeoutExpired:
        latency_ms = None
        ok = False
        error = "timeout"
    except FileNotFoundError:
        latency_ms = None
        ok = False
        error = "ping command missing"

    return PingResult(
        id=target.id,
        host=target.host,
        label=target.label,
        scope=target.scope,
        ok=ok,
        latency_ms=latency_ms if ok else None,
        checked_at=now_ms(),
        duration_ms=now_ms() - started,
        error=error,
    )


def ping_command(host: str, timeout_ms: int) -> list[str]:
    """Build a cross-platform ping command without invoking a shell."""

    system = platform.system().lower()
    if system == "darwin":
        return ["ping", "-n", "-c", "1", "-W", str(timeout_ms), host]
    if system == "linux":
        return ["ping", "-n", "-c", "1", "-W", str(max(1, math.ceil(timeout_ms / 1000))), host]
    if system == "windows":
        return ["ping", "-n", "1", "-w", str(timeout_ms), host]
    return ["ping", "-c", "1", host]


def parse_latency(output: str) -> float | None:
    """Extract latency in milliseconds from common ping output formats."""

    unix_match = re.search(r"time[=<]([\d.]+)\s*ms", output, re.IGNORECASE)
    if unix_match:
        return float(unix_match.group(1))

    windows_match = re.search(r"Average\s*=\s*(\d+)ms", output, re.IGNORECASE)
    if windows_match:
        return float(windows_match.group(1))

    return None


def normalize_ping_error(output: str) -> str:
    """Reduce verbose ping failures to stable UI/API error labels."""

    lowered = output.lower()
    if "100.0% packet loss" in lowered or "100% packet loss" in lowered:
        return "packet loss"
    if "unknown host" in lowered or "cannot resolve" in lowered or "name or service not known" in lowered:
        return "dns/resolve failed"
    if "no route to host" in lowered:
        return "no route to host"
    if "request timeout" in lowered:
        return "timeout"
    return "unreachable"
