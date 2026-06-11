"""Time helpers shared by the CLI, terminal renderer, and monitor loop."""

from __future__ import annotations

import math
import re
import time


def now_ms() -> int:
    """Return the current Unix timestamp in milliseconds."""

    return int(time.time() * 1000)


def parse_duration(value: str) -> int:
    """Parse a duration string such as `900ms`, `1s`, `30m`, or `2h`."""

    found = re.match(r"^(\d+(?:\.\d+)?)(ms|s|m|h)?$", value.strip(), re.IGNORECASE)
    if not found:
        raise ValueError(f"Invalid duration: {value}")

    amount = float(found.group(1))
    unit = (found.group(2) or "ms").lower()
    multiplier = {"ms": 1, "s": 1000, "m": 60_000, "h": 3_600_000}[unit]
    return round(amount * multiplier)


def format_duration(ms: int) -> str:
    """Format milliseconds as a compact `1h 2m 3s`-style string."""

    total_seconds = math.ceil(ms / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_clock(timestamp: int) -> str:
    """Format an epoch-ms timestamp as local clock time."""

    return time.strftime("%H:%M:%S", time.localtime(timestamp / 1000))
