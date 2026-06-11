"""Validation for custom HTTP request headers on monitor targets."""

from __future__ import annotations

import re
from typing import Any

HEADER_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
MAX_HEADERS = 20
MAX_HEADER_NAME_LEN = 64
MAX_HEADER_VALUE_LEN = 256


def validate_http_headers(headers: Any) -> dict[str, str]:
    """Validate and normalize a map of HTTP header names to values."""

    if headers is None:
        return {}
    if not isinstance(headers, dict):
        raise ValueError("headers must be an object")
    if len(headers) > MAX_HEADERS:
        raise ValueError(f"headers may contain at most {MAX_HEADERS} entries")

    normalized: dict[str, str] = {}
    for raw_name, raw_value in headers.items():
        name = str(raw_name).strip()
        if not name or len(name) > MAX_HEADER_NAME_LEN:
            raise ValueError("header names must be between 1 and 64 characters")
        if not HEADER_NAME_RE.match(name):
            raise ValueError(f"invalid header name: {raw_name}")

        value = str(raw_value)
        if len(value) > MAX_HEADER_VALUE_LEN:
            raise ValueError(f"header value for {name} must be at most {MAX_HEADER_VALUE_LEN} characters")
        if any(char in value for char in "\r\n\0"):
            raise ValueError(f"header value for {name} may not contain control characters")

        normalized[name] = value

    return normalized
